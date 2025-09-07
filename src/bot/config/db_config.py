from dotenv import load_dotenv
import os
from typing import Iterator

from sqlmodel import SQLModel, Session, create_engine

from bot.config import log_config


load_dotenv()

# .env 또는 컴포즈에서 제공되는 DSN을 사용합니다.
# 예시: mysql+pymysql://user:password@db:3306/database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bot_database.db")


logger = log_config.setup_logger()

# SQLAlchemy Engine 생성
# - pool_pre_ping: MySQL의 'server has gone away' 방지를 위한 연결 확인
# - pool_recycle: 오래된 연결 재활용 시간(초)
engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=3600,
)


def get_engine():
    """생성된 글로벌 엔진을 반환합니다."""
    return engine


def init_db() -> None:
    """
    모델 메타데이터를 기반으로 테이블을 생성합니다.
    - 테이블이 이미 있으면 무시됩니다.
    """
    try:
        # 순환 의존성을 피하기 위해 함수 내부에서 임포트합니다.
        from bot.models import members, gm_resources  # noqa: F401

        SQLModel.metadata.create_all(engine)
        logger.info("데이터베이스 초기화(SQLModel.metadata.create_all) 완료")
    except Exception as exc:
        logger.error(f"DB 초기화 중 오류: {exc}")
        raise


def ping_db() -> bool:
    """DB 연결 확인용 간단한 핑. 연결 가능하면 True."""
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        return True
    except Exception as exc:
        logger.warning(f"DB 연결 확인 실패: {exc}")
        return False


def create_session() -> Session:
    """
    새로운 세션 인스턴스를 생성하여 반환합니다.
    with 문과 함께 사용하세요:

    with create_session() as session:
        ...
    """
    return Session(engine)


def get_session() -> Iterator[Session]:
    """
    FastAPI 등 DI 스타일에서 사용할 수 있는 제너레이터 형태의 세션 제공자.
    필요 시 사용하세요.
    """
    with Session(engine) as session:
        yield session
