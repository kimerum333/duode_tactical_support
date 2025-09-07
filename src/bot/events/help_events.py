from discord.ext import commands

from bot.config import log_config


logger = log_config.setup_logger()


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="명령어")
    async def show_commands(self, ctx: commands.Context):
        """
        등록된 명령어들의 이름과 설명을 자동으로 모아 출력합니다.
        사용법: !명령어
        """
        lines = []
        for cmd in sorted(self.bot.commands, key=lambda c: c.name):
            # 숨김/비활성화된 명령은 제외
            if getattr(cmd, "hidden", False):
                continue
            name = cmd.name
            doc = (cmd.callback.__doc__ or "").strip()
            if doc:
                parts = [line.strip() for line in doc.splitlines() if line.strip()]
                desc = parts[0] if parts else "(설명 없음)"
                usage = next((p for p in parts if p.startswith("사용법:")), None)
            else:
                desc = "(설명 없음)"
                usage = None

            if usage:
                lines.append(f"!{name} - {desc} | {usage}")
            else:
                lines.append(f"!{name} - {desc}")

        output = "\n".join(lines) if lines else "등록된 명령어가 없습니다."
        await ctx.send(f"```\n{output}\n```")


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))


