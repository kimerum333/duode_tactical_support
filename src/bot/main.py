from discord.ext import commands
import discord
from bot.config import log_config, bot_config
from bot.config.db_config import ping_db, init_db
from bot.events import basic_events, member_events
from bot.events import lottery_events
from bot.events import admin_events
from bot.events import vault_events
from bot.guards import auth_guard
    
logger = log_config.setup_logger()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Cog 중복 로드를 방지하기 위한 플래그
_COGS_LOADED = False

# 명시적으로 Cog를 로드할 모듈 목록
modules_to_setup = [
    basic_events,
    member_events,
    auth_guard,
    lottery_events,
    admin_events,
    vault_events,
]

@bot.event
async def on_ready():
    """봇이 준비되었을 때 Cog를 로드합니다."""
    # DB 연결 확인 및 초기화
    if ping_db():
        init_db()
        logger.info("DB 연결 확인 및 초기화 완료")
    else:
        logger.warning("DB 연결 확인 실패. SQLite 폴백 또는 환경변수 확인 필요")

    logger.info(f'{bot.user}으로 로그인 성공!')
    global _COGS_LOADED
    if not _COGS_LOADED:
        for module in modules_to_setup:
            try:
                await module.setup(bot)
                logger.info(f"'{module.__name__}' Cog를 성공적으로 로드했습니다.")
            except Exception as e:
                logger.error(f"'{module.__name__}' Cog 로드 중 오류 발생: {e}")
        _COGS_LOADED = True
    
# 봇 실행
logger.info("봇을 시작합니다...")
bot.run(bot_config.DISCORD_BOT_TOKEN)

# python -m bot.main