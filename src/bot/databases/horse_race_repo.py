from __future__ import annotations

from typing import Optional, Iterable, List, Tuple
from datetime import datetime

from sqlmodel import Session, select

from bot.models.horse_race import HorseRace, HorseRaceEntry, HorseRaceStatus
from bot.models.members import User, GuildMember


def create_race(session: Session, *, guild_id: int, host_user_id: int, prep_message_id: int) -> HorseRace:
    race = HorseRace(guild_id=guild_id, host_user_id=host_user_id, prep_message_id=prep_message_id)
    session.add(race)
    session.commit()
    session.refresh(race)
    return race


def get_latest_race_by_host(session: Session, *, guild_id: int, host_user_id: int) -> Optional[HorseRace]:
    stmt = (
        select(HorseRace)
        .where(HorseRace.guild_id == guild_id, HorseRace.host_user_id == host_user_id)
        .order_by(HorseRace.created_at.desc())
    )
    return session.exec(stmt).first()


def get_active_race_by_host(session: Session, *, guild_id: int, host_user_id: int) -> Optional[HorseRace]:
    """해당 호스트의 PREPARED 또는 STARTED 상태인 최신 경마를 반환"""
    stmt = (
        select(HorseRace)
        .where(
            HorseRace.guild_id == guild_id,
            HorseRace.host_user_id == host_user_id,
            HorseRace.status.in_([HorseRaceStatus.PREPARED, HorseRaceStatus.STARTED]),
        )
        .order_by(HorseRace.id.desc())
    )
    return session.exec(stmt).first()


def get_latest_prepared_race_by_host(session: Session, *, guild_id: int, host_user_id: int) -> Optional[HorseRace]:
    stmt = (
        select(HorseRace)
        .where(
            HorseRace.guild_id == guild_id,
            HorseRace.host_user_id == host_user_id,
            HorseRace.status == HorseRaceStatus.PREPARED,
        )
        .order_by(HorseRace.id.desc())
    )
    return session.exec(stmt).first()


def get_prepared_race_by_prep_message_id(session: Session, *, prep_message_id: int) -> Optional[HorseRace]:
    stmt = (
        select(HorseRace)
        .where(
            HorseRace.prep_message_id == prep_message_id,
            HorseRace.status == HorseRaceStatus.PREPARED,
        )
        .order_by(HorseRace.id.desc())
    )
    return session.exec(stmt).first()


def add_participant(session: Session, *, race_id: int, user_id: int, emoji: Optional[str] = None) -> bool:
    print(f"🔍 [REPO] add_participant called: race_id={race_id}, user_id={user_id}, emoji={emoji}")
    
    # 인당 1개 참가만 허용
    exists_stmt = select(HorseRaceEntry).where(HorseRaceEntry.race_id == race_id, HorseRaceEntry.user_id == user_id)
    entry = session.exec(exists_stmt).first()
    
    if entry is not None:
        print(f"⚠️ [REPO] Participant already exists, updating emoji if different")
        # 이미 존재하면 이모지만 갱신
        if emoji and entry.emoji != emoji:
            print(f"📝 [REPO] Updating emoji from {entry.emoji} to {emoji}")
            entry.emoji = emoji
            session.add(entry)
            session.commit()
            print(f"✅ [REPO] Emoji updated successfully")
        else:
            print(f"ℹ️ [REPO] No emoji update needed")
        return False
    
    print(f"📝 [REPO] Creating new participant entry")
    new_entry = HorseRaceEntry(race_id=race_id, user_id=user_id, emoji=emoji)
    session.add(new_entry)
    session.commit()
    print(f"✅ [REPO] New participant entry created and committed")
    
    # 생성 확인
    verify_stmt = select(HorseRaceEntry).where(HorseRaceEntry.race_id == race_id, HorseRaceEntry.user_id == user_id)
    verify_entry = session.exec(verify_stmt).first()
    if verify_entry:
        print(f"✅ [REPO] Verification successful - entry exists in DB")
        return True
    else:
        print(f"❌ [REPO] Verification failed - entry not found in DB")
        return False


def list_participants(session: Session, *, race_id: int) -> List[Tuple[int, Optional[str]]]:
    stmt = select(HorseRaceEntry.user_id, HorseRaceEntry.emoji).where(HorseRaceEntry.race_id == race_id)
    return [(row[0], row[1]) for row in session.exec(stmt).all()]


def remove_participant(session: Session, *, race_id: int, user_id: int) -> bool:
    stmt = select(HorseRaceEntry).where(HorseRaceEntry.race_id == race_id, HorseRaceEntry.user_id == user_id)
    entry = session.exec(stmt).first()
    if entry is None:
        return False
    session.delete(entry)
    session.commit()
    return True


def mark_started(session: Session, *, race_id: int, race_message_id: int) -> None:
    race = session.get(HorseRace, race_id)
    if race is None:
        return
    race.status = HorseRaceStatus.STARTED
    race.race_message_id = race_message_id
    race.started_at = datetime.utcnow()
    session.add(race)
    session.commit()


def mark_finished(session: Session, *, race_id: int) -> None:
    race = session.get(HorseRace, race_id)
    if race is None:
        return
    race.status = HorseRaceStatus.FINISHED
    race.finished_at = datetime.utcnow()
    session.add(race)
    session.commit()


def get_user_display_name(session: Session, *, user_id: int, guild_id: int) -> str:
    """사용자의 서버 닉네임 또는 전역 이름을 조회"""
    # 먼저 서버별 닉네임 확인
    stmt = select(GuildMember).where(
        GuildMember.user_id == user_id,
        GuildMember.guild_id == guild_id
    )
    guild_member = session.exec(stmt).first()
    
    if guild_member and guild_member.server_nickname:
        return guild_member.server_nickname
    
    # 서버 닉네임이 없으면 전역 이름 확인
    user = session.get(User, user_id)
    if user and user.name:
        return user.name
    
    # 둘 다 없으면 ID 반환
    return f"사용자{user_id}"


