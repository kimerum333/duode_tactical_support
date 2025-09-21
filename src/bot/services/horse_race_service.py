from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from bot.databases.horse_race_repo import (
    get_active_race_by_host,
    create_race,
    get_latest_prepared_race_by_host,
    get_prepared_race_by_prep_message_id,
    add_participant,
    remove_participant,
)


def prepare_race_with_guard(
    session: Session, *, guild_id: int, host_user_id: int, prep_message_id: int
):
    """경마 생성 (인당 1개 제한 제거)"""
    race = create_race(session, guild_id=guild_id, host_user_id=host_user_id, prep_message_id=prep_message_id)
    return True, race


def get_latest_prepared_race(session: Session, *, guild_id: int, host_user_id: int):
    return get_latest_prepared_race_by_host(session, guild_id=guild_id, host_user_id=host_user_id)


def add_participant_by_reaction(
    session: Session, *, prep_message_id: int, user_id: int, emoji: str | None
) -> bool:
    print(f"🔍 [SERVICE] add_participant_by_reaction called: prep_msg_id={prep_message_id}, user_id={user_id}, emoji={emoji}")
    
    race = get_prepared_race_by_prep_message_id(session, prep_message_id=prep_message_id)
    if race is None:
        print(f"❌ [SERVICE] No race found for prep_message_id: {prep_message_id}")
        return False
    
    print(f"✅ [SERVICE] Found race: id={race.id}, status={race.status}, host={race.host_user_id}")
    
    try:
        print(f"📝 [SERVICE] Calling add_participant with race_id={race.id}, user_id={user_id}, emoji={emoji}")
        ok = add_participant(session, race_id=race.id, user_id=user_id, emoji=emoji)
        print(f"📝 [SERVICE] add_participant returned: {ok}")
        return ok
    except Exception as e:
        print(f"❌ [SERVICE] Exception in add_participant: {e}")
        return False


def remove_participant_by_reaction(
    session: Session, *, prep_message_id: int, user_id: int
) -> bool:
    race = get_prepared_race_by_prep_message_id(session, prep_message_id=prep_message_id)
    if race is None:
        return False
    try:
        ok = remove_participant(session, race_id=race.id, user_id=user_id)
        return ok
    except Exception as e:
        return False


