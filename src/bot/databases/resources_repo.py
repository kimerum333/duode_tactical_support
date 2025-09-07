from __future__ import annotations

from typing import Optional, Tuple

from sqlmodel import Session, select

from bot.models.gm_resources import GMResourceWallet, GMResourceLog, ResourceType


def get_wallet(
    session: Session, *, user_id: int, guild_id: int, resource_type: ResourceType
) -> Optional[GMResourceWallet]:
    stmt = select(GMResourceWallet).where(
        GMResourceWallet.user_id == user_id,
        GMResourceWallet.guild_id == guild_id,
        GMResourceWallet.resource_type == resource_type,
    )
    return session.exec(stmt).first()


def get_or_create_wallet(
    session: Session, *, user_id: int, guild_id: int, resource_type: ResourceType
) -> GMResourceWallet:
    wallet = get_wallet(
        session, user_id=user_id, guild_id=guild_id, resource_type=resource_type
    )
    if wallet is None:
        wallet = GMResourceWallet(
            user_id=user_id,
            guild_id=guild_id,
            resource_type=resource_type,
            amount=0,
        )
        session.add(wallet)
        session.flush()
    return wallet


def consume_resource(
    session: Session,
    *,
    user_id: int,
    guild_id: int,
    resource_type: ResourceType,
    amount: int = 1,
    reason: str = "spend",
) -> Tuple[bool, int]:
    """
    지정한 자원을 amount만큼 소모합니다.
    - 성공 시 (True, 소모 후 잔액)
    - 실패 시 (False, 현재 잔액)
    """
    if amount <= 0:
        return True, 0

    wallet = get_or_create_wallet(
        session, user_id=user_id, guild_id=guild_id, resource_type=resource_type
    )
    current_amount = wallet.amount or 0

    if current_amount < amount:
        return False, current_amount

    # 차감 및 로그 기록
    wallet.amount = current_amount - amount
    log = GMResourceLog(
        user_id=user_id,
        guild_id=guild_id,
        resource_type=resource_type,
        change_amount=-amount,
        reason=reason,
    )
    session.add(log)
    session.commit()
    session.refresh(wallet)
    return True, wallet.amount


def get_wallet_balance(
    session: Session, *, user_id: int, guild_id: int, resource_type: ResourceType
) -> int:
    wallet = get_or_create_wallet(
        session, user_id=user_id, guild_id=guild_id, resource_type=resource_type
    )
    return wallet.amount or 0


def withdraw_resource(
    session: Session,
    *,
    user_id: int,
    guild_id: int,
    resource_type: ResourceType,
    amount: int,
    reason: str = "withdraw",
) -> Tuple[bool, int]:
    return consume_resource(
        session,
        user_id=user_id,
        guild_id=guild_id,
        resource_type=resource_type,
        amount=amount,
        reason=reason,
    )

def deposit_resource(
    session: Session, *, user_id: int, guild_id: int, resource_type: ResourceType, amount: int, reason: str = "deposit"
) -> int:
    """지정한 자원을 amount만큼 입금하고 새 잔액을 반환합니다."""
    if amount <= 0:
        return get_or_create_wallet(
            session, user_id=user_id, guild_id=guild_id, resource_type=resource_type
        ).amount or 0

    wallet = get_or_create_wallet(
        session, user_id=user_id, guild_id=guild_id, resource_type=resource_type
    )
    wallet.amount = (wallet.amount or 0) + amount

    session.add(
        GMResourceLog(
            user_id=user_id,
            guild_id=guild_id,
            resource_type=resource_type,
            change_amount=amount,
            reason=reason,
        )
    )
    session.commit()
    session.refresh(wallet)
    return wallet.amount


def get_lottery_payout_logs(
    session: Session, *, user_id: int, guild_id: int
):
    """복권 당첨 로그(입금 로그) 목록을 오래된 순으로 반환합니다."""
    stmt = (
        select(GMResourceLog)
        .where(
            GMResourceLog.user_id == user_id,
            GMResourceLog.guild_id == guild_id,
            GMResourceLog.resource_type == ResourceType.VAULT,
            GMResourceLog.change_amount > 0,
            GMResourceLog.reason == "lottery_payout",
        )
        .order_by(GMResourceLog.created_at.asc())
    )
    return list(session.exec(stmt).all())


