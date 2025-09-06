from discord.ext import commands
import discord
from app.src.config import log_config, bot_config

logger = log_config.setup_logger()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 로드할 Cog 목록
initial_extensions = ['app.src.events']

@bot.event
async def on_ready():
    """봇이 준비되었을 때 Cog를 로드합니다."""
    logger.info(f'{bot.user}으로 로그인 성공!')
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            logger.info(f"'{extension}' Cog를 성공적으로 로드했습니다.")
        except Exception as e:
            logger.error(f"'{extension}' Cog 로드 중 오류 발생: {e}")
    
# 봇 실행
logger.info("봇을 시작합니다...")
bot.run(bot_config.DISCORD_BOT_TOKEN)

#python -m app.main