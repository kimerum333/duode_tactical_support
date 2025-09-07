from __future__ import annotations

from typing import Optional
import contextvars

from bot.models.members import GuildMember


# 메시지 처리 1회(명령어 1회) 동안 유지되는 컨텍스트 저장소
current_guild_member: contextvars.ContextVar[Optional[GuildMember]] = contextvars.ContextVar(
    "current_guild_member", default=None
)


def set_current_guild_member(guild_member: GuildMember) -> None:
    current_guild_member.set(guild_member)


def get_current_guild_member() -> Optional[GuildMember]:
    return current_guild_member.get()


def clear_context() -> None:
    current_guild_member.set(None)


