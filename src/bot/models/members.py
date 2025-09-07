from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Enum, Column
from sqlalchemy import BigInteger, ForeignKey, String
import enum

# int를 함께 상속받아, Enum 멤버들을 숫자처럼 비교할 수 있게 됩니다.
class RoleLevel(int, enum.Enum):
    USER = 1
    ADMIN = 2
    DEVELOPER = 3

# Guild와 User 사이의 관계를 정의하는 중간 테이블 모델입니다.
# SQLModel은 Pydantic의 BaseModel을 상속받으므로 데이터 유효성 검사가 가능합니다.
class GuildMember(SQLModel, table=True):
    # 복합 기본 키 설정
    user_id: int = Field(sa_column=Column(BigInteger, ForeignKey("user.id"), primary_key=True))
    guild_id: int = Field(sa_column=Column(BigInteger, ForeignKey("guild.id"), primary_key=True))
    role: RoleLevel = Field(default=RoleLevel.USER, sa_column=Column(Enum(RoleLevel)))
    server_nickname: Optional[str] = Field(default=None, sa_column=Column(String(100), nullable=True))

    user: "User" = Relationship(back_populates="guild_associations")
    guild: "Guild" = Relationship(back_populates="member_associations")


# 모든 디스코드 유저의 고유 정보를 저장하는 테이블 모델
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True))
    name: str
    
    guild_associations: List[GuildMember] = Relationship(back_populates="user")


# 봇이 속한 모든 서버(길드)의 고유 정보를 저장하는 테이블 모델
class Guild(SQLModel, table=True):
    id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, primary_key=True))
    name: str
    
    member_associations: List[GuildMember] = Relationship(back_populates="guild")