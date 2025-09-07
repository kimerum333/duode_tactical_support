from discord.ext import commands
from bot.config import log_config
from bot.services.authorization import require_min_role
from bot.models.members import RoleLevel

logger = log_config.setup_logger()


class BasicCog(commands.Cog):
    """
    봇의 기본적인 이벤트와 명령어들을 담고 있는 Cog 클래스입니다.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logger.info("BasicCog가 준비되었습니다.")

    # on_ready 외에도 on_member_join 등 다양한 디스코드 이벤트를 처리할 수 있습니다.
    @commands.Cog.listener()
    async def on_connect(self):
        """봇이 디스코드에 성공적으로 연결되었을 때 실행됩니다."""
        logger.info(f"{self.bot.user} (ID: {self.bot.user.id}) 가 성공적으로 연결되었습니다.")

    # name을 지정하지 않으면 함수 이름(test_command)이 명령어 이름이 됩니다.
    # @commands.command(name='테스트')
    # async def test_command(self, ctx: commands.Context):
    #     """
    #     (사용 중지) 봇 동작 확인용 테스트 명령어. 현재는 비활성화됨.
    #     사용법: !테스트
    #     """
    #     logger.info("테스트 명령 호출(현재 비활성화 상태)")

    @commands.command(name='관리자확인')
    @require_min_role(RoleLevel.ADMIN)
    async def admin_only(self, ctx: commands.Context):
        """
        관리자 권한 확인(ADMIN 이상) 명령어.
        사용법: !관리자확인
        """
        await ctx.send(f'관리자 권한 확인 완료: {ctx.author.mention}')

async def setup(bot: commands.Bot):
    """
    이 setup 함수는 main.py에서 bot.load_extension('bot.events.events')를 호출할 때
    필수적으로 실행되는 진입점입니다.
    """
    # BasicCog 클래스의 인스턴스를 생성하여 봇에 Cog로 추가합니다.
    await bot.add_cog(BasicCog(bot))
