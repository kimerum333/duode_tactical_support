from typing import Optional
from sqlmodel import Field, Relationship, SQLModel, Enum, Column
from sqlalchemy import BigInteger, ForeignKey
from datetime import datetime
import enum
from datetime import datetime

class ResourceType(str, enum.Enum):
    TALENT = "gm_talent"
    LUCKY_DICE = "gm_lucky_dice"
    VAULT = "gm_vault"

# 각 GM이 길드별로 가진 리소스의 현재 '잔액'을 저장하는 테이블
class GMResourceWallet(SQLModel, table=True):
    __tablename__ = "gm_resource_wallet"

    # 복합 기본 키
    user_id: int = Field(sa_column=Column(BigInteger, ForeignKey("user.id"), primary_key=True))
    guild_id: int = Field(sa_column=Column(BigInteger, ForeignKey("guild.id"), primary_key=True))
    resource_type: ResourceType = Field(sa_column=Column(Enum(ResourceType), primary_key=True))
    
    amount: int = Field(default=0, nullable=False)


# 모든 리소스의 증감 '거래 내역'을 기록하는 테이블
class GMResourceLog(SQLModel, table=True):
    __tablename__ = "gm_resource_log"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    user_id: int = Field(sa_column=Column(BigInteger, ForeignKey("user.id")))
    guild_id: int = Field(sa_column=Column(BigInteger, ForeignKey("guild.id")))
    resource_type: ResourceType = Field(sa_column=Column(Enum(ResourceType)))
    
    change_amount: int # 예: +10 (획득), -5 (사용)
    reason: str # 예: "주간 세션 진행 보상", "아이템 구매"
    
    # 레코드가 생성된 시간을 자동으로 기록합니다.
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)