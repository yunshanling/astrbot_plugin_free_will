# 自由意志核心（astrbot_plugin_free_will）

给 AstrBot 的 QQ 机器人加一个「常驻自由意志」：即使没人聊天，它也会按自己的作息安排活动、记行程、养猫、学习怎么和人聊天，偶尔主动找主人分享，写 QQ 空间动态。

> 这是一个「行为调度层」插件：负责日程/优先级/记录/注入上下文，不替代 AstrBot 的人设与对话能力。

## 功能

- **常驻脚本**：独立 asyncio 任务，与会话解耦；状态持久化，重启续跑。
- **作息**：默认 23:00–07:00 睡觉、11:55–13:55 午休；休息时只有主人能叫醒，其他人消息静默。
- **优先级**：主人会话(1) > 猫状态(2) > 自由意志(3) > 其它(4)。
- **行程记录**：按日生成 `YYYY-MM-DD.md` / `.json`，每条带 `HH:MM`；同时生成 `dashboard.html` 可视化看板（统计卡片 + 时间线）。
- **每日重置**：睡醒后新建当天统计，并写昨日总结。
- **养猫**：饥饿值随时间增长，≥阈值自动插入「喂猫」，喂完继续自己的事。
- **学习人性**：约一半清醒时间用于学习；从本地语料抽样，让模型总结具体聊天规律，写入记忆与 `学习笔记.md`。
- **主动分享**：按间隔/概率主动私聊主人；优先走 AstrBot 平台，失败自动降级到 OneBot HTTP。
- **聊天上下文**：`on_llm_request` 注入「当前在干嘛 + 最近行程 + 相关记忆 + 猫」，聊天时优先结合行程。
- **QQ 动态**：按自由意志生成草稿（每天最多 N 条、间隔至少 M 分钟）；若陪伴插件配置了有效 `QZONE_COOKIE`，可自动发布到 QQ 空间。
- **联动接口**：其它插件可读 `current_state.json`，或写 `external_activity.json` 投递活动。

## 安装

1. 把本目录放进 AstrBot 的 `data/plugins/astrbot_plugin_free_will/`。
2. 重启 AstrBot，在插件配置里填 **主人 QQ 号**（`OWNER_UID`）和行程记录目录（`RECORD_DIR`）。
3. 如需语音/空间等联动，按需开启对应配置。

要求：AstrBot >= 4.22。

## 命令

- `/意志 状态` — 当前活动、今日统计、猫、动态
- `/意志 记录` — 最近行程
- `/意志 笔记` — 最近学习笔记
- `/意志 自检` — 平台/HTTP/发送错误自检
- `/意志 猫` / `/意志 喂猫`
- `/意志 学` — 立刻去学习
- `/意志 暂停` / `/意志 继续`
- `/意志 动态` — 生成一条动态草稿
- `/猫` — 看猫；`/猫 喂` — 喂猫

## 关键配置

| 键 | 说明 |
|---|---|
| `OWNER_UID` | 主人 QQ 号（必填） |
| `RECORD_DIR` | 行程记录目录，默认 `行程记录` |
| `SLEEP_START` / `SLEEP_END` | 睡觉时段 |
| `NAP_START` / `NAP_END` | 午休时段 |
| `HUMAN_LEARNING_RATIO` | 学习人性占比目标（默认 0.5） |
| `CAT_ENABLED` / `CAT_FEED_THRESHOLD` | 养猫与喂食阈值 |
| `PROACTIVE_SHARE_ENABLED` / `SHARE_*` | 主动分享开关与间隔/概率 |
| `QQ_HTTP_URL` / `QQ_HTTP_TOKEN` | OneBot HTTP 兜底发送（可选） |
| `DYNAMIC_DAILY_MAX` / `DYNAMIC_MIN_GAP_MINUTES` | 每天动态上限 / 最小间隔 |
| `AUTO_PUBLISH_QZONE` | 草稿自动发布到 QQ 空间（需陪伴插件 Cookie） |
| `PERSONA_ID` | 使用哪个人设（留空自动取最近更新的人设） |

## 与其它插件联动

- 读当前状态：`<RECORD_DIR>/current_state.json`
- 投递活动：写 `<RECORD_DIR>/external_activity.json`，例如：

```json
{"plugin": "astrbot_plugin_xxx", "name": "处理一条私信", "category": "social", "detail": "有群友来问事情", "minutes": 10}
```

- QQ 空间发布依赖陪伴插件（`astrbot_plugin_private_companion`）的 `QZONE_COOKIE`，本插件自身不保存 Cookie。

## 文件

- `main.py` — 调度核心 + 插件钩子
- `_conf_schema.json` — 配置定义
- `pages/free-will/index.html` — 插件页看板
- `metadata.yaml` — AstrBot 插件元信息

## 说明

- 仓库中不包含任何账号、Cookie、Token 或运行数据；首次使用请自行填写 `OWNER_UID`。
- 欢迎按需修改活动池、语料与提示词；`human_chat_samples.txt` 会在首次运行时自动生成，可自行追加真实聊天片段。

## License

MIT，见 `LICENSE`。
