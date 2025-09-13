from discord.ext import commands

from bot.config.db_config import create_session
from bot.config import log_config
from bot.services.lottery_service import run_lottery_transaction
from bot.config.bot_config import LOTTERY_EXPECTED_PAYOUT, LOTTERY_MAX_PAYOUT
from bot.databases.resources_repo import get_lottery_payout_logs


logger = log_config.setup_logger()


class LotteryCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="복권")
    async def lottery(self, ctx: commands.Context):
        """
        복권 사용: 달란트 1 소모 후 1~1205g를 금고에 입금합니다.
        사용법: !복권
        """
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        user_id = ctx.author.id
        guild_id = ctx.guild.id

        with create_session() as session:
            ok, payout, vault_balance = run_lottery_transaction(
                session, user_id=user_id, guild_id=guild_id
            )

        if not ok:
            await ctx.send("달란트가 부족합니다. 현재 잔액이 1 미만입니다.")
            return

        await ctx.send(
            f"복권 결과: {payout} 지급! 현재 VAULT 잔액: {vault_balance}\n"
            f"(현재 설정: 최대상금 {LOTTERY_MAX_PAYOUT}, 1회 기댓값 {LOTTERY_EXPECTED_PAYOUT})"
        )

    @commands.command(name="복권통계")
    async def lottery_stats(self, ctx: commands.Context):
        """
        복권 내역과 수익 요약을 출력합니다.
        사용법: !복권통계
        """
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        user_id = ctx.author.id
        guild_id = ctx.guild.id

        with create_session() as session:
            logs = get_lottery_payout_logs(session, user_id=user_id, guild_id=guild_id)

        if not logs:
            await ctx.send(f"{ctx.author.display_name} 님의 복권 기록이 없습니다.")
            return

        # 라인 포맷: YY/MM/DD amount g (4자리 제로패딩)
        lines = []
        total = 0
        for log in logs:
            dt = log.created_at
            y = dt.strftime("%y")
            m = dt.strftime("%m")
            d = dt.strftime("%d")
            amt = int(log.change_amount)
            total += amt
            lines.append(f"{y}/{m}/{d} {amt:04d}g")

        n = len(logs)
        expected = n * LOTTERY_EXPECTED_PAYOUT
        # 수익률(본전=0%) = ((총수익 / 기댓값) - 1) * 100
        roi = ((total / expected - 1.0) * 100.0) if expected > 0 else 0.0

        history_block = "\n".join(lines)
        summary_block = (
            f"총 사용 달란트: {n}\n"
            f"기댓값 : {expected} (= {n} * {LOTTERY_EXPECTED_PAYOUT})\n"
            f"총수익금 : {total}\n"
            f"수익률 : {roi:.1f}%"
        )

        message = (
            f"{ctx.author.display_name} 님의 복권 기록 통계를 공개합니다.\n"
            f"```\n{history_block}\n```\n"
            f"```\n{summary_block}\n```"
        )
        await ctx.send(message)


async def setup(bot: commands.Bot):
    await bot.add_cog(LotteryCog(bot))


