from discord.ext import commands

from bot.config import log_config


logger = log_config.setup_logger()


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="명령어")
    async def show_commands(self, ctx: commands.Context):
        """
        등록된 명령어들의 이름과 설명을 카테고리별로 정리하여 출력합니다.
        사용법: !명령어
        """
        # 명령어를 카테고리별로 분류
        categories = {
            "💰 자산 관리": ["잔고확인", "입금", "출금"],
            "🎰 복권": ["복권", "복권통계"],
            "🏇 경마": ["경마"],
            "👤 관리자": ["관리자확인", "달란트지급"],
            "ℹ️ 도움말": ["명령어"]
        }
        
        output_lines = ["📋 **두오데 전술지원시스템 명령어 목록**\n"]
        
        for category, command_names in categories.items():
            category_commands = []
            for cmd in sorted(self.bot.commands, key=lambda c: c.name):
                if getattr(cmd, "hidden", False) or cmd.name not in command_names:
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
                    category_commands.append(f"  !{name} - {desc} | {usage}")
                else:
                    category_commands.append(f"  !{name} - {desc}")
            
            if category_commands:
                output_lines.append(f"**{category}**")
                output_lines.extend(category_commands)
                output_lines.append("")
        
        # 기타 명령어들 (분류되지 않은 것들)
        other_commands = []
        for cmd in sorted(self.bot.commands, key=lambda c: c.name):
            if getattr(cmd, "hidden", False):
                continue
            # 이미 분류된 명령어는 제외
            is_categorized = any(cmd.name in command_names for command_names in categories.values())
            if is_categorized:
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
                other_commands.append(f"  !{name} - {desc} | {usage}")
            else:
                other_commands.append(f"  !{name} - {desc}")
        
        if other_commands:
            output_lines.append("**🔧 기타**")
            output_lines.extend(other_commands)
            output_lines.append("")
        
        output_lines.append("💡 **팁**: 각 명령어의 자세한 사용법은 `!명령어명`을 입력해보세요!")
        
        output = "\n".join(output_lines)
        await ctx.send(output)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))


