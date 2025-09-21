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
    HORSE_RACE_START_REACTION,
    HORSE_RACE_TEST_REACTION,
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
from bot.databases.horse_race_repo import get_latest_race_by_host, get_prepared_race_by_prep_message_id, get_user_display_name
from bot.models.horse_race import HorseRaceStatus


logger = log_config.setup_logger()


class HorseRaceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="경마")
    async def horse_race_main(self, ctx: commands.Context, subcommand: str | None = None):
        if subcommand is None:
            await ctx.send("사용법: !경마 준비 | !경마 테스트\n경마 시작은 준비 메시지의 🏁 리액션을 사용하세요.")
            return

        if subcommand == "준비":
            await self._prepare_race(ctx)
            return
        if subcommand == "종료":
            await self._end_race(ctx)
            return
        if subcommand == "테스트":
            await self._start_race_test(ctx)
            return

        await ctx.send("사용법: !경마 준비 | !경마 테스트\n경마 시작은 준비 메시지의 🏁 리액션을 사용하세요.")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        print(f"🔍 [REACTION ADD] User: {payload.user_id}, Emoji: {payload.emoji}, MSG ID: {payload.message_id}")
        
        # DM/자기봇/다른 서버 등 필터링
        if payload.guild_id is None or payload.user_id is None:
            print("❌ [REACTION ADD] Filtered: DM/No user ID")
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            print("❌ [REACTION ADD] Filtered: No guild")
            return
        if self.bot.user and payload.user_id == self.bot.user.id:
            print("❌ [REACTION ADD] Filtered: Bot user")
            return

        # 채널 확보
        channel = self.bot.get_channel(payload.channel_id) if payload.channel_id else None  # type: ignore[attr-defined]
        if channel is None and payload.channel_id:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except Exception:
                channel = None

        emoji_str = str(payload.emoji)
        print(f"🔍 [REACTION ADD] Processing emoji: {emoji_str}")
        print(f"🔍 [REACTION ADD] Expected start emoji: {HORSE_RACE_START_REACTION}")
        print(f"🔍 [REACTION ADD] Expected test emoji: {HORSE_RACE_TEST_REACTION}")
        print(f"🔍 [REACTION ADD] Emoji match start: {emoji_str == HORSE_RACE_START_REACTION}")
        print(f"🔍 [REACTION ADD] Emoji match test: {emoji_str == HORSE_RACE_TEST_REACTION}")
        
        # 먼저 해당 메시지 ID로 경마가 있는지 확인
        with create_session() as session:
            race = get_prepared_race_by_prep_message_id(session, prep_message_id=payload.message_id)
            if not race:
                print(f"❌ [REACTION ADD] No race found for message ID: {payload.message_id}")
                return
            print(f"✅ [REACTION ADD] Found race ID: {race.id}, Host: {race.host_user_id}")
        
        # 경마 시작 리액션 처리 (여러 체커드 플래그 이모지 지원)
        start_emojis = [HORSE_RACE_START_REACTION, "🏁", "🏴", "🏳️", "🏳️‍🌈", "🏳️‍⚧️", "🏴‍☠️"]
        if emoji_str in start_emojis:
            print(f"🏁 [REACTION ADD] Start race reaction detected: {emoji_str}")
            await self._handle_race_start_reaction(payload, channel)
            return
        
        # 테스트 경마 시작 리액션 처리
        if emoji_str == HORSE_RACE_TEST_REACTION:
            print(f"🧪 [REACTION ADD] Test race reaction detected")
            await self._handle_test_race_reaction(payload, channel)
            return

        # 참가 신청 리액션 처리 (시작/테스트 이모지 제외)
        if emoji_str not in start_emojis and emoji_str != HORSE_RACE_TEST_REACTION:
            print(f"👥 [REACTION ADD] Join reaction detected: {emoji_str}")
            
            # DB에 참가자 추가 시도
            with create_session() as session:
                print(f"📝 [REACTION ADD] Calling add_participant_by_reaction...")
                ok = add_participant_by_reaction(
                    session,
                    prep_message_id=payload.message_id,
                    user_id=payload.user_id,
                    emoji=emoji_str,
                )
                print(f"📝 [REACTION ADD] add_participant_by_reaction returned: {ok}")
                
                # 실제 DB에서 엔트리 생성 여부 확인
                if ok:
                    # 참가자 엔트리 조회로 실제 생성 확인
                    entries = list_participants(session, race_id=race.id)
                    participant_found = any(entry[0] == payload.user_id for entry in entries)
                    print(f"🔍 [REACTION ADD] DB verification - participant found: {participant_found}")
                    print(f"🔍 [REACTION ADD] Current participants: {[entry[0] for entry in entries]}")
                    
                    if participant_found:
                        print(f"✅ [REACTION ADD] Participant successfully added to DB")
                        success_msg = f"<@{payload.user_id}> 참가 신청됨 {emoji_str}"
                    else:
                        print(f"❌ [REACTION ADD] Participant not found in DB despite success return")
                        success_msg = f"<@{payload.user_id}> 참가 신청 실패 (DB 확인 오류)"
                else:
                    print(f"❌ [REACTION ADD] add_participant_by_reaction failed")
                    success_msg = f"<@{payload.user_id}> 참가 신청 실패"
            
            # 피드백 메시지 전송
            if channel and isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(success_msg)
                    print(f"📤 [REACTION ADD] Sent feedback message: {success_msg}")
                except Exception as e:
                    print(f"❌ [REACTION ADD] Failed to send feedback message: {e}")
        else:
            print(f"❌ [REACTION ADD] Ignoring start/test emoji as join reaction: {emoji_str}")
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        print(f"🔍 [REACTION REMOVE] User: {payload.user_id}, Emoji: {payload.emoji}, MSG ID: {payload.message_id}")
        
        if payload.guild_id is None or payload.user_id is None:
            print("❌ [REACTION REMOVE] Filtered: DM/No user ID")
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            print("❌ [REACTION REMOVE] Filtered: No guild")
            return
        if self.bot.user and payload.user_id == self.bot.user.id:
            print("❌ [REACTION REMOVE] Filtered: Bot user")
            return

        # 채널 확보
        channel = self.bot.get_channel(payload.channel_id) if payload.channel_id else None  # type: ignore[attr-defined]
        if channel is None and payload.channel_id:
            try:
                channel = await self.bot.fetch_channel(payload.channel_id)
            except Exception:
                channel = None

        emoji_str = str(payload.emoji)
        print(f"🔍 [REACTION REMOVE] Processing emoji: {emoji_str}")
        
        # 먼저 해당 메시지 ID로 경마가 있는지 확인
        with create_session() as session:
            race = get_prepared_race_by_prep_message_id(session, prep_message_id=payload.message_id)
            if not race:
                print(f"❌ [REACTION REMOVE] No race found for message ID: {payload.message_id}")
                return
            print(f"✅ [REACTION REMOVE] Found race ID: {race.id}, Host: {race.host_user_id}")
        
        # 참가 취소 리액션 처리 (시작/테스트 이모지 제외)
        start_emojis = [HORSE_RACE_START_REACTION, "🏁", "🏴", "🏳️", "🏳️‍🌈", "🏳️‍⚧️", "🏴‍☠️"]
        if emoji_str not in start_emojis and emoji_str != HORSE_RACE_TEST_REACTION:
            print(f"👥 [REACTION REMOVE] Remove participant: {emoji_str}")
            with create_session() as session:
                ok = remove_participant_by_reaction(session, prep_message_id=payload.message_id, user_id=payload.user_id)
            print(f"📝 [REACTION REMOVE] Remove participant result: {ok}")
            
            if channel and isinstance(channel, discord.TextChannel):
                try:
                    await channel.send(f"<@{payload.user_id}> 참가 취소됨 {emoji_str}")
                except Exception:
                    pass
        else:
            print(f"❌ [REACTION REMOVE] Ignoring start/test emoji removal: {emoji_str}")

    async def _handle_race_start_reaction(self, payload: discord.RawReactionActionEvent, channel):
        """경마 시작 리액션 처리"""
        print(f"🏁 [HANDLE START] Processing start reaction for user: {payload.user_id}")
        
        if not channel or not isinstance(channel, discord.TextChannel):
            print("❌ [HANDLE START] Invalid channel")
            return
            
        with create_session() as session:
            race = get_prepared_race_by_prep_message_id(session, prep_message_id=payload.message_id)
            if not race:
                print("❌ [HANDLE START] No race found")
                await channel.send("진행할 경마가 없습니다.")
                return
            print(f"✅ [HANDLE START] Found race ID: {race.id}, Host: {race.host_user_id}")
            
            if race.host_user_id != payload.user_id:
                print(f"❌ [HANDLE START] User {payload.user_id} is not host {race.host_user_id}")
                await channel.send("경마 주최자만 경마를 시작할 수 있습니다.")
                return
                
        print(f"🚀 [HANDLE START] Starting race animation for race ID: {race.id}")
        # 기존 _start_race 로직 실행
        await self._start_race_animation(channel, race.id, race.guild_id, race.host_user_id)

    async def _handle_test_race_reaction(self, payload: discord.RawReactionActionEvent, channel):
        """테스트 경마 시작 리액션 처리"""
        print(f"🧪 [HANDLE TEST] Processing test reaction for user: {payload.user_id}")
        
        if not channel or not isinstance(channel, discord.TextChannel):
            print("❌ [HANDLE TEST] Invalid channel")
            return
            
        with create_session() as session:
            race = get_prepared_race_by_prep_message_id(session, prep_message_id=payload.message_id)
            if not race:
                print("❌ [HANDLE TEST] No race found")
                await channel.send("진행할 경마가 없습니다.")
                return
            print(f"✅ [HANDLE TEST] Found race ID: {race.id}, Host: {race.host_user_id}")
            
            if race.host_user_id != payload.user_id:
                print(f"❌ [HANDLE TEST] User {payload.user_id} is not host {race.host_user_id}")
                await channel.send("경마 주최자만 테스트 경마를 시작할 수 있습니다.")
                return
                
        print(f"🚀 [HANDLE TEST] Starting test race animation for guild: {race.guild_id}")
        # 테스트 경마 실행
        await self._start_race_test_animation(channel, race.guild_id)

    async def _prepare_race(self, ctx: commands.Context):
        if ctx.guild is None:
            await ctx.send("길드(서버) 안에서만 사용할 수 있습니다.")
            return

        # 준비 메시지 발행 (인당 1개 제한 제거)
        prep_msg = await ctx.send(
            f"{ctx.author.display_name} 님이 경마를 준비합니다.\n"
            f"원하는 이모지로 리액션하여 참가 신청하세요!\n"
            f"{HORSE_RACE_START_REACTION} 리액션으로 경마를 시작하세요!\n"
            f"{HORSE_RACE_TEST_REACTION} 리액션으로 테스트 경마를 시작하세요!"
        )

        # DB에 경마 생성
        with create_session() as session:
            create_race(
                session,
                guild_id=ctx.guild.id,
                host_user_id=ctx.author.id,
                prep_message_id=prep_msg.id,
            )

    async def _start_race_animation(self, channel, race_id: int, guild_id: int, host_user_id: int):
        """경마 애니메이션 실행"""
        print(f"🏃 [RACE ANIMATION] Starting animation for race ID: {race_id}, guild: {guild_id}")
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            print("❌ [RACE ANIMATION] Guild not found")
            return

        # 참가자 수집
        participants: List[int] = []
        with create_session() as session:
            entries = list_participants(session, race_id=race_id)
            participants = [user_id for user_id, emoji in entries]
        print(f"👥 [RACE ANIMATION] Found {len(participants)} participants: {participants}")

        # 최소 2명 필요
        if len(participants) < 2:
            print("❌ [RACE ANIMATION] Not enough participants")
            await channel.send("경마를 시작하려면 최소 2명이 필요합니다.")
            return

        # 레일 초기 메시지 구성(참가자별 이모지 적용)
        with create_session() as session:
            entries = list_participants(session, race_id=race_id)
        emoji_map: Dict[int, str] = {user_id: (emoji or "🏇") for user_id, emoji in entries}
        
        # 참가자별 닉네임 조회
        name_map: Dict[int, str] = {}
        with create_session() as session:
            for uid in participants:
                name_map[uid] = get_user_display_name(session, user_id=uid, guild_id=guild_id)
        
        lines = [self._render_lane(None, 0.0, emoji_map.get(uid, "🏇"), display_name=name_map.get(uid)) for uid in participants]
        rail_msg = await channel.send("```\n" + "\n".join(lines) + "\n```")

        with create_session() as session:
            mark_started(session, race_id=race_id, race_message_id=rail_msg.id)

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

            new_lines = [self._render_lane(None, lane_progress[uid], emoji_map.get(uid, "🏇"), display_name=name_map.get(uid)) for uid in participants]
            content = "```\n" + "\n".join(new_lines)

            # 모두 완주했으면 즉시 순위 발표를 같은 메시지에 덧붙임
            if all(p >= 1.0 for p in lane_progress.values()) and not final_announced:
                ranking = sorted([(uid, finish_time_sec.get(uid, duration_all)) for uid in participants], key=lambda x: x[1])
                lines_rank = []
                for idx, (uid, t) in enumerate(ranking, start=1):
                    with create_session() as session:
                        name = get_user_display_name(session, user_id=uid, guild_id=guild_id)
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
            mark_finished(session, race_id=race_id)

        # 최종 순위는 이미 메시지에 반영됨(final_announced). 실패 케이스 대비 보조 출력
        if not final_announced:
            ranking = sorted([(uid, finish_time_sec.get(uid, duration_all)) for uid in participants], key=lambda x: x[1])
            lines_rank = []
            for idx, (uid, t) in enumerate(ranking, start=1):
                with create_session() as session:
                    name = get_user_display_name(session, user_id=uid, guild_id=guild_id)
                lines_rank.append(f"{idx}위  {name}  {t}s")
            try:
                await rail_msg.edit(content="```\n최종 순위\n" + "\n".join(lines_rank) + "\n```")
            except Exception:
                pass

    async def _start_race_test_animation(self, channel, guild_id: int):
        """테스트 경마 애니메이션 실행"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        # 더미 참가자 8명
        dummy_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Heidi"]
        dummy_emojis = ["🐎", "🦄", "🐴", "🏇", "🐎", "🦄", "🐴", "🏇"]
        participants = list(range(1001, 1001 + len(dummy_names)))  # 더미 ID

        # 레일 초기 메시지 구성
        lines = [self._render_lane(None, 0.0, dummy_emojis[i], dummy_names[i]) for i in range(len(participants))]
        rail_msg = await channel.send("```\n" + "\n".join(lines) + "\n```")

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

            new_lines = [self._render_lane(None, lane_progress[uid], dummy_emojis[i], dummy_names[i]) for i, uid in enumerate(participants)]
            content = "```\n" + "\n".join(new_lines)

            # 모두 완주했으면 즉시 순위 발표를 같은 메시지에 덧붙임
            if all(p >= 1.0 for p in lane_progress.values()) and not final_announced:
                ranking = sorted([(uid, finish_time_sec.get(uid, duration_all)) for uid in participants], key=lambda x: x[1])
                lines_rank = []
                for idx, (uid, t) in enumerate(ranking, start=1):
                    name = dummy_names[participants.index(uid)]
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

    def _render_lane(self, member: discord.Member | None, progress: float, emoji: str = "🏇", dummy_name: str | None = None, display_name: str | None = None) -> str:
        if dummy_name:
            name = dummy_name
        elif display_name:
            name = display_name
        else:
            name = member.display_name if member else "참가자"
        
        length = 20
        pos = min(length, max(0, int(progress * length)))
        # 오른쪽 → 왼쪽 진행: 이모지를 좌측으로 이동
        bar = "-" * (length - pos) + emoji + "-" * pos
        return f"|{bar}| {name}"

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


