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

# 경마 설정
# n초 안에 전체 완주
HORSE_RACE_ALL_FINISH_SEC = int(os.getenv("HORSE_RACE_ALL_FINISH_SEC", "20"))
HORSE_RACE_JOIN_REACTION = os.getenv("HORSE_RACE_JOIN_REACTION", "\U0001f3c7")  # 🏇