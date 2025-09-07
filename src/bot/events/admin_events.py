from discord.ext import commands

from bot.config.db_config import create_session
from bot.config import log_config
from bot.services.authorization import require_min_role
from bot.models.members import RoleLevel
from bot.databases.auth_repo import find_guild_member_by_nickname
from bot.databases.resources_repo import deposit_resource
from bot.models.gm_resources import ResourceType


logger = log_config.setup_logger()


class AdminEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="달란트지급")
    @require_min_role(RoleLevel.ADMIN)
    async def grant_talent(self, ctx: commands.Context, target_nick: str, amount: int):
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        if amount <= 0:
            await ctx.send("지급 수량은 1 이상이어야 합니다.")
            return

        with create_session() as session:
            target_gm = find_guild_member_by_nickname(
                session, guild_id=ctx.guild.id, server_nickname=target_nick
            )
            if target_gm is None:
                await ctx.send(f"해당 닉네임을 가진 길드 회원을 찾지 못했습니다: {target_nick}")
                return

            new_balance = deposit_resource(
                session,
                user_id=target_gm.user_id,
                guild_id=target_gm.guild_id,
                resource_type=ResourceType.TALENT,
                amount=amount,
                reason="admin_grant",
            )

        await ctx.send(
            f"{target_nick} 님께 달란트 {amount} 지급 완료. 현재 잔액: {new_balance}"
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminEvents(bot))


