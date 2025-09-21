from __future__ import annotations

from typing import Optional, Iterable, List, Tuple
from datetime import datetime

from sqlmodel import Session, select

from bot.models.horse_race import HorseRace, HorseRaceEntry, HorseRaceStatus


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
    # 인당 1개 참가만 허용
    exists_stmt = select(HorseRaceEntry).where(HorseRaceEntry.race_id == race_id, HorseRaceEntry.user_id == user_id)
    entry = session.exec(exists_stmt).first()
    if entry is not None:
        # 이미 존재하면 이모지만 갱신
        if emoji and entry.emoji != emoji:
            entry.emoji = emoji
            session.add(entry)
            session.commit()
        return False
    session.add(HorseRaceEntry(race_id=race_id, user_id=user_id, emoji=emoji))
    session.commit()
    return True


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


