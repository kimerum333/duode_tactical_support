from discord.ext import commands

from bot.config.db_config import create_session
from bot.config import log_config
from bot.databases.resources_repo import get_wallet_balance, withdraw_resource
from bot.models.gm_resources import ResourceType


logger = log_config.setup_logger()


class VaultCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="잔고확인")
    async def check_balance(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        with create_session() as session:
            balance = get_wallet_balance(
                session,
                user_id=ctx.author.id,
                guild_id=ctx.guild.id,
                resource_type=ResourceType.VAULT,
            )

        await ctx.send(f"현재 VAULT 잔액: {balance}")

    @commands.command(name="인출")
    async def withdraw(self, ctx: commands.Context, amount: int):
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        if amount <= 0:
            await ctx.send("인출 금액은 1 이상이어야 합니다.")
            return

        with create_session() as session:
            ok, remain = withdraw_resource(
                session,
                user_id=ctx.author.id,
                guild_id=ctx.guild.id,
                resource_type=ResourceType.VAULT,
                amount=amount,
                reason="vault_withdraw",
            )

        if not ok:
            await ctx.send(f"잔액 부족으로 인출 실패. 현재 VAULT 잔액: {remain}")
            return

        await ctx.send(f"인출 완료: {amount}. 현재 VAULT 잔액: {remain}")


async def setup(bot: commands.Bot):
    await bot.add_cog(VaultCog(bot))


