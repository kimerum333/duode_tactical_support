from __future__ import annotations

import asyncio
from typing import Dict, List
import time

import discord
from discord.ext import commands

from bot.config import log_config
from bot.config.db_config import create_session
from bot.config.bot_config import (
    HORSE_RACE_ALL_FINISH_SEC,
    HORSE_RACE_JOIN_REACTION,
)
from bot.databases.horse_race_repo import (
    add_participant,
    list_participants,
    mark_started,
    mark_finished,
    create_race,
)
from bot.services.horse_race_service import (
    prepare_race_with_guard,
    get_latest_prepared_race,
    add_participant_by_reaction,
    remove_participant_by_reaction,
)
from bot.databases.horse_race_repo import get_latest_race_by_host
from bot.models.horse_race import HorseRaceStatus


logger = log_config.setup_logger()


class HorseRaceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="경마")
    async def horse_race_main(self, ctx: commands.Context, subcommand: str | None = None):
        if subcommand is None:
            await ctx.send("사용법: !경마 준비 | !경마 시작")
            return

        if subcommand == "준비":
            await self._prepare_race(ctx)
            return
        if subcommand == "시작":
            await self._start_race(ctx)
            return
        if subcommand == "시작" and False:
            # placeholder
            pass
        if subcommand == "종료":
            await self._end_race(ctx)
            return
        if subcommand == "테스트":
            await self._start_race_test(ctx)
            return

        await ctx.send("알 수 없는 하위 명령입니다. 사용법: !경마 준비 | !경마 시작")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        print(f"✅ [RAW REACTION DETECTED] User: {payload.user_id}, Emoji: {payload.emoji}, MSG ID: {payload.message_id}")
        # DM/자기봇/다른 서버 등 필터링
        if payload.guild_id is None or payload.user_id is None:
            return
        # 참가 이모지: 설정된 기본 이모지 이외에도 허용하고, 해당 이모지를 저장합니다.
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        # 자기 봇 제외만, 멤버 캐시 미존재여도 통과
        if self.bot.user and payload.user_id == self.bot.user.id:
            return

        # 즉시 감지 피드백 (채널 캐시 실패 시 fetch)
        channel = self.bot.get_channel(payload.channel_id) if payload.channel_id else None  # type: ignore[attr-defined]
        if channel is None and payload.channel_id:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except Exception:
                channel = None
        if channel and isinstance(channel, discord.TextChannel):
            try:
                await channel.send(f"리액션 감지: <@{payload.user_id}> {str(payload.emoji)} (msg:{payload.message_id})")
            except Exception:
                pass

        # PREPARED 상태의 해당 prep_message에 참가자로 기록(이모지 저장)
        with create_session() as session:
            print(f"[DBG] handler.add: calling add_participant_by_reaction")
            ok = add_participant_by_reaction(
                session,
                prep_message_id=payload.message_id,
                user_id=payload.user_id,
                emoji=str(payload.emoji),
            )
        # 간단 피드백 1회
        if channel and isinstance(channel, discord.TextChannel):
            try:
                await channel.send(f"<@{payload.user_id}> 참가 신청됨 {str(payload.emoji)}")
            except Exception:
                pass
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if payload.guild_id is None or payload.user_id is None:
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        if self.bot.user and payload.user_id == self.bot.user.id:
            return

        # 채널 확보
        channel = self.bot.get_channel(payload.channel_id) if payload.channel_id else None  # type: ignore[attr-defined]
        if channel is None and payload.channel_id:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except Exception:
                channel = None

        with create_session() as session:
            print(f"[DBG] handler.remove: calling remove_participant_by_reaction")
            ok = remove_participant_by_reaction(session, prep_message_id=payload.message_id, user_id=payload.user_id)
        if channel and isinstance(channel, discord.TextChannel):
            try:
                await channel.send(f"<@{payload.user_id}> 참가 취소됨 {str(payload.emoji)}")
            except Exception:
                pass

    async def _prepare_race(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        # 먼저 DB 생성 가능 여부 확인 후 메시지 생성
        with create_session() as session:
            # 임시 prep_message_id=0으로 생성 시도 후, 메시지 발행 뒤 업데이트하는 흐름으로도 가능하나,
            # 여기서는 사전 체크 후 메시지를 발행합니다.
            ok, _ = prepare_race_with_guard(
                session,
                guild_id=ctx.guild.id,
                host_user_id=ctx.author.id,
                prep_message_id=0,
            )
        if not ok:
            await ctx.send("이미 진행 중이거나 준비된 경마가 있습니다. 기존 경마를 먼저 종료하세요.")
            return

        # 준비 메시지 발행
        prep_msg = await ctx.send(
            f"{ctx.author.display_name} 님이 경마를 준비합니다. {HORSE_RACE_JOIN_REACTION} 리액션으로 참가 신청하세요!"
        )
        try:
            await prep_msg.add_reaction(HORSE_RACE_JOIN_REACTION)
        except Exception:
            pass

        # 실제 DB에 prep_message_id를 넣어 생성(사전 체크 통과했으므로 직접 생성)
        with create_session() as session:
            create_race(
                session,
                guild_id=ctx.guild.id,
                host_user_id=ctx.author.id,
                prep_message_id=prep_msg.id,
            )

    async def _start_race(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        with create_session() as session:
            race = get_latest_race_by_host(session, guild_id=ctx.guild.id, host_user_id=ctx.author.id)

        if race is None:
            await ctx.send("진행할 경마가 없습니다. 먼저 !경마 준비를 실행하세요.")
            return
        if race.status == HorseRaceStatus.STARTED:
            await ctx.send("가장 최근 경마가 이미 진행 중입니다.")
            return
        if race.status == HorseRaceStatus.FINISHED:
            await ctx.send("가장 최근 경마는 이미 종료되었습니다. 새로 !경마 준비 후 시작하세요.")
            return

        # 준비 메시지의 리액션에서 참가자 수집
        participants: List[int] = []
        try:
            prep_message = await ctx.channel.fetch_message(race.prep_message_id)  # type: ignore[arg-type]
            for reaction in prep_message.reactions:
                if str(reaction.emoji) == HORSE_RACE_JOIN_REACTION:
                    users = [u async for u in reaction.users() if not u.bot]
                    participants = [u.id for u in users]
                    break
        except Exception:
            participants = []

        # 최소 2명 필요
        if len(participants) < 2:
            await ctx.send("경마를 시작하려면 최소 2명이 필요합니다.")
            return

        # 참가자 저장(중복 허용 안 함) + 이미 리액션에서 emoji가 기록되었을 수 있음
        with create_session() as session:
            for uid in participants:
                add_participant(session, race_id=race.id, user_id=uid)  # type: ignore[arg-type]

        # 레일 초기 메시지 구성(참가자별 이모지 적용)
        with create_session() as session:
            entries = list_participants(session, race_id=race.id)  # type: ignore[arg-type]
        emoji_map: Dict[int, str] = {uid: (e or "🏇") for uid, e in entries}
        lines = [self._render_lane(ctx.guild.get_member(uid), 0.0, emoji_map.get(uid, "🏇")) for uid in participants]  # type: ignore[union-attr]
        rail_msg = await ctx.send("```\n" + "\n".join(lines) + "\n```")

        with create_session() as session:
            mark_started(session, race_id=race.id, race_message_id=rail_msg.id)  # type: ignore[arg-type]

        # 사전 시뮬레이션: 최종 순위와 각 완주 시각(초) 결정
        import random
        duration_all = HORSE_RACE_ALL_FINISH_SEC
        order = participants[:]
        random.shuffle(order)
        if len(order) < duration_all:
            finish_seconds = sorted(random.sample(range(1, duration_all + 1), k=len(order)))
        else:
            step = max(1, duration_all // len(order))
            finish_seconds = [min(duration_all, i * step) for i in range(1, len(order) + 1)]
        finish_time_sec: Dict[int, int] = {uid: t for uid, t in zip(order, finish_seconds)}

        lane_progress: Dict[int, float] = {uid: 0.0 for uid in participants}
        final_announced = False

        # 초 단위 애니메이션: 진행률 = elapsed_sec / finish_time_sec
        for sec in range(1, duration_all + 1):
            for uid in participants:
                t = finish_time_sec.get(uid, duration_all)
                lane_progress[uid] = min(1.0, sec / max(1, t))

            new_lines = [self._render_lane(ctx.guild.get_member(uid), lane_progress[uid], emoji_map.get(uid, "🏇")) for uid in participants]  # type: ignore[union-attr]
            content = "```\n" + "\n".join(new_lines)

            # 모두 완주했으면 즉시 순위 발표를 같은 메시지에 덧붙임
            if all(p >= 1.0 for p in lane_progress.values()) and not final_announced:
                ranking = sorted([(uid, finish_time_sec.get(uid, duration_all)) for uid in participants], key=lambda x: x[1])
                lines_rank = []
                for idx, (uid, t) in enumerate(ranking, start=1):
                    m = ctx.guild.get_member(uid)  # type: ignore[union-attr]
                    name = m.display_name if m else str(uid)
                    lines_rank.append(f"{idx}위  {name}  {t}s")
                content += "\n\n최종 순위\n" + "\n".join(lines_rank) + "\n```"
                final_announced = True
            else:
                content += "\n```"

            try:
                await rail_msg.edit(content=content)
            except Exception:
                pass

            if final_announced:
                break
            await asyncio.sleep(1)

        with create_session() as session:
            mark_finished(session, race_id=race.id)  # type: ignore[arg-type]

        # 최종 순위는 이미 메시지에 반영됨(final_announced). 실패 케이스 대비 보조 출력
        if not final_announced:
            ranking = sorted([(uid, finish_time_sec.get(uid, duration_all)) for uid in participants], key=lambda x: x[1])
            lines_rank = []
            for idx, (uid, t) in enumerate(ranking, start=1):
                m = ctx.guild.get_member(uid)  # type: ignore[union-attr]
                name = m.display_name if m else str(uid)
                lines_rank.append(f"{idx}위  {name}  {t}s")
            try:
                await rail_msg.edit(content="```\n최종 순위\n" + "\n".join(lines_rank) + "\n```")
            except Exception:
                pass

    def _render_lane(self, member: discord.Member | None, progress: float, emoji: str = "🏇") -> str:
        name = member.display_name if member else "참가자"
        length = 20
        pos = min(length, max(0, int(progress * length)))
        # 오른쪽 → 왼쪽 진행: 이모지를 좌측으로 이동
        bar = "-" * (length - pos) + emoji + "-" * pos
        return f"{name:10s} |{bar}|"

    def _render_lane_name(self, name: str, progress: float, emoji: str = "🏇") -> str:
        length = 20
        pos = min(length, max(0, int(progress * length)))
        bar = "-" * (length - pos) + emoji + "-" * pos
        return f"{name:10s} |{bar}|"

    async def _start_race_test(self, ctx: commands.Context):
        """
        테스트 전용: 더미 참가자 4명을 사용해 경주를 시작합니다(실제 유저/DB 비사용).
        사용법: !경마 테스트
        """
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        with create_session() as session:
            race = get_latest_race_by_host(session, guild_id=ctx.guild.id, host_user_id=ctx.author.id)
        if race is None or race.status != HorseRaceStatus.PREPARED:
            await ctx.send("시작할 수 있는 최신 경마가 없습니다. 먼저 !경마 준비를 실행하세요.")
            return

        # 더미 참가자 이름 8명 사용
        participants = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Heidi"]

        # 레일 초기 메시지 구성(더미 이름 기반)
        lines = [self._render_lane_name(name, 0.0) for name in participants]
        rail_msg = await ctx.send("```\n" + "\n".join(lines) + "\n```")

        with create_session() as session:
            mark_started(session, race_id=race.id, race_message_id=rail_msg.id)  # type: ignore[arg-type]

        # 테스트 모드: 사전 시뮬레이션 + 초 단위 애니메이션
        import random
        duration_all = HORSE_RACE_ALL_FINISH_SEC
        order = participants[:]
        random.shuffle(order)
        if len(order) < duration_all:
            finish_seconds = sorted(random.sample(range(1, duration_all + 1), k=len(order)))
        else:
            step = max(1, duration_all // len(order))
            finish_seconds = [min(duration_all, i * step) for i in range(1, len(order) + 1)]
        finish_time_sec_name: Dict[str, int] = {name: t for name, t in zip(order, finish_seconds)}

        lane_progress: Dict[str, float] = {name: 0.0 for name in participants}
        final_announced = False

        for sec in range(1, duration_all + 1):
            for name in participants:
                t = finish_time_sec_name.get(name, duration_all)
                lane_progress[name] = min(1.0, sec / max(1, t))

            new_lines = [self._render_lane_name(name, lane_progress[name]) for name in participants]
            content = "```\n" + "\n".join(new_lines)
            if all(p >= 1.0 for p in lane_progress.values()) and not final_announced:
                ranking = sorted([(name, finish_time_sec_name.get(name, duration_all)) for name in participants], key=lambda x: x[1])
                lines_rank = [f"{idx}위  {name}  {t}s" for idx, (name, t) in enumerate(ranking, start=1)]
                content += "\n\n최종 순위\n" + "\n".join(lines_rank) + "\n```"
                final_announced = True
            else:
                content += "\n```"
            try:
                await rail_msg.edit(content=content)
            except Exception:
                pass
            if final_announced:
                break
            await asyncio.sleep(1)

        with create_session() as session:
            mark_finished(session, race_id=race.id)  # type: ignore[arg-type]

        # 최종 순위는 이미 메시지에 반영됨. 실패 케이스 대비 보조 출력
        if not final_announced:
            ranking = sorted([(name, finish_time_sec_name.get(name, duration_all)) for name in participants], key=lambda x: x[1])
            lines_rank = [f"{idx}위  {name}  {t}s" for idx, (name, t) in enumerate(ranking, start=1)]
            try:
                await rail_msg.edit(content="```\n최종 순위\n" + "\n".join(lines_rank) + "\n```")
            except Exception:
                pass

    async def _end_race(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        # 최신 준비 상태 경마 조회
        with create_session() as session:
            race = get_latest_prepared_race(session, guild_id=ctx.guild.id, host_user_id=ctx.author.id)

        if race is None:
            await ctx.send("종료할 대기중(준비) 경마가 없습니다.")
            return

        # 종료 처리
        with create_session() as session:
            mark_finished(session, race_id=race.id)  # type: ignore[arg-type]

        # 안내
        try:
            await ctx.send("대기중인 경마를 종료했습니다.")
        except Exception:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(HorseRaceCog(bot))


