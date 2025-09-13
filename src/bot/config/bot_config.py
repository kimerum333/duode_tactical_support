from dotenv import load_dotenv
import os

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if DISCORD_BOT_TOKEN is None:
    raise ValueError("DISCORD_BOT_TOKEN이 .env 파일에 설정되지 않았습니다!")

# 복권 설정
# - 최대 상금
LOTTERY_MAX_PAYOUT = int(os.getenv("LOTTERY_MAX_PAYOUT", "1205"))
# - 1회당 기댓값 (정수)
LOTTERY_EXPECTED_PAYOUT = int(os.getenv("LOTTERY_EXPECTED_PAYOUT", "603"))