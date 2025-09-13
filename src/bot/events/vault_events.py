from discord.ext import commands

from bot.config.db_config import create_session
from bot.config import log_config
from bot.databases.resources_repo import withdraw_resource
from bot.models.gm_resources import ResourceType
from bot.services.wallet_service import (
    get_member_balances,
    deposit_member_resource,
    withdraw_member_resource,
)


logger = log_config.setup_logger()


class VaultCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="잔고확인")
    async def check_balance(self, ctx: commands.Context):
        """
        본인 금고 잔액을 확인합니다.
        사용법: !잔고확인
        """
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        balances = get_member_balances(user_id=ctx.author.id, guild_id=ctx.guild.id)
        message = (
            f"현재 잔액\n"
            f"- 금고: {balances['vault']} gp \n"
            f"- 달란트: {balances['talent']}\n"
            f"- 럭키: {balances['lucky']}"
        )
        await ctx.send(f"```\n{message}\n```")

    @commands.command(name="출금")
    async def withdraw(self, ctx: commands.Context, resource: str | None = None, amount: int | None = None):
        """
        본인 지갑에서 재화를 출금(차감)합니다.
        사용법: !출금 {재화종류} {수량}
        예: !출금 달란트 1, !출금 럭키 1, !출금 골드 1200
        """
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        if resource is None or amount is None:
            await ctx.send(
                "사용법: !출금 {재화종류} {수량}\n예: !출금 달란트 1, !출금 럭키 1, !출금 골드 1200"
            )
            return

        ok, label_or_msg, remain = withdraw_member_resource(
            user_id=ctx.author.id,
            guild_id=ctx.guild.id,
            resource_alias=resource,
            amount=amount,
        )

        if not ok:
            await ctx.send(label_or_msg)
            return

        await ctx.send(f"출금 완료: {label_or_msg} {amount}. 현재 {label_or_msg} 잔액: {remain}")

    @commands.command(name="입금")
    async def deposit(self, ctx: commands.Context, resource: str | None = None, amount: int | None = None):
        """
        본인 지갑에 재화를 입금합니다.
        사용법: !입금 {재화종류} {수량}
        예: !입금 달란트 1, !입금 럭키 1, !입금 골드 1200
        """
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        if resource is None or amount is None:
            await ctx.send(
                "사용법: !입금 {재화종류} {수량}\n예: !입금 달란트 1, !입금 럭키 1, !입금 골드 1200"
            )
            return

        ok, label_or_msg, new_balance = deposit_member_resource(
            user_id=ctx.author.id,
            guild_id=ctx.guild.id,
            resource_alias=resource,
            amount=amount,
        )

        if not ok:
            await ctx.send(label_or_msg)
            return

        await ctx.send(f"입금 완료: {label_or_msg} {amount}. 현재 {label_or_msg} 잔액: {new_balance}")


async def setup(bot: commands.Bot):
    await bot.add_cog(VaultCog(bot))


