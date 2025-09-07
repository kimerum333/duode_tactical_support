from discord.ext import commands
import discord

from bot.config import log_config
from bot.config.db_config import create_session
from bot.databases.auth_repo import ensure_guild_member
from bot.services.request_context import set_current_guild_member, clear_context
from discord.ext import commands


logger = log_config.setup_logger()


class AuthGuard(commands.Cog):
    """
    모든 메시지/명령 처리 전에 길드 멤버를 DB에 보장하고 컨텍스트에 주입.
    Nest의 Guard, Spring Security의 Filter/Interceptor와 유사한 위치.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _inject_ctx_check(self, ctx: commands.Context) -> bool:
        """
        모든 명령 실행 전에 길드 멤버를 보장하고 컨텍스트에 주입합니다.
        (discord.py는 이벤트와 명령 실행이 다른 Task일 수 있으므로 on_message만으로는 부족)
        """
        if ctx.guild is None or getattr(ctx.author, "bot", False):
            return True
        with create_session() as session:
            gm = ensure_guild_member(
                session,
                user_id=ctx.author.id,
                user_name=ctx.author.name,
                guild_id=ctx.guild.id,
                guild_name=ctx.guild.name,
                server_nickname=getattr(ctx.author, "nick", None) or getattr(ctx.author, "display_name", None),
            )
            set_current_guild_member(gm)
        return True

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # DM 또는 시스템 메시지 등 길드 없는 경우는 패스
        if message.guild is None or message.author.bot:
            return

        with create_session() as session:
            gm = ensure_guild_member(
                session,
                user_id=message.author.id,
                user_name=message.author.name,
                guild_id=message.guild.id,
                guild_name=message.guild.name,
                server_nickname=message.author.nick or message.author.display_name,
            )
            set_current_guild_member(gm)

        # 명령 실행 여부 판단을 위해 컨텍스트 확인
        ctx = await self.bot.get_context(message)

        # Bot 기본 on_message가 명령 처리를 수행하므로 여기서 재호출하지 않습니다.
        # 명령이 아닌 일반 메시지라면 컨텍스트를 즉시 정리합니다.
        if ctx.command is None:
            clear_context()

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        clear_context()

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        # 권한/체크 실패는 사용자에게 안내
        if isinstance(error, commands.CheckFailure):
            try:
                await ctx.send(str(error))
            except Exception:
                pass
        clear_context()


async def setup(bot: commands.Bot):
    guard = AuthGuard(bot)
    await bot.add_cog(guard)
    bot.add_check(guard._inject_ctx_check)


