from __future__ import annotations

from typing import Dict, Tuple, Optional

from bot.config.db_config import create_session
from bot.databases.resources_repo import (
    get_wallet_balance,
    deposit_resource,
    withdraw_resource,
)
from bot.models.gm_resources import ResourceType


def get_member_balances(*, user_id: int, guild_id: int) -> Dict[str, int]:
    """
    주어진 사용자/길드의 주요 리소스 잔액을 모두 조회합니다.
    반환 키: vault, talent, lucky
    """
    with create_session() as session:
        vault_balance = get_wallet_balance(
            session,
            user_id=user_id,
            guild_id=guild_id,
            resource_type=ResourceType.VAULT,
        )
        talent_balance = get_wallet_balance(
            session,
            user_id=user_id,
            guild_id=guild_id,
            resource_type=ResourceType.TALENT,
        )
        lucky_balance = get_wallet_balance(
            session,
            user_id=user_id,
            guild_id=guild_id,
            resource_type=ResourceType.LUCKY_DICE,
        )

    return {
        "vault": vault_balance,
        "talent": talent_balance,
        "lucky": lucky_balance,
    }


# 재화명 별칭 매핑
_RESOURCE_ALIAS_MAP: Dict[str, ResourceType] = {
    # VAULT
    "골드": ResourceType.VAULT,
    "gold": ResourceType.VAULT,
    "vault": ResourceType.VAULT,
    "금고": ResourceType.VAULT,
    # TALENT
    "달란트": ResourceType.TALENT,
    "talent": ResourceType.TALENT,
    # LUCKY
    "럭키": ResourceType.LUCKY_DICE,
    "lucky": ResourceType.LUCKY_DICE,
}

_DISPLAY_NAME_MAP: Dict[ResourceType, str] = {
    ResourceType.VAULT: "골드",
    ResourceType.TALENT: "달란트",
    ResourceType.LUCKY_DICE: "럭키",
}


def resolve_resource_type(alias: str) -> Optional[ResourceType]:
    key = (alias or "").strip().lower()
    return _RESOURCE_ALIAS_MAP.get(key)


def get_resource_display_name(resource_type: ResourceType) -> str:
    return _DISPLAY_NAME_MAP.get(resource_type, resource_type.name)


def deposit_member_resource(
    *, user_id: int, guild_id: int, resource_alias: str, amount: int
) -> Tuple[bool, str, int]:
    """
    재화 문자열 별칭을 받아 해당 리소스에 amount를 입금하고 결과를 반환합니다.

    반환값:
      - (True, <표시이름>, <새 잔액>) 성공
      - (False, <오류메시지>, 0) 실패
    """
    if amount <= 0:
        return False, "입금 금액은 1 이상이어야 합니다.", 0

    rtype = resolve_resource_type(resource_alias)
    if rtype is None:
        return False, "지원하지 않는 재화입니다. 사용 가능: 골드/달란트/럭키", 0

    with create_session() as session:
        new_balance = deposit_resource(
            session,
            user_id=user_id,
            guild_id=guild_id,
            resource_type=rtype,
            amount=amount,
            reason="manual_deposit_command",
        )

    return True, get_resource_display_name(rtype), new_balance


def withdraw_member_resource(
    *, user_id: int, guild_id: int, resource_alias: str, amount: int
) -> Tuple[bool, str, int]:
    """
    재화 문자열 별칭을 받아 해당 리소스에서 amount를 출금(차감)하고 결과를 반환합니다.

    반환값:
      - (True, <표시이름>, <새 잔액>) 성공
      - (False, <오류메시지>, <현재 잔액>) 실패(잔액 부족 등)
    """
    if amount <= 0:
        return False, "출금 금액은 1 이상이어야 합니다.", 0

    rtype = resolve_resource_type(resource_alias)
    if rtype is None:
        return False, "지원하지 않는 재화입니다. 사용 가능: 골드/달란트/럭키", 0

    with create_session() as session:
        ok, remain = withdraw_resource(
            session,
            user_id=user_id,
            guild_id=guild_id,
            resource_type=rtype,
            amount=amount,
            reason="manual_withdraw_command",
        )

    if not ok:
        label = get_resource_display_name(rtype)
        return False, f"잔액 부족으로 출금 실패. 현재 {label} 잔액: {remain}", remain

    # 성공 시 remain이 차감 후 잔액
    return True, get_resource_display_name(rtype), remain


