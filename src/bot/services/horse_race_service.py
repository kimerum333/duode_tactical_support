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
    """동일 호스트의 활성 경마(PREPARED/STARTED)가 있으면 생성 금지"""
    active = get_active_race_by_host(session, guild_id=guild_id, host_user_id=host_user_id)
    if active is not None:
        return False, active
    race = create_race(session, guild_id=guild_id, host_user_id=host_user_id, prep_message_id=prep_message_id)
    return True, race


def get_latest_prepared_race(session: Session, *, guild_id: int, host_user_id: int):
    return get_latest_prepared_race_by_host(session, guild_id=guild_id, host_user_id=host_user_id)


def add_participant_by_reaction(
    session: Session, *, prep_message_id: int, user_id: int, emoji: str | None
) -> bool:
    race = get_prepared_race_by_prep_message_id(session, prep_message_id=prep_message_id)
    if race is None:
        return False
    try:
        ok = add_participant(session, race_id=race.id, user_id=user_id, emoji=emoji)
        return ok
    except Exception as e:
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


