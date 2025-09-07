from discord.ext import commands
import discord

from bot.config import log_config
from bot.config.db_config import create_session
from bot.databases.auth_repo import ensure_guild_member
from bot.services.request_context import get_current_guild_member


logger = log_config.setup_logger()


class MemberEvents(commands.Cog):
    """
    가입 등 멤버 관련 명령어를 제공하는 Cog.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name='가입')
    async def join(self, ctx: commands.Context):
        """
        현재 길드에서 호출 유저를 회원으로 보장합니다.
        가드가 이미 보장했어도, 멱등하게 다시 보장합니다.
        """
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        with create_session() as session:
            gm = ensure_guild_member(
                session,
                user_id=ctx.author.id,
                user_name=ctx.author.name,
                guild_id=ctx.guild.id,
                guild_name=ctx.guild.name,
                server_nickname=ctx.author.nick or ctx.author.display_name,
            )

        await ctx.send(f"가입 완료: {ctx.author.mention} (길드: {ctx.guild.name})")


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberEvents(bot))


