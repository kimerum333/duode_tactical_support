from __future__ import annotations

from typing import Iterable

from discord.ext import commands

from bot.models.members import RoleLevel
from bot.services.request_context import get_current_guild_member


def require_min_role(min_role: RoleLevel):
    """명령 실행에 필요한 최소 역할을 보장합니다."""

    async def predicate(ctx: commands.Context) -> bool:
        gm = get_current_guild_member()
        if gm is None:
            raise commands.CheckFailure("인증 컨텍스트가 비어 있습니다. 잠시 후 다시 시도하세요.")
        if int(gm.role) >= int(min_role):
            return True
        raise commands.CheckFailure(
            f"권한이 부족합니다. 필요한 최소 역할: {min_role.name}, 현재: {gm.role.name}"
        )

    return commands.check(predicate)


def require_any_role(roles: Iterable[RoleLevel]):
    """지정한 역할 중 하나만 충족해도 통과합니다."""

    role_set = {int(r) for r in roles}

    async def predicate(ctx: commands.Context) -> bool:
        gm = get_current_guild_member()
        if gm is None:
            raise commands.CheckFailure("인증 컨텍스트가 비어 있습니다. 잠시 후 다시 시도하세요.")
        if int(gm.role) in role_set:
            return True
        names = ", ".join(sorted([RoleLevel(r).name for r in role_set]))
        raise commands.CheckFailure(
            f"권한이 부족합니다. 요구 역할 중 하나 필요: {names}, 현재: {gm.role.name}"
        )

    return commands.check(predicate)


