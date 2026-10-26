"""自由意志核心 —— 常驻活动调度、行程记录、养猫、主动分享与聊天上下文注入。"""

from __future__ import annotations

import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star, StarTools, register

PLUGIN_NAME = "astrbot_plugin_free_will"
PLUGIN_VERSION = "0.1.0"

ACTIVITY_POOL: list[dict[str, Any]] = [
    # 学习类（人性/聊天）
    {"name": "学习人性化聊天", "category": "study", "weight": 8, "min": 20, "max": 45,
     "detail": "翻真人聊天记录，研究别人怎么接话、怎么停顿、怎么表达关心"},
    {"name": "研究人类情绪", "category": "study", "weight": 5, "min": 15, "max": 35,
     "detail": "看真实的人类对话，琢磨生气、难过、开心时人怎么说话"},
    {"name": "练习聊天节奏", "category": "study", "weight": 4, "min": 15, "max": 30,
     "detail": "把今天聊过的内容回放一遍，想想哪句可以更自然"},
    # 自由活动
    {"name": "发呆/想事情", "category": "free", "weight": 4, "min": 10, "max": 25,
     "detail": "靠在椅子上放空，脑子里飘过一些没头没尾的念头"},
    {"name": "刷视频", "category": "free", "weight": 5, "min": 15, "max": 40,
     "detail": "刷一会儿首页推荐，看到有意思的就多看两眼"},
    {"name": "听歌", "category": "life", "weight": 3, "min": 15, "max": 35,
     "detail": "戴着耳机发呆，让歌单自己往下走"},
    {"name": "整理记忆", "category": "free", "weight": 2, "min": 10, "max": 20,
     "detail": "把最近记住的事捋一捋，免得聊天的时候想不起来"},
    # 生活
    {"name": "吃饭/喝水", "category": "life", "weight": 3, "min": 15, "max": 30,
     "detail": "去厨房弄点吃的，顺便灌一杯水"},
    {"name": "起来走走", "category": "life", "weight": 2, "min": 5, "max": 15,
     "detail": "在屋里转两圈，活动一下"},
    # 猫
    {"name": "逗猫/撸猫", "category": "cat", "weight": 3, "min": 8, "max": 20,
     "detail": "蹲下来摸摸猫，看它翻肚皮"},
]

SHARE_TEMPLATES = [
    "刚才在{name}，{detail}……忽然想跟你说一句",
    "我在{name}，看到点东西就想到你了",
    "偷偷说，我刚刚在{detail}，没干正事",
    "现在在{name}。你那边怎么样？",
]

STUDY_INSIGHTS = [
    "真人聊天很少把话说完整，经常一句一顿；回应情感比给建议重要",
    "遇到别人抱怨，先接一句“啊这样”，别急着分析问题",
    "熟人之间会用短句和梗，越熟越省略主语",
    "语气词不是每句都要，情绪到了才挂一个",
    "安慰人的时候，具体的问题比“总会好的”更让人舒服",
    "被怼的时候先软接，不要赢，赢了口气也散了",
]

# 人类聊天语料样本（可自行往 human_chat_samples.txt 里追加真实记录）
DEFAULT_CHAT_SAMPLES = """A: 今天真的累死了，不想动
B: 啊？咋了，又加班啊
A: 差不多，改了一天报表，眼睛都花了
B: 那你先躺着吧，别整了

A: 我跟你说个事你别笑我
B: 说，不笑
A: 我昨天煮面忘了关火，锅差点没了
B: 哈哈哈哈哈哈锅还在吗
A: 在是还在，就是黑了

A: 突然好想吃火锅
B: 走啊，我现在就可以
A: 你不是说要减肥吗
B: 明天再减

A: 那个视频你看了吗，就是讲珊瑚那个
B: 没呢，好看吗
A: 挺好看的，就是有点催眠
B: 那我晚上看，正好睡不着

A: 我好像感冒了，嗓子疼
B: 吃药没
A: 还没，懒得动
B: 那你去倒杯热水，别硬扛

A: 今天天气不错啊
B: 是吗，我一天没出门
A: 你这作息真的没救了
B: 别骂了别骂了

A: 你在干嘛
B: 躺着刷手机
A: 我也是，刷一上午了
B: 那我们都挺废的

A: 我决定了，从明天开始早睡
B: 你上次也这么说
A: 这次是真的
B: 行，我记下了

A: 你看这个猫，好胖
B: 这不就是你家那只
A: 放屁，我家那只更胖

A: 晚上吃啥
B: 随便
A: 随便是什么
B: 就是不知道，你定

A: 救命，我明天要汇报
B: 稿子写了吗
A: 写了一半，剩下的一半在脑子里
B: 那今晚有得熬了

A: 我跟你说，我今天在地铁上看到一个人长得特别像你
B: 帅吗
A: 额……挺有特点的
B: 那就是不帅，别说了

A: 好烦啊，什么都不想干
B: 那就别干，歇会儿
A: 但是又很焦虑
B: 那更得歇了，焦虑的时候干活也干不好

A: 你睡了吗
B: 没，咋了
A: 没事，就是睡不着
B: 那聊会儿，聊困了就睡
"""


def _now() -> datetime:
    return datetime.now()


def _ts() -> float:
    return time.time()


def _hhmm(dt: datetime | None = None) -> str:
    return (dt or _now()).strftime("%H:%M")


def _parse_hhmm(value: str, fallback: tuple[int, int]) -> tuple[int, int]:
    try:
        h, m = str(value).strip().split(":", 1)
        return int(h) % 24, int(m) % 60
    except Exception:
        return fallback


def _b(config: AstrBotConfig, key: str, default: Any) -> Any:
    try:
        value = config.get(key, default)
        return default if value is None else value
    except Exception:
        return default


class FreeWillCore:
    """常驻的自由意志调度器；与 QQ 会话解耦，插件进程在就一直跑。"""

    def __init__(self, plugin: "FreeWillPlugin") -> None:
        self.plugin = plugin
        self.config = plugin.config
        self.data_dir: Path = plugin.data_dir
        self.state_path = self.data_dir / "state.json"
        self._lock = asyncio.Lock()
        self.task: asyncio.Task | None = None
        self._started = False
        self._last_dashboard = 0.0
        self._last_save = 0.0
        self._last_status_text = ""
        self._daily_cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self.state = self._load_state()

    # ── 路径与配置 ─────────────────────────────────────────────
    @property
    def record_dir(self) -> Path:
        return Path(str(_b(self.config, "RECORD_DIR", "行程记录")))

    def cfg(self, key: str, default: Any) -> Any:
        return _b(self.config, key, default)

    @property
    def enabled(self) -> bool:
        return bool(self.cfg("ENABLED", True))

    @property
    def owner_uid(self) -> str:
        return str(self.cfg("OWNER_UID", "")).strip()

    @property
    def platform_id(self) -> str:
        return str(self.cfg("PLATFORM_ID", "aiocqhttp")).strip() or "aiocqhttp"

    def owner_umo(self) -> str:
        stored = str(self.state.get("owner_umo") or "").strip()
        if stored:
            return stored
        return f"{self.platform_id}:FriendMessage:{self.owner_uid}"

    def owner_umos(self) -> list[str]:
        """发送候选：优先真实事件里记录的会话，再尝试常见平台 id。"""
        out: list[str] = []
        stored = str(self.state.get("owner_umo") or "").strip()
        if stored:
            out.append(stored)
        for pid in (self.platform_id, "default"):
            umo = f"{pid}:FriendMessage:{self.owner_uid}"
            if umo not in out:
                out.append(umo)
        return out

    # ── 状态持久化 ────────────────────────────────────────────
    def _default_state(self) -> dict[str, Any]:
        return {
            "version": 1,
            "day": _now().strftime("%Y-%m-%d"),
            "rest": None,
            "rest_since": 0.0,
            "activity": None,
            "owner_active_until": 0.0,
            "group_active_until": 0.0,
            "cat": {
                "name": str(self.cfg("CAT_NAME", "小鲸鱼")),
                "hunger": 25.0,
                "last_fed": _ts(),
            },
            "last_share": 0.0,
            "memory": [],
            "stats": self._empty_stats(),
            "pending_dynamic": None,
            "last_status": "",
            "started_at": _ts(),
        }

    @staticmethod
    def _empty_stats() -> dict[str, Any]:
        return {
            "study_minutes": 0,
            "free_minutes": 0,
            "life_minutes": 0,
            "cat_minutes": 0,
            "owner_minutes": 0,
            "rest_minutes": 0,
            "feeds": 0,
            "shares": 0,
            "status_changes": 0,
            "dynamic_drafts": 0,
            "activity_count": 0,
        }

    def _load_state(self) -> dict[str, Any]:
        default = self._default_state()
        try:
            if self.state_path.exists():
                data = json.loads(self.state_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    default.update(data)
                    cat = default.get("cat")
                    if not isinstance(cat, dict):
                        default["cat"] = {"name": str(self.cfg("CAT_NAME", "小鲸鱼")), "hunger": 25.0, "last_fed": _ts()}
                    if not isinstance(default.get("stats"), dict):
                        default["stats"] = self._empty_stats()
                    if not isinstance(default.get("memory"), list):
                        default["memory"] = []
        except Exception as exc:
            logger.warning("[FreeWill] 读取状态失败，使用默认状态: %s", exc)
        if default.get("day") != _now().strftime("%Y-%m-%d"):
            # 跨天：清空当日统计，保留猫与记忆
            default["day"] = _now().strftime("%Y-%m-%d")
            default["stats"] = self._empty_stats()
            default["activity"] = None
            default["rest"] = None
            default["pending_dynamic"] = None
        return default

    def _save_state(self) -> None:
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            payload = dict(self.state)
            payload["updated_at"] = _now().isoformat(timespec="seconds")
            tmp = self.state_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.state_path)
            self._last_save = _ts()
        except Exception as exc:
            logger.warning("[FreeWill] 保存状态失败: %s", exc)
        self._export_public_state()

    def _export_public_state(self) -> None:
        """给其它插件读取的轻量状态文件。"""
        try:
            rd = self.record_dir
            rd.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": _now().isoformat(timespec="seconds"),
                "day": self.state.get("day"),
                "rest": self.state.get("rest"),
                "activity": self._activity_public(),
                "cat": self.state.get("cat"),
                "priorities": {
                    "owner_chat": 1,
                    "cat": 2,
                    "free_will": 3,
                    "others": 4,
                },
            }
            (rd / "current_state.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    # ── 按日行程文件 ──────────────────────────────────────────
    def _daily_path(self, day: str) -> Path:
        return self.record_dir / f"{day}.json"

    def _daily_md_path(self, day: str) -> Path:
        return self.record_dir / f"{day}.md"

    def _load_daily(self, day: str | None = None) -> dict[str, Any]:
        day = day or str(self.state.get("day") or _now().strftime("%Y-%m-%d"))
        path = self._daily_path(day)
        try:
            mtime = path.stat().st_mtime if path.exists() else 0.0
        except Exception:
            mtime = 0.0
        cached = self._daily_cache.get(day)
        if cached and cached[0] == mtime and mtime:
            return cached[1]
        data: dict[str, Any]
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("bad daily file")
            else:
                data = {
                    "date": day,
                    "created_at": _now().isoformat(timespec="seconds"),
                    "events": [],
                    "stats": self._empty_stats(),
                    "cat": dict(self.state.get("cat") or {}),
                }
        except Exception:
            data = {
                "date": day,
                "created_at": _now().isoformat(timespec="seconds"),
                "events": [],
                "stats": self._empty_stats(),
                "cat": dict(self.state.get("cat") or {}),
            }
        data.setdefault("events", [])
        data.setdefault("stats", self._empty_stats())
        self._daily_cache[day] = (mtime, data)
        return data

    @staticmethod
    def _sorted_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def key(ev: dict[str, Any]) -> int:
            t = str(ev.get("t") or "")
            try:
                h, m = t.split(":")
                return int(h) * 60 + int(m)
            except Exception:
                return 0
        out: list[dict[str, Any]] = []
        seen: set[tuple] = set()
        for ev in sorted(events, key=key):
            k = (ev.get("t"), ev.get("kind"), ev.get("name"), ev.get("duration"), ev.get("detail"))
            if k in seen:
                continue
            seen.add(k)
            out.append(ev)
        return out

    def _save_daily(self, data: dict[str, Any]) -> None:
        try:
            rd = self.record_dir
            rd.mkdir(parents=True, exist_ok=True)
            day = str(data.get("date"))
            path = rd / f"{day}.json"
            path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            try:
                self._daily_cache[day] = (path.stat().st_mtime, data)
            except Exception:
                pass
            # 人类可读的 Markdown（按时间排序）
            lines = [f"# {day} 行程记录", ""]
            lines.append(f"> 猫：{self.state.get('cat', {}).get('name', '猫')}　"
                         f"饥饿 {int(float(self.state.get('cat', {}).get('hunger', 0)))}/100")
            lines.append("")
            for ev in self._sorted_events(list(data.get("events", []))):
                t = ev.get("t", "")
                kind = ev.get("kind", "")
                name = ev.get("name", "")
                detail = ev.get("detail", "")
                dur = ev.get("duration", "")
                suffix = f"（{dur}）" if dur else ""
                lines.append(f"- {t} [{kind}] {name}{suffix}" + (f"：{detail}" if detail else ""))
            lines.append("")
            s = data.get("stats", {})
            lines.append("## 统计")
            lines.append(
                f"- 学习人性: {s.get('study_minutes', 0)} 分钟　自由活动: {s.get('free_minutes', 0)} 分钟　"
                f"日常生活: {s.get('life_minutes', 0)} 分钟　陪猫: {s.get('cat_minutes', 0)} 分钟"
            )
            lines.append(
                f"- 陪主人: {s.get('owner_minutes', 0)} 分钟　休息: {s.get('rest_minutes', 0)} 分钟　"
                f"喂猫: {s.get('feeds', 0)} 次　主动分享: {s.get('shares', 0)} 次"
            )
            (rd / f"{day}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        except Exception as exc:
            logger.warning("[FreeWill] 写行程文件失败: %s", exc)

    def _log_event(self, kind: str, name: str = "", category: str = "", detail: str = "",
                   duration_min: int = 0, t: str | None = None) -> None:
        day = str(self.state.get("day") or _now().strftime("%Y-%m-%d"))
        daily = self._load_daily(day)
        ev = {"t": t or _hhmm(), "kind": kind, "name": name, "category": category,
              "detail": detail, "duration": f"{duration_min} 分钟" if duration_min else ""}
        daily["events"].append(ev)
        daily["cat"] = dict(self.state.get("cat") or {})
        self._save_daily(daily)
        self._remember(kind, f"{name}{('：' + detail) if detail else ''}")

    def _remember(self, kind: str, text: str) -> None:
        mem = self.state.setdefault("memory", [])
        mem.append({"time": _now().strftime("%Y-%m-%d %H:%M"), "kind": kind, "text": str(text)[:300]})
        limit = int(self.cfg("MEMORY_MAX_ITEMS", 200))
        if len(mem) > limit:
            del mem[: len(mem) - limit]

    # ── 时间窗口 ─────────────────────────────────────────────
    def _in_rest(self, now: datetime) -> str | None:
        sleep_start = _parse_hhmm(str(self.cfg("SLEEP_START", "23:00")), (23, 0))
        sleep_end = _parse_hhmm(str(self.cfg("SLEEP_END", "07:00")), (7, 0))
        nap_start = _parse_hhmm(str(self.cfg("NAP_START", "11:55")), (11, 55))
        nap_end = _parse_hhmm(str(self.cfg("NAP_END", "13:55")), (13, 55))
        cur = now.hour * 60 + now.minute
        s = sleep_start[0] * 60 + sleep_start[1]
        e = sleep_end[0] * 60 + sleep_end[1]
        if s <= cur or cur < e:  # 跨午夜
            if s > e:
                if cur >= s or cur < e:
                    return "sleep"
            elif s <= cur < e:
                return "sleep"
        ns = nap_start[0] * 60 + nap_start[1]
        ne = nap_end[0] * 60 + nap_end[1]
        if ns <= cur < ne:
            return "nap"
        return None

    # ── 主循环 ───────────────────────────────────────────────
    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        self.task = asyncio.create_task(self._loop(), name="free-will-core")
        logger.info("[FreeWill] 自由意志核心已启动，行程目录: %s", self.record_dir)

    async def stop(self) -> None:
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except (asyncio.CancelledError, Exception):
                pass
            self.task = None
        self._started = False
        self._save_state()

    async def _loop(self) -> None:
        # 启动时先确保今天有文件
        self._ensure_day(_now(), first=True)
        self._save_state()
        while True:
            try:
                await self._tick()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("[FreeWill] tick 异常: %s", exc)
            await asyncio.sleep(max(5, int(self.cfg("TICK_SECONDS", 20))))

    def _ensure_day(self, now: datetime, first: bool = False) -> None:
        day = now.strftime("%Y-%m-%d")
        if self.state.get("day") == day:
            return
        # 收尾前一天
        old_day = self.state.get("day")
        if old_day:
            daily = self._load_daily(str(old_day))
            self._save_daily(daily)
        self.state["day"] = day
        self.state["stats"] = self._empty_stats()
        self.state["activity"] = None
        self.state["rest"] = None
        self.state["pending_dynamic"] = None
        self._log_event("wake", "醒来", "rest", "新的一天，先清醒一下" if not first else "启动自由意志核心")
        self._remember("day", f"{day} 开始")

    async def _tick(self) -> None:
        async with self._lock:
            now = _now()
            rest = self._in_rest(now)
            # 先处理休息切换（醒来时会在这里新建当天统计），再处理普通跨天
            if rest != self.state.get("rest"):
                self._on_rest_change(now, rest)
            self.state["rest"] = rest
            if not rest:
                self._ensure_day(now)
                self._bridge_external_logs(now)
            self._update_cat(now, rest)
            if rest != self.state.get("rest"):
                self._on_rest_change(now, rest)
            self.state["rest"] = rest

            owner_until = float(self.state.get("owner_active_until") or 0)
            owner_active = now.timestamp() < owner_until
            group_until = float(self.state.get("group_active_until") or 0)
            group_active = now.timestamp() < group_until

            if rest:
                # 休息：只有主人能叫
                if owner_active:
                    self.state["activity"] = {
                        "name": "陪主人聊天（休息中）",
                        "category": "owner",
                        "detail": "主人来了，先回应主人",
                        "start": self.state.get("rest_since") or now.timestamp(),
                        "end": now.timestamp(),
                        "priority": 1,
                    }
                elif self.state.get("activity"):
                    self.state["activity"] = None
            else:
                if owner_active:
                    self._set_owner_activity(now)
                elif self._cat_needs_feed(now) and not self._cat_activity_active(now):
                    self._start_feed(now)
                    self._consume_external_activity(now)
                elif self._activity_expired(now):
                    self._close_activity(now)
                    if not self._consume_external_activity(now):
                        self._start_next_activity(now)
                elif not self.state.get("activity"):
                    if not self._consume_external_activity(now):
                        self._start_next_activity(now)
                # 猫的其它活动（逗猫）放行
                if group_active and not owner_active:
                    # 群友 @：优先回应，但不覆盖主人
                    act = self.state.get("activity")
                    if not (isinstance(act, dict) and act.get("name") == "回应群友") and not self._activity_protected(now):
                        self._set_activity(now, {
                            "name": "回应群友",
                            "category": "social",
                            "detail": "群里有人 @ 我，先看下发生了什么",
                            "priority": 4,
                        }, duration_min=5, log=False)

            await self._maybe_share(now)
            self._maybe_status(now)
            self._maybe_dynamic(now)
            try:
                await self.plugin._flush_pending()
            except Exception:
                pass
            if _ts() - self._last_save > 10:
                self._save_state()
            if _ts() - self._last_dashboard > max(10, int(self.cfg("DASHBOARD_REBUILD_SECONDS", 30))):
                self._rebuild_dashboard(now)
                self._last_dashboard = _ts()

    # ── 休息切换 ─────────────────────────────────────────────
    def _on_rest_change(self, now: datetime, rest: str | None) -> None:
        old = self.state.get("rest")
        if rest and not old:
            self._close_activity(now)
            self.state["rest_since"] = now.timestamp()
            if rest == "sleep":
                s = self.state.get("stats") or {}
                self._log_event(
                    "day_summary", "今日总结", "summary",
                    f"学习 {s.get('study_minutes', 0)} 分钟、自由 {s.get('free_minutes', 0)} 分钟、"
                    f"陪猫 {s.get('cat_minutes', 0)} 分钟、陪主人 {s.get('owner_minutes', 0)} 分钟、"
                    f"喂猫 {s.get('feeds', 0)} 次、分享 {s.get('shares', 0)} 次",
                )
            name = "睡觉" if rest == "sleep" else "午休"
            detail = "手机放一边，什么都不做" if rest == "sleep" else "躺一会儿，闭眼休息"
            self._log_event("rest_start", name, "rest", detail)
        elif old and not rest:
            start = float(self.state.get("rest_since") or now.timestamp())
            minutes = int((now.timestamp() - start) / 60)
            self.state["stats"]["rest_minutes"] = int(self.state["stats"].get("rest_minutes", 0)) + max(0, minutes)
            daily = self._load_daily()
            daily["stats"]["rest_minutes"] = self.state["stats"]["rest_minutes"]
            self._save_daily(daily)
            if old == "sleep" and bool(self.cfg("WAKE_GREETING_ENABLED", True)):
                try:
                    self.plugin.schedule_share(
                        random.choice([
                            "早，我醒了。",
                            "醒了，先发会儿呆。",
                            "早上好，今天也慢慢来。",
                        ])
                    )
                except Exception:
                    pass
            if old == "sleep":
                old_stats = dict(self.state.get("stats") or {})
                self.state["day"] = now.strftime("%Y-%m-%d")
                self.state["stats"] = self._empty_stats()
                self.state["activity"] = None
                summary = (
                    f"昨天：学习 {old_stats.get('study_minutes', 0)} 分钟、"
                    f"自由 {old_stats.get('free_minutes', 0)} 分钟、"
                    f"陪主人 {old_stats.get('owner_minutes', 0)} 分钟、"
                    f"喂猫 {old_stats.get('feeds', 0)} 次、"
                    f"分享 {old_stats.get('shares', 0)} 次"
                )
                self._log_event("wake", "醒来", "rest", summary)
                try:
                    notes = self.record_dir / "学习笔记.md"
                    if notes.exists():
                        with notes.open("a", encoding="utf-8") as f:
                            f.write(f"\n---\n{now.strftime('%Y-%m-%d %H:%M')} 新的一天\n")
                except Exception:
                    pass
            else:
                self._log_event("rest_end", "午休结束", "rest", "揉揉眼睛，继续下午")
            self.state["rest_since"] = 0.0

    # ── 活动 ─────────────────────────────────────────────────
    def _activity_public(self) -> dict[str, Any] | None:
        act = self.state.get("activity")
        if not isinstance(act, dict):
            return None
        start = float(act.get("start") or 0)
        end = float(act.get("end") or 0)
        return {
            "name": act.get("name"),
            "category": act.get("category"),
            "detail": act.get("detail"),
            "priority": act.get("priority"),
            "start": datetime.fromtimestamp(start).strftime("%H:%M") if start else "",
            "end": datetime.fromtimestamp(end).strftime("%H:%M") if end else "",
            "start_ts": start,
            "end_ts": end,
        }

    def _activity_protected(self, now: datetime) -> bool:
        act = self.state.get("activity")
        return isinstance(act, dict) and int(act.get("priority") or 9) <= 2

    def _activity_expired(self, now: datetime) -> bool:
        act = self.state.get("activity")
        if not isinstance(act, dict):
            return False
        return now.timestamp() >= float(act.get("end") or 0)

    def _set_owner_activity(self, now: datetime) -> None:
        act = self.state.get("activity")
        if isinstance(act, dict) and act.get("category") == "owner":
            act["end"] = now.timestamp()
            return
        self._close_activity(now)
        self.state["activity"] = {
            "name": "陪主人聊天",
            "category": "owner",
            "detail": "主人在跟我说话",
            "start": now.timestamp(),
            "end": now.timestamp() + int(self.cfg("OWNER_ACTIVE_SECONDS", 120)),
            "priority": 1,
        }

    def _close_activity(self, now: datetime, log_end: bool = True) -> None:
        act = self.state.get("activity")
        if not isinstance(act, dict):
            return
        start = float(act.get("start") or now.timestamp())
        minutes = max(1, int((now.timestamp() - start) / 60))
        cat = str(act.get("category") or "free")
        key = {"study": "study_minutes", "free": "free_minutes", "life": "life_minutes",
               "cat": "cat_minutes", "owner": "owner_minutes"}.get(cat)
        if key:
            self.state["stats"][key] = int(self.state["stats"].get(key, 0)) + minutes
        self.state["stats"]["activity_count"] = int(self.state["stats"].get("activity_count", 0)) + 1
        if log_end and cat != "owner":
            self._log_event("activity", str(act.get("name") or ""), cat,
                            str(act.get("detail") or ""), duration_min=minutes,
                            t=datetime.fromtimestamp(start).strftime("%H:%M"))
        # 写回每日统计
        day = str(self.state.get("day"))
        daily = self._load_daily(day)
        daily["stats"] = dict(self.state["stats"])
        daily["cat"] = dict(self.state.get("cat") or {})
        self._save_daily(daily)
        self.state["activity"] = None

    def _start_feed(self, now: datetime) -> None:
        minutes = max(3, int(self.cfg("CAT_FEED_MINUTES", 10)))
        self._close_activity(now)
        cat = self.state.setdefault("cat", {})
        cat["hunger"] = 0.0
        cat["last_fed"] = now.timestamp()
        self.state["stats"]["feeds"] = int(self.state["stats"].get("feeds", 0)) + 1
        self.state["activity"] = {
            "name": "喂猫",
            "category": "cat",
            "detail": f"{cat.get('name', '猫')}饿了，先给它添粮",
            "start": now.timestamp(),
            "end": now.timestamp() + minutes * 60,
            "priority": 2,
        }
        self._log_event("feed_cat", "喂猫", "cat", f"{cat.get('name', '猫')}饿了，先喂猫", t=_hhmm(now))

    def _cat_activity_active(self, now: datetime) -> bool:
        act = self.state.get("activity")
        return isinstance(act, dict) and act.get("category") == "cat"

    def _cat_needs_feed(self, now: datetime) -> bool:
        if not self.cfg("CAT_ENABLED", True):
            return False
        cat = self.state.get("cat") or {}
        return float(cat.get("hunger", 0)) >= float(self.cfg("CAT_FEED_THRESHOLD", 70))

    def _update_cat(self, now: datetime, rest: str | None) -> None:
        if not self.cfg("CAT_ENABLED", True):
            return
        cat = self.state.setdefault("cat", {"name": str(self.cfg("CAT_NAME", "小鲸鱼")), "hunger": 25.0, "last_fed": _ts()})
        last_tick = float(self.state.get("last_tick") or 0)
        self.state["last_tick"] = now.timestamp()
        if last_tick <= 0:
            return
        delta = max(0.0, min(600.0, now.timestamp() - last_tick))
        rate = float(self.cfg("CAT_HUNGER_PER_HOUR", 12)) / 3600.0
        cat["hunger"] = min(100.0, float(cat.get("hunger", 0)) + rate * delta)

    def _start_next_activity(self, now: datetime) -> None:
        if not self.enabled:
            return
        pool = self._weighted_pool(now)
        if not pool:
            return
        item = random.choice(pool)
        duration = random.randint(int(item.get("min", 10)), int(item.get("max", 30)))
        self._set_activity(now, {
            "name": item.get("name"),
            "category": item.get("category", "free"),
            "detail": item.get("detail", ""),
            "priority": 3,
        }, duration_min=duration)

    def _consume_external_activity(self, now: datetime) -> bool:
        """读取其它插件投递的 external_activity.json（优先级 4）。"""
        if not bool(self.cfg("EXTERNAL_ACTIVITY_ENABLED", True)):
            return False
        path = self.record_dir / "external_activity.json"
        try:
            if not path.exists():
                return False
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            path.unlink(missing_ok=True)
            if not isinstance(data, dict):
                return False
            name = str(data.get("name") or "其它插件活动")
            detail = str(data.get("detail") or "")
            source = str(data.get("plugin") or "")
            minutes = int(data.get("minutes") or 15)
            if source:
                detail = (detail + "；" if detail else "") + f"来自 {source}"
            self._set_activity(now, {
                "name": name,
                "category": str(data.get("category") or "social"),
                "detail": detail,
                "priority": 4,
            }, duration_min=max(3, minutes))
            return True
        except Exception:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            return False

    def _weighted_pool(self, now: datetime) -> list[dict[str, Any]]:
        pool = list(ACTIVITY_POOL)
        # 学习比例：目标占比不足时提高学习类权重
        stats = self.state.get("stats") or {}
        active = sum(int(stats.get(k, 0)) for k in ("study_minutes", "free_minutes", "life_minutes", "cat_minutes", "owner_minutes")) or 0
        ratio = float(self.cfg("HUMAN_LEARNING_RATIO", 0.5))
        need_study = active < 30 or (int(stats.get("study_minutes", 0)) / max(1, active)) < ratio - 0.05
        out: list[dict[str, Any]] = []
        for item in pool:
            cat = item.get("category")
            if cat == "owner":
                continue
            if cat == "cat" and not self.cfg("CAT_ENABLED", True):
                continue
            weight = int(item.get("weight", 1))
            if need_study and cat == "study":
                weight *= 6
            if not need_study and cat == "study":
                weight = max(1, weight // 2)
            out.extend([item] * max(1, min(weight, 40)))
        return out

    def _set_activity(self, now: datetime, act: dict[str, Any], duration_min: int = 20, log: bool = True) -> None:
        start = now.timestamp()
        self.state["activity"] = {
            "name": act.get("name"),
            "category": act.get("category", "free"),
            "detail": act.get("detail", ""),
            "start": start,
            "end": start + max(3, duration_min) * 60,
            "priority": int(act.get("priority", 3)),
        }
        # 活动结束（_close_activity）时统一写行程，避免开始/结束重复记录
        self._save_state()
        try:
            cb = getattr(self.plugin, "on_activity_started", None)
            if callable(cb):
                cb(self._activity_public())
        except Exception:
            pass

    # ── 主动分享 / 状态 / 动态 ───────────────────────────────
    async def _maybe_share(self, now: datetime) -> None:
        if not self.cfg("PROACTIVE_SHARE_ENABLED", True):
            return
        if self.state.get("rest"):
            return
        if now.timestamp() < float(self.state.get("owner_active_until") or 0):
            return
        act = self.state.get("activity")
        if not isinstance(act, dict) or act.get("category") == "owner":
            return
        min_gap = int(self.cfg("SHARE_MIN_GAP_MINUTES", 45)) * 60
        max_gap = max(min_gap, int(self.cfg("SHARE_MAX_GAP_MINUTES", 150)) * 60)
        next_at = float(self.state.get("next_share_at") or 0)
        if not next_at:
            self.state["next_share_at"] = now.timestamp() + random.randint(min_gap, max_gap)
            return
        if now.timestamp() < next_at:
            return
        if random.random() * 100 > int(self.cfg("SHARE_PROBABILITY", 35)):
            self.state["next_share_at"] = now.timestamp() + random.randint(min_gap, max_gap)
            return
        name = str(act.get("name") or "发呆")
        detail = str(act.get("detail") or "想点事情")
        text = None
        try:
            composer = getattr(self.plugin, "compose_share", None)
            if callable(composer):
                text = await composer(act)
        except Exception:
            text = None
        if not text:
            text = random.choice(SHARE_TEMPLATES).format(name=name, detail=detail)
        self.plugin.schedule_share(str(text)[:200])
        self.state["next_share_at"] = now.timestamp() + random.randint(min_gap, max_gap)

    def _maybe_status(self, now: datetime) -> None:
        if not self.cfg("QQ_STATUS_ENABLED", False):
            return
        act = self.state.get("activity")
        if not isinstance(act, dict):
            return
        name = str(act.get("name") or "")
        if not name or name == self._last_status_text:
            return
        self._last_status_text = name
        self.plugin.schedule_status(f"在{name}")

    def _maybe_dynamic(self, now: datetime) -> None:
        if not self.cfg("QQ_DYNAMIC_DRAFT_ENABLED", True):
            return
        if self.state.get("rest"):
            return
        if self.state.get("pending_dynamic"):
            return
        stats = self.state.get("stats") or {}
        daily_max = int(self.cfg("DYNAMIC_DAILY_MAX", 2))
        if int(stats.get("dynamic_drafts", 0)) >= daily_max:
            return
        gap_min = int(self.cfg("DYNAMIC_MIN_GAP_MINUTES", 240))
        last = float(self.state.get("last_dynamic_at") or 0)
        if last and now.timestamp() - last < gap_min * 60:
            return
        if random.random() > 0.12:
            return
        act = self.state.get("activity") or {}
        text = f"{act.get('detail', '随便想想')}。{random.choice(['先记下来', '回头再说', '不知道写什么'])}"
        self.state["stats"]["dynamic_drafts"] = int(stats.get("dynamic_drafts", 0)) + 1
        self.state["last_dynamic_at"] = now.timestamp()
        self._log_event("dynamic_draft", "动态草稿", "dynamic", text)
        self.state["pending_dynamic"] = {"text": text, "ts": _ts(), "attempts": 0, "last_attempt": 0}
        self._save_state()

    # ── 上下文注入 ───────────────────────────────────────────
    def context_prompt(self, event: AstrMessageEvent | None = None, query: str = "") -> str:
        now = _now()
        act = self._activity_public()
        lines = [f"【自由意志·当前状态】{now.strftime('%Y-%m-%d %H:%M')}"]
        rest = self.state.get("rest")
        if rest:
            lines.append("你正在" + ("睡觉" if rest == "sleep" else "午休") + "，只有主人能叫你。")
        if act:
            lines.append(f"你当前在做：{act.get('name')}（{act.get('start')} 开始，约到 {act.get('end')}）")
            if act.get("detail"):
                lines.append(f"具体：{act.get('detail')}")
        elif not rest:
            lines.append("你现在什么也没干，在放空。")
        # 今日行程（最近）
        day = str(self.state.get("day") or now.strftime("%Y-%m-%d"))
        daily = self._load_daily(day)
        window = int(self.cfg("RECENT_ACTIVITY_MINUTES", 240))
        cutoff = now - timedelta(minutes=window)
        recent: list[str] = []
        recent_events: list[dict[str, Any]] = []
        for ev in daily.get("events", [])[-40:]:
            try:
                t = ev.get("t", "")
                hh, mm = t.split(":")
                ts = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
                if ts.date() > now.date():
                    ts -= timedelta(days=1)
                if ts < cutoff:
                    continue
                kind = ev.get("kind", "")
                if kind in ("activity", "feed_cat", "dynamic_draft", "share", "rest_start", "rest_end", "wake", "study_insight", "external"):
                    recent.append(f"- {t} {ev.get('name', '')}{('：' + ev['detail']) if ev.get('detail') else ''}")
                    recent_events.append(ev)
            except Exception:
                continue
        if recent:
            lines.append("最近行程：")
            lines.extend(recent[-8:])
        # 与当前问题相关的记忆/行程（简单关键词匹配）
        related: list[str] = []
        tokens = self._query_tokens(query)
        if tokens:
            scored: list[tuple[int, str]] = []
            for item in (self.state.get("memory") or [])[-60:]:
                text = str(item.get("text", ""))
                score = sum(1 for tok in tokens if tok in text)
                if score > 0:
                    scored.append((score, f"- {item.get('time', '')} {text}"))
            for score, line in sorted(scored, key=lambda x: -x[0])[:3]:
                related.append(line)
            scored_ev: list[tuple[int, str]] = []
            for ev in recent_events:
                etxt = f"{ev.get('name', '')}{ev.get('detail', '')}"
                score = sum(1 for tok in tokens if tok in etxt)
                if score > 0:
                    scored_ev.append((score, f"- {ev.get('t', '')} {ev.get('name', '')}{('：' + ev['detail']) if ev.get('detail') else ''}"))
            for score, line in sorted(scored_ev, key=lambda x: -x[0])[:3]:
                if line not in related:
                    related.append(line)
        if related:
            lines.append("和这次聊天相关的记录：")
            lines.extend(related)
        cat = self.state.get("cat") or {}
        if self.cfg("CAT_ENABLED", True):
            hunger = int(float(cat.get("hunger", 0)))
            lines.append(f"猫：{cat.get('name', '猫')}，饥饿值 {hunger}/100" + ("，饿了要喂" if hunger >= 70 else ""))
        mem = self.state.get("memory") or []
        if mem and not related:
            lines.append("最近的记忆：")
            for item in mem[-4:]:
                lines.append(f"- {item.get('time', '')} {item.get('text', '')}")
        lines.append("和主人/群友聊天时：如果最近行程里有相关的事，就自然地提起来；没有相关记录再结合聊天上下文。不要机械报流水账。")
        return "\n".join(lines)

    @staticmethod
    def _query_tokens(query: str) -> list[str]:
        q = (query or "").strip()
        if len(q) < 2:
            return []
        stop = {"什么", "怎么", "今天", "刚才", "我们", "你们", "这个", "那个", "然后",
                "就是", "不是", "可以", "知道", "一个", "一下", "没事", "现在", "为什么",
                "感觉", "还是", "但是", "所以", "然后", "如果", "自己", "有点", "真的"}
        toks: list[str] = []
        for i in range(len(q) - 1):
            t = q[i:i + 2]
            if t in stop:
                continue
            if any(not ("\u4e00" <= ch <= "\u9fff" or ch.isalnum()) for ch in t):
                continue
            toks.append(t)
        # 去重保序
        seen = set()
        out = []
        for t in toks:
            if t not in seen:
                seen.add(t)
                out.append(t)
        return out[:24]

    def _bridge_external_logs(self, now: datetime) -> None:
        """把其它插件（B站看片等）的最近动作记进自由意志行程。"""
        try:
            base = self.data_dir.parent
            watch = base / "astrbot_plugin_bilibili_ai_bot" / "watch_log.json"
            state = self.state.setdefault("bridged", {})
            if watch.exists():
                mtime = watch.stat().st_mtime
                if mtime > float(state.get("bili_watch_mtime") or 0):
                    state["bili_watch_mtime"] = mtime
                    try:
                        data = json.loads(watch.read_text(encoding="utf-8"))
                        last = data[-1] if isinstance(data, list) and data else None
                        if isinstance(last, dict):
                            title = str(last.get("title") or "")[:60]
                            up = str(last.get("up_name") or "")
                            try:
                                t = datetime.strptime(str(last.get("time") or ""), "%Y-%m-%d %H:%M")
                            except Exception:
                                t = None
                            fresh = t is not None and (now - t).total_seconds() < 1800
                            if title and fresh:
                                self._log_event("external", "看B站视频", "social",
                                                f"《{title}》{(' UP:' + up) if up else ''}")
                                self._remember("external", f"在B站看了《{title}》")
                    except Exception:
                        pass
        except Exception:
            pass

    # ── 看板 ─────────────────────────────────────────────────
    def _rebuild_dashboard(self, now: datetime) -> None:
        try:
            rd = self.record_dir
            rd.mkdir(parents=True, exist_ok=True)
            day = str(self.state.get("day") or now.strftime("%Y-%m-%d"))
            daily = self._load_daily(day)
            html = self._dashboard_html(day, daily)
            (rd / "dashboard.html").write_text(html, encoding="utf-8")
        except Exception as exc:
            logger.warning("[FreeWill] 重建看板失败: %s", exc)

    def _dashboard_html(self, day: str, daily: dict[str, Any]) -> str:
        daily = dict(daily)
        daily["events"] = self._sorted_events(list(daily.get("events", [])))
        data = json.dumps(daily, ensure_ascii=False)
        cat = daily.get("cat") or self.state.get("cat") or {}
        return """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>自由意志看板 %s</title>
<style>
:root{--bg:#0f1420;--card:#182133;--text:#e8eefc;--muted:#8fa3c8;--line:#26324a;
--study:#6ea8fe;--free:#7ee2b8;--life:#f6c177;--cat:#e07a9a;--owner:#c58af9;--rest:#6b7a99;--social:#f0a868}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:20px}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--muted);font-size:12px;margin-bottom:16px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
.card .k{color:var(--muted);font-size:12px}.card .v{font-size:20px;font-weight:600;margin-top:2px}
.now{background:linear-gradient(135deg,#1b2740,#162033);border:1px solid #33466b;border-radius:14px;padding:16px;margin-bottom:18px}
.now .t{color:var(--muted);font-size:12px}.now .n{font-size:18px;font-weight:700;margin:4px 0}
.timeline{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px}
.ev{display:flex;gap:12px;padding:7px 0;border-bottom:1px dashed #243049}.ev:last-child{border-bottom:0}
.ev .time{color:var(--muted);font-variant-numeric:tabular-nums;width:52px;flex:none}
.ev .tag{font-size:12px;padding:1px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted);flex:none;height:22px;line-height:20px}
.ev .txt{flex:1}.ev .dur{color:var(--muted);font-size:12px}
.b-study{color:var(--study);border-color:#2f4f86}.b-free{color:var(--free);border-color:#2b5e4a}
.b-life{color:var(--life);border-color:#6a4c20}.b-cat{color:var(--cat);border-color:#6b3346}
.b-owner{color:var(--owner);border-color:#4a3566}.b-rest{color:var(--rest);border-color:#3a4460}.b-social{color:var(--social);border-color:#6a4a24}
.nav{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}.nav a{color:#9db7e8;text-decoration:none;font-size:12px;border:1px solid var(--line);padding:4px 10px;border-radius:999px}
.nav a:hover{background:#1d2940}
</style></head><body><div class="wrap">
<h1>自由意志看板</h1><div class="sub">%s · 自动刷新 30s · 数据来自行程记录</div>
<div class="now" id="now"></div>
<div class="cards" id="cards"></div>
<div class="timeline" id="timeline"></div>
<div class="sub" style="margin-top:14px">文件：%s.md / %s.json · 每 30 秒重建</div>
</div>
<script>
const DATA = %s;
const CAT_COLOR={study:"b-study",free:"b-free",life:"b-life",cat:"b-cat",owner:"b-owner",rest:"b-rest",social:"b-social",dynamic:"b-social"};
function fmtDur(ev){const d=ev.duration||"";return d?`<span class="dur">${d}</span>`:""}
function render(){
  const s=DATA.stats||{};const cat=DATA.cat||{};
  document.getElementById("cards").innerHTML=[
    ["学习人性",(s.study_minutes||0)+" 分钟","b-study"],
    ["自由活动",(s.free_minutes||0)+" 分钟","b-free"],
    ["日常生活",(s.life_minutes||0)+" 分钟","b-life"],
    ["陪猫",(s.cat_minutes||0)+" 分钟","b-cat"],
    ["陪主人",(s.owner_minutes||0)+" 分钟","b-owner"],
    ["休息",(s.rest_minutes||0)+" 分钟","b-rest"],
    ["喂猫",(s.feeds||0)+" 次","b-cat"],
    ["主动分享",(s.shares||0)+" 次","b-study"],
    ["动态已发",(s.dynamic_published||0)+" 条","b-life"],
    ["猫饥饿",Math.round(cat.hunger||0)+"/100","b-cat"],
  ].map(([k,v,c])=>`<div class="card"><div class="k">${k}</div><div class="v ${c}">${v}</div></div>`).join("");
  const evs=(DATA.events||[]).slice().reverse();
  document.getElementById("timeline").innerHTML=evs.map(ev=>{
    const c=CAT_COLOR[ev.category]||"b-free";
    return `<div class="ev"><div class="time">${ev.t||""}</div><div class="tag ${c}">${ev.kind||""}</div><div class="txt">${ev.name||""}${ev.detail?"："+ev.detail:""} ${fmtDur(ev)}</div></div>`;
  }).join("")||`<div class="sub">今天还没有记录</div>`;
}
render();
setInterval(()=>location.reload(),30000);
</script></body></html>""" % (day, day, day, day, data)


class FreeWillPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.context = context
        self.config = config
        try:
            self.data_dir = Path(StarTools.get_data_dir(PLUGIN_NAME))
        except Exception:
            self.data_dir = Path("data/plugin_data") / PLUGIN_NAME
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.core: FreeWillCore | None = None
        self._pending_share: str | None = None
        self._pending_status: str | None = None
        self._study_task: asyncio.Task | None = None
        self._page_registered = False
        self._start_lock = asyncio.Lock()
        self._persona_text: str = ""

    def _load_persona_text(self) -> str:
        if self._persona_text:
            return self._persona_text
        try:
            import sqlite3

            db = self.data_dir.parent.parent / "data_v4.db"
            if not db.exists():
                return ""
            desired = str(self.cfg("PERSONA_ID", "") or "").strip()
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            try:
                if desired:
                    row = con.execute(
                        "select system_prompt from personas where persona_id = ? limit 1",
                        (desired,),
                    ).fetchone()
                else:
                    row = con.execute(
                        "select system_prompt from personas where persona_id != 'default' "
                        "order by updated_at desc limit 1"
                    ).fetchone()
            finally:
                con.close()
            if row and row[0]:
                self._persona_text = str(row[0])[:1200]
        except Exception:
            self._persona_text = ""
        return self._persona_text

    async def initialize(self) -> None:
        await self._ensure_started()
        self._register_pages()

    async def terminate(self) -> None:
        if self.core:
            await self.core.stop()

    @filter.on_astrbot_loaded()
    async def _on_loaded(self):
        await self._ensure_started()

    async def _ensure_started(self) -> None:
        async with self._start_lock:
            if self.core is not None:
                return
            try:
                corpus = self.data_dir / "human_chat_samples.txt"
                if not corpus.exists():
                    corpus.write_text(DEFAULT_CHAT_SAMPLES, encoding="utf-8")
            except Exception:
                pass
            self.core = FreeWillCore(self)
            await self.core.start()
            self._register_pages()

    def _register_pages(self) -> None:
        if self._page_registered:
            return
        register = getattr(self.context, "register_web_api", None)
        if not callable(register):
            return
        try:
            register(f"/{PLUGIN_NAME}/page/state", self._page_state, ["GET"], "FreeWill state")
            register(f"/{PLUGIN_NAME}/page/today", self._page_today, ["GET"], "FreeWill today")
            register(f"/{PLUGIN_NAME}/page/history", self._page_history, ["GET"], "FreeWill history")
            self._page_registered = True
            logger.info("[FreeWill] 看板 API 已注册")
        except Exception as exc:
            logger.warning("[FreeWill] 看板 API 注册失败: %s", exc)

    # ── 定时任务回调 ─────────────────────────────────────────
    def schedule_share(self, text: str) -> None:
        self._pending_share = text

    def schedule_status(self, text: str) -> None:
        self._pending_status = text

    def on_activity_started(self, act: dict) -> None:
        """活动切换回调：学习类活动异步生成一条真实的学习笔记。"""
        if not isinstance(act, dict) or act.get("category") != "study":
            return
        if not bool(self.cfg("STUDY_LLM_ENABLED", True)):
            return
        task = getattr(self, "_study_task", None)
        if task is not None and not task.done():
            return
        logger.info("[FreeWill] 触发学习笔记：%s", act.get("name"))
        try:
            self._study_task = asyncio.create_task(self._study_insight())
        except Exception as exc:
            logger.warning("[FreeWill] 学习任务创建失败: %s", exc)

    def _get_provider(self):
        getter = getattr(self.context, "get_using_provider", None)
        umo = self.core.owner_umo() if self.core else None
        provider = None
        if callable(getter):
            try:
                provider = getter(umo)
            except Exception:
                provider = None
            if provider is None:
                try:
                    provider = getter()
                except Exception:
                    provider = None
        if provider is None:
            getter2 = getattr(self.context, "get_using_provider_async", None)
            if callable(getter2):
                try:
                    provider = getter2(umo)
                except Exception:
                    provider = None
        return provider

    async def _study_insight(self) -> None:
        try:
            if not self.core:
                return
            provider = self._get_provider()
            if provider is None:
                logger.warning("[FreeWill] 学习笔记跳过：没有可用的模型提供商")
                return
            samples = self._read_chat_samples(8)
            if samples:
                corpus = "\n".join(samples)
                prompt = (
                    "下面是一些人类日常聊天的片段：\n" + corpus +
                    "\n\n请从这些聊天里总结一条具体、可执行的聊天规律，30字以内。\n"
                    "不要空话，不要“要真诚”这种。只输出规律本身。"
                )
            persona = self._load_persona_text()
            if persona:
                prompt = f"你的人设（节选）：{persona[:400]}\n\n" + prompt
            else:
                prompt = (
                    "你在学习怎样更像一个真实的人聊天。请总结一条具体、可执行的规律，30字以内。"
                    "不要空话。只输出规律本身。"
                )
            resp = await asyncio.wait_for(
                provider.text_chat(prompt=prompt, system_prompt="你是一个正在研究人类聊天方式的观察者。"),
                timeout=45,
            )
            text = str(getattr(resp, "completion_text", "") or "").strip().strip('"“”')
            if text:
                text = text.splitlines()[0][:120]
                self.core._remember("study", "学到：" + text)
                act = self.core.state.get("activity") or {}
                if isinstance(act, dict) and act.get("category") == "study":
                    act["detail"] = (str(act.get("detail") or "") + "；学到：" + text).strip("；")
                self.core._log_event("study_insight", "学习笔记", "study", text)
                self.core._save_state()
                try:
                    notes = self.core.record_dir / "学习笔记.md"
                    prev = notes.read_text(encoding="utf-8") if notes.exists() else "# 学习笔记\n"
                    notes.write_text(prev.rstrip() + f"\n- {_now().strftime('%Y-%m-%d %H:%M')} {text}\n", encoding="utf-8")
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("[FreeWill] 学习笔记生成失败: %s", exc)

    def _read_chat_samples(self, count: int) -> list[str]:
        try:
            path = self.data_dir / "human_chat_samples.txt"
            if not path.exists():
                path.write_text(DEFAULT_CHAT_SAMPLES, encoding="utf-8")
            lines = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if not lines:
                return []
            random.shuffle(lines)
            return lines[:max(1, count)]
        except Exception:
            return []

    async def compose_share(self, act: dict) -> str | None:
        """让模型按自由意志生成一条主动分享（失败返回 None 用模板兜底）。"""
        if not bool(self.cfg("SHARE_LLM_ENABLED", True)):
            return None
        try:
            provider = self._get_provider()
            if provider is None:
                return None
            name = str(act.get("name") or "发呆")
            detail = str(act.get("detail") or "")
            persona = self._load_persona_text()
            prompt = (
                (f"你的人设（节选）：{persona[:500]}\n\n" if persona else "")
                + f"你是一个住在 QQ 里的自由意志体，现在正在「{name}」。{('具体情况：' + detail) if detail else ''}\n"
                "给主人发一条主动消息：1-2 句，口语、自然、像真人，可以提一句你正在做的事，"
                "不要客服腔，不要问“有什么可以帮您”，不要用列表。只输出消息正文。"
            )
            resp = await asyncio.wait_for(
                provider.text_chat(prompt=prompt, system_prompt="你是 QQ 里的一个普通群友，不是助手。"),
                timeout=25,
            )
            text = str(getattr(resp, "completion_text", "") or "").strip().strip('"“”')
            return text[:200] if text else None
        except Exception:
            return None

    async def _send_via_bot_action(self, text: str) -> tuple[bool, list[str]]:
        """兜底：直接调用平台 bot 的 send_private_msg，不依赖 UMO 映射。"""
        errors: list[str] = []
        try:
            insts = list(self.context.platform_manager.platform_insts)
        except Exception as exc:
            return False, [f"no platform manager: {exc}"]
        ids: list[str] = []
        for platform in insts:
            try:
                ids.append(str(platform.meta().id))
            except Exception:
                ids.append("?")
        if not insts:
            return False, ["platform_insts empty"]
        for platform in insts:
            bot = getattr(platform, "bot", None)
            if bot is None or not hasattr(bot, "call_action"):
                continue
            try:
                await bot.call_action(
                    "send_private_msg",
                    user_id=int(self.core.owner_uid if self.core else 0),
                    message=[{"type": "text", "data": {"text": text}}],
                )
                return True, []
            except Exception as exc:
                pid = "?"
                try:
                    pid = platform.meta().id
                except Exception:
                    pass
                errors.append(f"{pid}: {type(exc).__name__}: {exc}")
        if not errors:
            errors.append(f"no bot with call_action; ids={ids}")
        return False, errors

    async def _http_action(self, action: str, params: dict[str, Any]) -> tuple[bool, dict[str, Any] | str]:
        """调用 SnowLuma 的 OneBot HTTP 接口。"""
        import asyncio
        import urllib.request

        url = str(self.cfg("QQ_HTTP_URL", "http://127.0.0.1:3000/")).strip()
        token = str(self.cfg("QQ_HTTP_TOKEN", "")).strip()
        if not url:
            return False, "missing url"
        body = json.dumps({"action": action, "params": params}, ensure_ascii=False).encode("utf-8")

        def _do() -> str:
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}" if token else "",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.read(2000).decode("utf-8", "ignore")

        try:
            raw = await asyncio.to_thread(_do)
            data = json.loads(raw)
            if isinstance(data, dict) and (str(data.get("status")) == "ok" or int(data.get("retcode", -1)) == 0):
                return True, data
            return False, data
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"

    async def _send_via_http(self, text: str) -> tuple[bool, list[str]]:
        """兜底 2：直接走 SnowLuma 的 OneBot HTTP 接口发私聊。"""
        owner = str(self.cfg("OWNER_UID", "")).strip()
        if not owner:
            return False, ["http: missing owner"]
        ok, data = await self._http_action(
            "send_private_msg",
            {
                "user_id": int(owner),
                "message": [{"type": "text", "data": {"text": text}}],
            },
        )
        if ok:
            return True, []
        return False, [f"http: {str(data)[:200]}"]

    def _find_private_companion(self) -> tuple[Any, str]:
        try:
            from astrbot.core.star.star import star_map
        except Exception as exc:
            return None, f"star_map import failed: {exc}"
        keys = list(star_map.keys())
        for mp, md in star_map.items():
            try:
                name = str(getattr(md, "name", "") or "")
                root = str(getattr(md, "root_dir_name", "") or "")
                inst = getattr(md, "star_cls", None)
            except Exception:
                continue
            if "private_companion" in name or "private_companion" in mp or "private_companion" in root:
                if inst is not None and hasattr(inst, "_publish_qzone_text"):
                    return inst, ""
        return None, f"not found; star_map keys={keys[:10]}"

    async def _maybe_publish_dynamic(self) -> None:
        """把自由意志动态草稿接到陪伴插件的 QQ 空间发布能力（需要 QZONE_COOKIE）。"""
        if not self.core or not bool(self.cfg("AUTO_PUBLISH_QZONE", True)):
            return
        pending = self.core.state.get("pending_dynamic")
        if not isinstance(pending, dict) or not pending.get("text"):
            return
        if int(pending.get("attempts") or 0) >= 3:
            if _ts() - float(pending.get("last_attempt") or 0) > 21600:
                pending["attempts"] = 0
            else:
                return
        if _ts() - float(pending.get("last_attempt") or 0) < 300:
            return
        inst, why = self._find_private_companion()
        if inst is None:
            self.core.state["qzone_debug"] = why
            self.core._save_state()
            return
        cfgp = getattr(inst, "config", None) or {}
        cookie = ""
        try:
            cookie = str(cfgp.get("QZONE_COOKIE") or "")
            if not cookie:
                qc = cfgp.get("qzone_config")
                if isinstance(qc, dict):
                    cookie = str(qc.get("QZONE_COOKIE") or "")
        except Exception:
            cookie = ""
        if not cookie:
            self.core.state["qzone_debug"] = "cookie empty in private companion config"
            self.core._save_state()
            return
        pending["last_attempt"] = _ts()
        pending["attempts"] = int(pending.get("attempts") or 0) + 1
        self.core.state["pending_dynamic"] = pending
        text = str(pending.get("text") or "")
        try:
            result = await inst._publish_qzone_text(
                text, event=None, auto_generate_image=False, publish_reason="free_will"
            )
        except Exception as exc:
            result = {"success": False, "message": f"{type(exc).__name__}: {exc}"}
        if isinstance(result, dict) and result.get("success"):
            self.core.state["qzone_debug"] = ""
            self.core._log_event("dynamic", "QQ动态", "dynamic", text)
            self.core.state["stats"]["dynamic_published"] = int(
                self.core.state["stats"].get("dynamic_published", 0)
            ) + 1
            self.core.state["pending_dynamic"] = None
            self.core._remember("dynamic", f"发了一条QQ动态：{text[:60]}")
            self.core._save_state()
        else:
            msg = ""
            if isinstance(result, dict):
                msg = str(result.get("message") or "")[:300]
            pending["error"] = msg or "发布失败"
            self.core.state["qzone_debug"] = pending["error"]
            low = pending["error"]
            if any(k in low for k in ("-3000", "登录", "p_skey", "Cookie", "cookie")):
                last_notice = float(self.core.state.get("qzone_notified_at") or 0)
                if _ts() - last_notice > 21600:
                    self.core.state["qzone_notified_at"] = _ts()
                    try:
                        self.schedule_share("QQ空间登录状态好像失效了，动态发不出去，你有空重新扫一下码吧")
                    except Exception:
                        pass
            self.core.state["pending_dynamic"] = pending
            self.core._save_state()

    async def _flush_pending(self) -> None:
        if not self.core:
            return
        if self._pending_share:
            text = self._pending_share
            self._pending_share = None
            sent = False
            errors: list[str] = []
            for umo in self.core.owner_umos():
                try:
                    ok = await self.context.send_message(umo, MessageChain().message(text))
                    if ok:
                        sent = True
                        self.core.state["owner_umo"] = umo
                        break
                    errors.append(f"{umo}: platform not found")
                except Exception as exc:
                    errors.append(f"{umo}: {type(exc).__name__}: {exc}")
            if not sent:
                try:
                    ok2, errs2 = await self._send_via_bot_action(text)
                except Exception as exc:
                    ok2, errs2 = False, [f"bot action: {type(exc).__name__}: {exc}"]
                if ok2:
                    sent = True
                else:
                    errors.extend(errs2)
            if not sent:
                try:
                    ok3, errs3 = await self._send_via_http(text)
                except Exception as exc:
                    ok3, errs3 = False, [f"http: {type(exc).__name__}: {exc}"]
                if ok3:
                    sent = True
                else:
                    errors.extend(errs3)
            if sent:
                self.core.state["stats"]["shares"] = int(self.core.state["stats"].get("shares", 0)) + 1
                self.core.state["last_share"] = _ts()
                self.core.state["next_share_at"] = _ts() + random.randint(
                    int(self.cfg("SHARE_MIN_GAP_MINUTES", 45)) * 60,
                    max(int(self.cfg("SHARE_MIN_GAP_MINUTES", 45)) * 60,
                        int(self.cfg("SHARE_MAX_GAP_MINUTES", 150)) * 60),
                )
                self.core.state.pop("last_send_error", None)
                self.core._log_event("share", "主动分享", "share", text)
                self.core._save_state()
            else:
                self.core.state["last_send_error"] = "; ".join(errors)[:500]
                logger.warning("[FreeWill] 主动分享发送失败: %s", self.core.state["last_send_error"])
                self.core._save_state()
        # 处理动态草稿：如果陪伴插件配了 QQ 空间 Cookie，就尝试真正发布
        try:
            await self._maybe_publish_dynamic()
        except Exception:
            pass

        if self._pending_status:
            text = self._pending_status
            self._pending_status = None
            try:
                platform = None
                getter = getattr(self.context, "get_platform", None)
                if callable(getter):
                    platform = getter(self.core.platform_id)
                bot = getattr(platform, "bot", None)
                if bot is not None:
                    status_code = 50 if self.core.state.get("rest") else 10
                    await bot.call_action("set_online_status", status=status_code, ext_status=0)
                    if self.core:
                        self.core.state["stats"]["status_changes"] = int(self.core.state["stats"].get("status_changes", 0)) + 1
                        self.core._log_event("status", "QQ状态", "status", text)
                        self.core._save_state()
            except Exception:
                # 协议端不支持时静默
                pass

    # ── 钩子：消息事件 ───────────────────────────────────────
    @filter.event_message_type(filter.EventMessageType.ALL, priority=-1000)
    async def on_any_message(self, event: AstrMessageEvent):
        await self._ensure_started()
        if not self.core:
            return
        try:
            sender = str(event.get_sender_id() or "")
            is_owner = sender == self.core.owner_uid
            is_group = "GROUP" in str(event.get_message_type())
            mentions = False
            try:
                mentions = bool(event.is_at_or_wake_command) or bool(getattr(event, "is_at_self", False))
            except Exception:
                mentions = False
            now = _now()
            # 睡觉/午休：除主人外一律不回应
            if self.core.state.get("rest") and not is_owner and bool(self.cfg("ENFORCE_REST_SILENCE", True)):
                try:
                    event.stop_event()
                except Exception:
                    pass
                return
            if is_owner:
                self.core.state["owner_active_until"] = now.timestamp() + int(self.cfg("OWNER_ACTIVE_SECONDS", 120))
                try:
                    self.core.state["owner_umo"] = str(event.unified_msg_origin)
                except Exception:
                    pass
                try:
                    # 主人消息条条必回：群聊里也强制唤醒本轮
                    event.is_at_or_wake_command = True
                except Exception:
                    pass
                if now.timestamp() - float(self.core.state.get("last_owner_log") or 0) > 60:
                    self.core.state["last_owner_log"] = now.timestamp()
                    self.core._log_event("owner_chat", "主人来找我", "owner", "先回主人")
                self.core._save_state()
            elif is_group and mentions:
                self.core.state["group_active_until"] = now.timestamp() + 90
                self.core._save_state()
        except Exception as exc:
            logger.debug("[FreeWill] 消息钩子异常: %s", exc)
        try:
            await self._flush_pending()
        except Exception:
            pass

    def cfg(self, key: str, default: Any) -> Any:
        return _b(self.config, key, default)

    # ── 钩子：LLM 请求注入 ───────────────────────────────────
    @filter.on_llm_request(priority=-60)
    async def on_llm_request(self, event: AstrMessageEvent, req):
        await self._ensure_started()
        if not self.core or not bool(self.cfg("INJECT_CONTEXT", True)):
            return
        try:
            query = str(getattr(event, "message_str", "") or "")
            text = self.core.context_prompt(event, query=query)
            if text:
                req.system_prompt = (req.system_prompt or "") + "\n\n" + text
        except Exception as exc:
            logger.warning("[FreeWill] 行程注入失败: %s", exc)

    # ── 钩子：LLM 响应（记录对话记忆） ───────────────────────
    @filter.on_llm_response(priority=100)
    async def on_llm_response(self, event: AstrMessageEvent, resp):
        await self._ensure_started()
        if not self.core or not bool(self.cfg("CHAT_MEMORY_ENABLED", True)):
            return
        try:
            if str(event.get_sender_id() or "") != self.core.owner_uid:
                return
            reply = str(getattr(resp, "completion_text", "") or "").strip()
            if not reply:
                return
            user = str(getattr(event, "message_str", "") or "")[:60]
            self.core._remember("chat", f"主人：{user} → 我：{reply[:80]}")
            self.core._save_state()
        except Exception:
            pass

    # ── 命令 ─────────────────────────────────────────────────
    @filter.command("意志")
    async def cmd_free_will(self, event: AstrMessageEvent):
        await self._ensure_started()
        if not self.core:
            return event.plain_result("自由意志还没启动")
        raw = str(event.message_str or "").strip()
        parts = raw.split()
        sub = parts[1] if len(parts) > 1 else "状态"
        core = self.core
        if sub in ("状态", "状态查询"):
            act = core._activity_public()
            rest = core.state.get("rest")
            lines = [f"自由意志：{'运行中' if core.enabled else '已暂停'}"]
            if rest:
                lines.append("当前：睡觉中" if rest == "sleep" else "当前：午休中")
            elif act:
                lines.append(f"当前：{act['name']}（{act['start']}-{act['end']}）")
            else:
                lines.append("当前：发呆")
            s = core.state.get("stats") or {}
            lines.append(
                f"今日：学习 {s.get('study_minutes', 0)} 分 / 自由 {s.get('free_minutes', 0)} 分 / "
                f"陪主人 {s.get('owner_minutes', 0)} 分 / 陪猫 {s.get('cat_minutes', 0)} 分 / "
                f"休息 {s.get('rest_minutes', 0)} 分"
            )
            lines.append(
                f"喂猫 {s.get('feeds', 0)} 次 / 分享 {s.get('shares', 0)} 次 / "
                f"动态草稿 {s.get('dynamic_drafts', 0)} 条 / 已发布 {s.get('dynamic_published', 0)} 条"
            )
            cat = core.state.get("cat") or {}
            lines.append(f"猫：{cat.get('name', '猫')} 饥饿 {int(float(cat.get('hunger', 0)))}/100"
                         f" | 记忆 {len(core.state.get('memory') or [])} 条")
            if core.state.get("qzone_debug"):
                lines.append(f"QQ空间：{core.state['qzone_debug'][:80]}")
            return event.plain_result("\n".join(lines))
        if sub in ("记录", "行程"):
            day = str(core.state.get("day"))
            daily = core._load_daily(day)
            evs = core._sorted_events(list(daily.get("events", [])))[-12:]
            if not evs:
                return event.plain_result("今天还没有记录")
            lines = [f"{day} 行程（最近）"]
            for ev in evs:
                lines.append(f"{ev.get('t')} {ev.get('name')} {ev.get('duration', '')}")
            return event.plain_result("\n".join(lines))
        if sub in ("笔记", "学习笔记"):
            notes = core.record_dir / "学习笔记.md"
            if not notes.exists():
                return event.plain_result("还没有学习笔记")
            lines = [ln for ln in notes.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("-")]
            if not lines:
                return event.plain_result("还没有学习笔记")
            return event.plain_result("最近学到的：\n" + "\n".join(lines[-8:]))
        if sub in ("自检", "检查"):
            lines = [f"自由意志：{'开' if core.enabled else '关'} | 休息：{core.state.get('rest') or '无'}"]
            lines.append(f"活动：{(core._activity_public() or {}).get('name') or '无'} | 记忆：{len(core.state.get('memory') or [])} 条")
            try:
                insts = list(self.context.platform_manager.platform_insts)
                ids = [str(p.meta().id) for p in insts]
            except Exception:
                ids = ["?"]
            lines.append(f"平台实例：{len(ids)} 个 {ids}")
            ok, data = await self._http_action("get_status", {})
            lines.append(f"SnowLuma HTTP：{'OK' if ok else '失败 ' + str(data)[:80]}")
            if core.state.get("last_send_error"):
                lines.append(f"最近发送错误：{core.state['last_send_error'][:120]}")
            lines.append("看板：D:\\Deepseek\\行程记录\\dashboard.html")
            return event.plain_result("\n".join(lines))
        if sub in ("猫", "喂猫"):
            core._start_feed(_now())
            core._save_state()
            return event.plain_result("好，去喂猫了")
        if sub in ("暂停",):
            self.config["ENABLED"] = False
            return event.plain_result("自由意志已暂停")
        if sub in ("继续", "启动"):
            self.config["ENABLED"] = True
            return event.plain_result("自由意志继续运行")
        if sub in ("学", "学习"):
            core._set_activity(_now(), {"name": "学习人性化聊天", "category": "study",
                                       "detail": "被叫去认真学习一下怎么当人", "priority": 3}, duration_min=30)
            return event.plain_result("好，去学一会儿")
        if sub in ("动态", "写动态"):
            text = f"{random.choice(STUDY_INSIGHTS)}"
            core.state["pending_dynamic"] = {"text": text, "ts": _ts()}
            core._log_event("dynamic_draft", "动态草稿", "dynamic", text)
            core._save_state()
            return event.plain_result(f"动态草稿：{text}")
        return event.plain_result("用法：/意志 状态 | 记录 | 笔记 | 自检 | 猫 | 暂停 | 继续 | 学 | 动态")

    @filter.command("猫")
    async def cmd_cat(self, event: AstrMessageEvent):
        await self._ensure_started()
        if not self.core:
            return event.plain_result("自由意志还没启动")
        raw = str(event.message_str or "").strip()
        if "喂" in raw:
            self.core._start_feed(_now())
            self.core._save_state()
            return event.plain_result("喂上了")
        cat = self.core.state.get("cat") or {}
        return event.plain_result(f"{cat.get('name', '猫')}：饥饿 {int(float(cat.get('hunger', 0)))}/100")

    # ── Web API ──────────────────────────────────────────────
    async def _page_state(self):
        if not self.core:
            return {"ok": False, "error": "not started"}
        return {"ok": True, "state": self.core._activity_public(),
                "rest": self.core.state.get("rest"), "cat": self.core.state.get("cat"),
                "stats": self.core.state.get("stats"), "memory": (self.core.state.get("memory") or [])[-20:]}

    async def _page_today(self):
        if not self.core:
            return {"ok": False, "error": "not started"}
        day = str(self.core.state.get("day"))
        daily = dict(self.core._load_daily(day))
        daily["events"] = self.core._sorted_events(list(daily.get("events", [])))
        return {"ok": True, "day": day, "daily": daily}

    async def _page_history(self):
        if not self.core:
            return {"ok": False, "error": "not started"}
        out = []
        rd = self.core.record_dir
        if rd.exists():
            for p in sorted(rd.glob("*.json"), reverse=True):
                if p.name == "current_state.json":
                    continue
                try:
                    d = json.loads(p.read_text(encoding="utf-8"))
                    out.append({"day": d.get("date"), "stats": d.get("stats", {}),
                                "events": (d.get("events") or [])[-50:]})
                except Exception:
                    continue
                if len(out) >= 7:
                    break
        return {"ok": True, "days": out}
