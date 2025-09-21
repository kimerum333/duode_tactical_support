from __future__ import annotations

from typing import Optional
from datetime import datetime

from sqlmodel import SQLModel, Field, Column, Enum
from sqlalchemy import BigInteger, ForeignKey, String
import enum


class HorseRaceStatus(str, enum.Enum):
    PREPARED = "PREPARED"
    STARTED = "STARTED"
    FINISHED = "FINISHED"


class HorseRace(SQLModel, table=True):
    __tablename__ = "horse_race"

    id: Optional[int] = Field(default=None, primary_key=True)

    guild_id: int = Field(sa_column=Column(BigInteger, ForeignKey("guild.id")))
    host_user_id: int = Field(sa_column=Column(BigInteger, ForeignKey("user.id")))

    # 참가 신청을 받는 준비 메시지(리액션 대상) id
    prep_message_id: Optional[int] = Field(sa_column=Column(BigInteger, nullable=True))
    # 실제 레이스 진행 메시지 id
    race_message_id: Optional[int] = Field(sa_column=Column(BigInteger, nullable=True))

    status: HorseRaceStatus = Field(
        default=HorseRaceStatus.PREPARED,
        sa_column=Column(Enum(HorseRaceStatus), nullable=False, default=HorseRaceStatus.PREPARED),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    finished_at: Optional[datetime] = Field(default=None)


class HorseRaceEntry(SQLModel, table=True):
    __tablename__ = "horse_race_entry"

    race_id: int = Field(foreign_key="horse_race.id", primary_key=True)
    user_id: int = Field(sa_column=Column(BigInteger, ForeignKey("user.id"), primary_key=True))
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    # 참가자가 선택한 이모지(유니코드 또는 커스텀 이모지 문자열)
    emoji: Optional[str] = Field(default=None, sa_column=Column(String(64), nullable=True))


