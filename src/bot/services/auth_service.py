from typing import Optional

from sqlmodel import select
from sqlmodel import Session

from bot.models.members import User, Guild, GuildMember, RoleLevel


def ensure_guild_member(
    session: Session,
    *,
    user_id: int,
    user_name: str,
    guild_id: int,
    guild_name: str,
) -> GuildMember:
    """
    주어진 Discord 사용자/길드 정보를 기준으로 DB에 User, Guild, GuildMember를 보장합니다.
    존재하지 않으면 생성하고, 존재하면 해당 Association을 반환합니다.
    """
    # User 확보 및 이름 갱신
    user: Optional[User] = session.get(User, user_id)
    if user is None:
        user = User(id=user_id, name=user_name)
        session.add(user)
    else:
        if user.name != user_name:
            user.name = user_name

    # Guild 확보 및 이름 갱신
    guild: Optional[Guild] = session.get(Guild, guild_id)
    if guild is None:
        guild = Guild(id=guild_id, name=guild_name)
        session.add(guild)
    else:
        if guild.name != guild_name:
            guild.name = guild_name

    # GuildMember 확보
    stmt = select(GuildMember).where(
        GuildMember.user_id == user_id,
        GuildMember.guild_id == guild_id,
    )
    gm: Optional[GuildMember] = session.exec(stmt).first()

    if gm is None:
        gm = GuildMember(user_id=user_id, guild_id=guild_id, role=RoleLevel.USER)
        session.add(gm)

    session.commit()
    session.refresh(gm)
    return gm


