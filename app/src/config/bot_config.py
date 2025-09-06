from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if DISCORD_BOT_TOKEN is None:
    raise ValueError("DISCORD_BOT_TOKEN이 .env 파일에 설정되지 않았습니다!")