from discord.ext import commands
import logging

logger = logging.getLogger()


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
    @commands.command(name='테스트')
    async def test_command(self, ctx: commands.Context):
        """
        Cog 로드가 정상적으로 되었는지 테스트하기 위한 간단한 명령어입니다.
        사용자가 '!테스트'를 입력하면 실행됩니다.
        """
        # ctx (Context) 객체에는 메시지에 대한 모든 정보(보낸 사람, 채널 등)가 담겨있습니다.
        guild_name = ctx.guild.name
        user_name = ctx.author.name
        logger.info(f"'{ctx.command}' 명령어가 '{user_name}'에 의해 호출되었습니다.")
        
        # ctx.send()를 사용하면 명령어가 입력된 채널로 바로 메시지를 보낼 수 있습니다.
        await ctx.send(f'안녕하세요, {ctx.author.mention}! `events.py` 파일이 정상적으로 로드되었습니다.')


async def setup(bot: commands.Bot):
    """
    이 setup 함수는 main.py에서 bot.load_extension('app.src.events')를 호출할 때
    필수적으로 실행되는 진입점입니다.
    """
    # BasicCog 클래스의 인스턴스를 생성하여 봇에 Cog로 추가합니다.
    await bot.add_cog(BasicCog(bot))
