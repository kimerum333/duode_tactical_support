from __future__ import annotations

import random
from typing import Tuple

from sqlmodel import Session

from bot.databases.resources_repo import (
    consume_resource,
    deposit_resource,
)
from bot.models.gm_resources import ResourceType
from bot.config.bot_config import LOTTERY_MAX_PAYOUT


def run_lottery_transaction(
    session: Session, *, user_id: int, guild_id: int
) -> Tuple[bool, int, int]:
    """
    복권 로직:
    1) TALENT 1 소모 (부족 시 실패: False, 0, 현재 TALENT 잔액)
    2) 1~1205 상금 계산 후 VAULT 지갑에 입금
    3) 입금 로그 기록

    반환값: (성공여부, 획득 상금, 현재 VAULT 잔액)
    """
    ok, talent_remain = consume_resource(
        session,
        user_id=user_id,
        guild_id=guild_id,
        resource_type=ResourceType.TALENT,
        amount=1,
    )
    if not ok:
        return False, 0, talent_remain

    payout = random.randint(1, LOTTERY_MAX_PAYOUT)

    new_vault_balance = deposit_resource(
        session,
        user_id=user_id,
        guild_id=guild_id,
        resource_type=ResourceType.VAULT,
        amount=payout,
        reason="lottery_payout",
    )

    return True, payout, new_vault_balance


