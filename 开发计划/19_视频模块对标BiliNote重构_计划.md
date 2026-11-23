# 19 · 视频解析模块重构（对标 BiliNote）+ 火山方舟接入 · 执行计划

> 目标：把「视频 → 笔记」这条链路做到**能用、够快、笔记像样**，并按 BiliNote 的产品形态重构视频页。
> 本文只写**可验证的事实**：已实测的数字、已确认可用的模型、可落地的方案。**待你确认后才动代码。**
> 测试视频：`BV1YPsJ6BEPx`（肖八带刷逐题精讲，**16 个分 P，总 7.4 小时**）

---

## 0. 结论先行（三句话）

1. **你的视频打不开、慢、笔记差，不是模型不行**：根因是「取材方式」错了——我们在本机跑 Whisper，而 BiliNote 走的是 **B 站官方字幕 → 必剪云转写 → 本地兜底**三级链，第一级 0 秒，第二级实测 **RTF 0.028**（比我们并行 Whisper 还快 3 倍且不吃本机 CPU）。
2. **笔记质量差是「结构」问题**：我们让模型吐 JSON 再渲染，长视频必崩/必截断；BiliNote 让模型**直接写 Markdown**，并用 `*Content-[mm:ss]` / `*Screenshot-[mm:ss]` 两个标记做时间轴和插图，**没有 JSON 可崩**。
3. **火山方舟能用，但只有 4 个模型真正开通**：`deepseek-v4-1-flash` / `-economy` / `deepseek-v4-pro-ga` / `kimi-k3-1-pro`。doubao 全系（含 seed-2-1 视觉）**当前账号未开通**，所以视觉 OCR 走 `deepseek-v4-1-flash`（实测 **13.2s/张**，现在我们是 **125s**）。

---

## 1. 火山方舟：模型清单与真实可用性

### 1.1 API 与鉴权
- Models 列表：`GET https://ark.cn-beijing.volces.com/api/v3/models`（已实测，返回 **55 个**）
- 对话：`POST /api/v3/chat/completions`（OpenAI 兼容）
- Key 只写入 `gflc/backend/.env`（已在 `.gitignore`），不写进任何文档/代码/镜像。

### 1.2 ⚠️ 第一个坑：列出来的 ≠ 开通的

`/models` 返回 55 个，但实际调用逐个探测后，**只有 4 个返回 200**：

| 模型 ID | 状态 | 实测延迟（20 token 回答） | 多模态 |
|---|---|---|---|
| `deepseek-v4-1-flash-261017` | ✅ 可用 | 18.0s | text+image+video，1M ctx，json_schema |
| `deepseek-v4-1-flash-economy-261017` | ✅ 可用 | 19.8s | 同上（更便宜） |
| `deepseek-v4-pro-ga-260813` | ✅ 可用 | 21.2s | 纯文本，1M ctx |
| `kimi-k3-1-pro-261024` | ✅ 可用 | 19.5s | text+image+video，1M ctx |
| `doubao-seed-2-1-pro/lite/turbo-*` | ❌ 404 未开通 | — | — |
| `glm-5-3-flash / qwen3-* / deepseek-v4-flash-ga` | ❌ 404 / 不存在 | — | — |

> 未开通的模型需要你在方舟控制台「开通管理」里授权，否则一律 404 `has not activated the model`。

### 1.3 关键实测：视觉识图（这决定图文笔记快不快）

同一张 4×3 关键帧拼图（233KB base64），要求逐格识别板书文字：

| 模型 | 延迟 | 输出质量 |
|---|---|---|
| **`deepseek-v4-1-flash`**（thinking=disabled） | **13.2s** | 12 格全部命中，公式正确（`F_T(t)=1-e^{-λt}`、`P(N(t)=1)=λte^{-λt}`） |
| `kimi-k3-1-pro` | 22.0s | 12 格命中，细节更多 |
| 现有（DeepSeek 官方 key，light 档） | **~100–125s** | 可用但慢 8–10 倍 |

### 1.4 推荐配置

```ini
# 笔记生成（长文 Markdown 直出，1M 上下文，不再截断转写）
NOTE_MODEL=deepseek-v4-1-flash-261017        # 或 -economy 省钱
# 视觉识图（拼图 OCR / 截图理解）
VISION_MODEL=deepseek-v4-1-flash-261017
# 备用/长文理解
LONG_MODEL=kimi-k3-1-pro-261024
# 全部走方舟
ARK_BASE=https://ark.cn-beijing.volces.com/api/v3
```

配套注意：方舟这几个都是**推理模型**（返回 `reasoning_content`），必须 `thinking: {"type":"disabled"}` 或 `reasoning_effort=low`，否则正文被思考 token 吃光——这个坑我们 README 里已经记过一次。

---

## 2. BiliNote 逆向：它为什么快、为什么笔记像样

MIT 许可（可复用代码，需保留版权声明；不复制其品牌、截图、文档文案与 Pro 版引导）。

| 机制 | 它的做法 | 我们的现状 | 差距 |
|---|---|---|---|
| **M1 取材三级链** | ① B站 `player/wbi/v2` 直拉官方/AI 字幕（**不下载视频**）② 必剪 bcut 云转写 ③ 本地 whisper / Groq | 只有本地 whisper（今天已改并行，RTF 0.09） | **决定量级** |
| **M2 必剪云转写** | 上传音频到 `member.bilibili.com/x/bcut/...`，免费、免登录、云端识别 | 无 | 实测可用 ↓ |
| **M3 Markdown 直出** | 提示词要求直接输出 Markdown，`##` 标题后附 `*Content-[mm:ss]` | 输出 JSON → 渲染，长文必截断 | 重构生成层 |
| **M4 截图占位** | 模型在需要图示处写 `*Screenshot-[mm:ss]`，后处理正则提取时间点 → ffmpeg 精确抽帧 → 替换成图片 | 网格拼图 + 视觉 OCR（2 次 100s） | 更快更准 |
| **M5 单页三段式 UI** | 左「表单」/ 中「Markdown 预览」/ 右「历史」，顶部 StepBar 显示 下载→转写→总结 | 10 页分散，视频页是上传表单 | 复刻视频页 |
| **M6 任务轮询 + 状态机** | 3s 轮询 + PENDING/PARSING/DOWNLOADING/TRANSCRIBING/SUMMARIZING 状态 | 已有 task + stage_timeline | 复用即可 |

### 2.1 必剪（bcut）实测结果（我刚跑通）

| 音频 | 耗时 | RTF | 结果 |
|---|---|---|---|
| 13s 教学音频 | 6.2s | — | 6 段，术语识别正确（「间隔重复」「遗忘曲线」） |
| **4.5 分钟音频** | **7.6s** | **0.028** | 112 段 |
| 折算 27 分钟视频 | **≈ 45s** | | 免费、免登录、**不占本机 CPU** |

### 2.2 测试视频的字幕情况（重要）

刚用 B 站公开 API 查了 `BV1YPsJ6BEPx`：`subtitle.subtitles = []`（**无字幕**，且 AI 字幕需 `SESSDATA` 登录 cookie）。
→ 这条视频**只能走必剪云转写或本地 ASR**，正好验证 M2 的价值。

---

## 3. 现状差距（今天实测，31 分钟视频）

| 环节 | 现状 | 目标 | 差距 |
|---|---|---|---|
| 取材 | 107s（并行 whisper） | 字幕 0–3s / 必剪 ~45s | 2.4–35× |
| 笔记外观 | 生成 24s，但是「摘要/大纲/问答」三份分离卡片 | 单篇 Markdown，带时间戳可跳转 | 形态不对 |
| 图文 | 抽帧 22s + 视觉 OCR **125s** + 生成 14s | Ark VLM 13s×2 并发 + 按点抽帧 | **5–8×** |
| **视频播放** | ❌ 打不开：`documents.mime = 'video/*'`（非法通配）+ 早期 URL 导入存的是**纯音频**（42/84MB 无扩展名文件） | 存 480p mp4、正确 `video/mp4`、Range 可拖 | 修 3 处 |
| 16P 合集 | 只取单 P（`noplaylist`），但 UI 没告诉用户「这是第 1/16 集」 | 显示分 P 列表，默认当前 P，可「批量整季」 | 新增 |

---

## 4. 目标架构 v2（只换三段，不动数据层）

```
URL ──▶ [L1 取材路由]  B站? ─┬─ 有字幕(cookie) ──▶ 字幕 API        0–3s
                             ├─ 无字幕 ─────────▶ 必剪云转写      ~45s/27min
                             └─ 失败/非B站 ──────▶ Whisper 并行   已在用(兜底)
                                        │
                                        ▼ segments(ts) 全量（不再截断）
                    [L2 生成] Markdown 直出（流式）
                         · 提示词：## 标题 + *Content-[mm:ss] + *Screenshot-[mm:ss]
                         · 模型：Ark deepseek-v4-1-flash（1M ctx，无需采样压缩）
                                        │
                          ┌─────────────┴──────────────┐
                          ▼                            ▼
              [L3a 流式展示] 首字 ≤8s          [L3b 图文后处理]
              SSE/轮询增量渲染                 正则提取截图点 → ffmpeg -ss 精确抽帧
                                              → 替换标记为 <img>（本地 /api/... 可达）
                                        │
                                        ▼
                    [L4 播放] 480p mp4 落存储 + video/mp4 + Range
```

**关键设计取舍**
- 保留现有 `Task` 状态机 / `stage_timeline` / checkpoint 续跑机制（这部分我们已经比 BiliNote 强）。
- 生成层从「JSON + 三模板」改为「Markdown 单篇 + 标记」，**旧的三模板笔记保留为兼容路径**（`?templates=legacy`）。
- 截图走「按点抽帧」，废弃「网格拼图 + 视觉 OCR」作主链路（保留为兜底：视频无画面/纯音频时）。

---

## 5. 分阶段计划

### P0 · 打通「能播、有字、有图」（1 个工作段，可独立验收）
1. 接入火山方舟 provider（`ARK_BASE` + 4 个已开通模型映射 + thinking 关闭）
2. 取材三级路由：字幕 → 必剪 → whisper（配置开关，默认按序降级）
3. 下载改 480p mp4 并**落库可播**：修 `mime`、扩展名、`storage_key`、Range
4. 视觉 OCR 换 `deepseek-v4-1-flash`（125s → ~15s）
5. 分 P 识别：UI 显示「第 N/16 集」，默认当前 P

### P1 · 复刻视频页（1 个工作段）
6. 视频页重构为 BiliNote 三段式：左表单 / 中 Markdown 预览 / 右历史，顶部 StepBar（下载→转写→生成→图文）
7. Markdown 直出 + 流式渲染；`[mm:ss]` 可点击跳转播放器
8. `*Screenshot-[mm:ss]` → 抽帧插图
9. 讲稿全文 tab（带时间戳）、复制/导出 Markdown

### P2 · 质量与稳定（1 个工作段）
10. 提示词工程：考点/公式/例题结构（针对刷题类视频），**术语音译纠正表**
11. 整季批量（16P）：队列串行 + 进度聚合 + 失败重试
12. 评测：10 条视频 × 人工评分（覆盖率/准确性/可读性）

---

## 6. 验收标准（可测，不达标不算完）

| 编号 | 验收项 | 判定标准 | 测法 |
|---|---|---|---|
| **A1** | B站有字幕视频取材 | ≤3s，`source_mode=subtitle` | 换一个带 AI 字幕的视频跑 |
| **A2** | 无字幕视频取材（27min） | ≤75s，`source_mode=bcut` | `BV1YPsJ6BEPx` p1 |
| **A3** | 取材降级可用 | 关掉 bcut 自动回落 whisper，仍能出笔记 | 配置开关测试 |
| **A4** | 首字时间 | 点击后 ≤8s 出现首段 Markdown | 前端计时 |
| **A5** | 全流程（27min 视频） | **≤3 分钟**出完整笔记 + 图文 | `video_probe.py` |
| **A6** | 视频可播放 | `<video>` 能播，拖动进度条正常，首帧 ≤2s | 浏览器手测 + `mime=video/mp4` |
| **A7** | 图文正确性 | 截图时间点误差 ≤2s；每 3 分钟 ≥1 张；图片 100% 可访问 | 抽样 10 张对比原片 |
| **A8** | 笔记质量 | 公式/术语正确率 ≥90%（人工抽样 10 段）；每章有 `[mm:ss]` | 人工评分表 |
| **A9** | 16P 分集 | 只处理指定 P；UI 显示「第 N/16」；不误下整季 | `BV1YPsJ6BEPx` 手测 |
| **A10** | 稳定性 | 中断可续跑；失败有错误码 + 可读原因；无静默失败 | 拔网/中止测试 |
| **A11** | 回归 | `verify_all.py` 95/95 不退化 | 硬门禁 |
| **A12** | 成本 | 27min 视频单次 ≤¥0.3（方舟 flash 计价） | cost_ledger 抽查 |

---

## 7. 需要你拍板的 5 件事

1. **复刻范围**：只重构「视频模块 + 视频页布局」（保留现有仪表盘/复习/计划 9 个页面），还是要把 BiliNote 的整体单页布局替换全站？
2. **必剪云转写**：这是 B站自己的免费接口（无官方 SLA、可能限流）。接受作为主路径吗？还是只做「有字幕才快、没字幕走 whisper」？
3. **火山方舟**：作为**默认**模型（替代 DeepSeek 官方 key），还是并存可切换？
4. **三模板笔记**：改成 BiliNote 式单篇 Markdown 后，旧的「摘要/大纲/问答」三张卡要不要保留？
5. **整季批量**：16P 一次性排队解析，还是先只做单 P？

---

## 8. 风险

| 风险 | 处理 |
|---|---|
| 必剪接口变更/限流 | 做成可开关 + 自动降级 whisper；失败不阻断任务 |
| 方舟未开通模型误用 404 | 启动自检探活，未开通直接报错并回退 |
| Markdown 直出的渲染坑（有序列表被吃掉） | 提示词强制 `1\. ` 转义 + 前端 GFM 渲染（沿用现有 Markdown 组件） |
| 截图点过于密集导致抽帧慢 | 每 3 分钟限 1 张 + 最多 20 张 + ffmpeg `-ss` 精确定位 |
| 版权/许可 | BiliNote MIT，保留声明；不复制其品牌与文案 |

---

## 9. 执行记录（P0 已完成部分，2026-11-22 15:45）

### 9.1 已落地

| # | 内容 | 文件 |
|---|---|---|
| 1 | 火山方舟通道（独立 base/key、默认关思考、未开通模型给明确错误、失败回落） | `app/ai/ark.py`（新增）、`core/config.py` |
| 2 | 笔记 JSON 生成**方舟优先**，失败静默回落 DeepSeek | `app/ai/router.py` |
| 3 | 必剪云转写客户端（申请→分片上传→提交→轮询→解析） | `app/services/bcut.py`（新增） |
| 4 | 取材三级路由：字幕 → **必剪** → Whisper（自动降级 + 心跳防误杀） | `worker/handlers.py` `_try_bcut()` |
| 5 | 视觉 OCR 走方舟（13s/张，原 100s+） | `services/frames.py` |
| 6 | 播放修复：`mime` 由 `video/*` 改为真实类型；历史数据按后缀兜底 | `worker/handlers.py`、`routers/videos.py` |
| 7 | **手写 Range 支持**（Starlette 0.37 的 FileResponse 不带 Range，实测返回 200+全量 55MB） | `routers/videos.py` `_file_iter()` |

### 9.2 实测验收（`BV1YPsJ6BEPx` p1，27 分钟肖八刷题）

任务 `tasks#315`，`stage_timeline` 实测：

| 阶段 | 耗时 | 说明 |
|---|---|---|
| 解析链接 + 下载 480p（含音视频合并） | 22.4s | 52MB |
| 抽音频 | 0.7s | |
| **必剪云转写** | **15.0s** | 958 段，`source_mode=bcut`，本机 CPU 空闲 |
| 三模板并发生成 | 24.8s | 走方舟 |
| 抽关键帧 | 63.1s | ← 现在最大头 |
| **视觉 OCR（方舟）** | **24.8s** | 原 125s |
| 图文笔记生成 | 9.1s | |
| **合计** | **178.9s ≈ 3 分钟** | 同类 31 分钟视频改造前 482s |

- 播放：`Range: bytes=0-1023` → **206**，`content-range: bytes 0-1023/55831857`，`content-type: video/mp4` ✅
- 三模板：3/3 成功，图文笔记 `frames.done=true` ✅

### 9.3 尚未做（下一段）

1. **抽帧 63s**：改 `-skip_frame nokey`（只解关键帧，预期 63s → 15s 级）
2. 分 P 元信息（「第 N/16 集」）与整季批量
3. **P1**：Markdown 直出 + `*Screenshot-[mm:ss]` 抽帧插图 + 三段式 UI
4. 方舟视觉/笔记成本记账（目前仍记在 DeepSeek 单价上，需按方舟计价）

---

## 10. 执行记录（第二批：并发 / 配置中心 / Markdown / 截图）

### 10.1 已落地

| # | 内容 | 位置 |
|---|---|---|
| 1 | **视频任务独立 5 并发池**（其余任务仍单线程，避免 SQLite 抢锁） | `worker/runner.py` `_vq` / `_vthreads` |
| 2 | 原子领取（条件 UPDATE 抢占），杜绝并发下同一任务跑两次 | `worker/runner.py` `_run_task()` |
| 3 | SQLite **WAL + busy_timeout=15s** | `db/session.py` |
| 4 | 配置中心四表：`ai_providers / ai_models / app_settings / platform_cookies` | `models/models.py`、`migrations/versions/0009_settings_center.py` |
| 5 | 密钥 **Fernet 加密入库**，接口只回掩码 `ark-********1457` | `services/settings_store.py` |
| 6 | 配置中心 API：providers/models CRUD、模型真探活、runtime、cookies、diagnostics、monitor | `routers/settings.py` |
| 7 | LLM 路由改「**配置中心优先，env 兜底**」，改完即热生效（内存缓存刷新） | `ai/ark.py`、`ai/router.py`、`services/settings_store.py` `refresh_cache()` |
| 8 | 方舟**信号量限流 2 + 429 退避**（实测 3 并发必 429，且排队 171s） | `ai/ark.py` |
| 9 | **单篇 Markdown 笔记**（`*Content-[mm:ss]` 转可点跳转） | `services/video_note.py` |
| 10 | **`*Screenshot-[mm:ss]` 按点抽帧插图**（`ffmpeg -ss` 精确定位，非全片解码） | `services/video_note.py` `grab_frames()` |
| 11 | 平台 Cookie 落成 Netscape `cookies.txt` 供 yt-dlp 使用（B站 AI 字幕通道） | `settings_store.materialize_cookie()` |
| 12 | 取材策略可切换：auto / subtitle / bcut / whisper | `handlers._transcriber_mode()` |

### 10.2 验收

| 项 | 结果 |
|---|---|
| `video_workers` | **5**（`/api/tasks/health`） |
| 配置中心 6 个接口 | 全 200，密钥掩码正确 |
| 方舟探活（模型 1） | `probe_status=ok` |
| 方舟 3 并发（限 2） | 13.1s 全部成功，无 429 |
| **Markdown 笔记（p3，27min 肖八）** | **6099 字 / 18 个二级标题 / 6 张截图**，`*Content` 已转 `[mm:ss](/video?t=秒)` |
| 截图可达性 | `/api/videos/frames/shot212_00056.jpg` → 200 `image/jpeg` 98KB |
| 阶段耗时（p3 冷跑） | 下载 20.3s → 抽音 1.4s → **必剪 13.5s** → 三模板 126s（限流后）→ Markdown+截图 23.1s → 抽帧 63s → OCR/图文 |
| 回归 | `verify_all.py` 95/95（见 /tmp/v12.log） |

### 10.3 发现并处理的新问题

- **方舟账号并发上限极低**：3 个并发请求中 1 个直接 429，且 **171s** 后才返回。
  → 加信号量（`ARK_MAX_CONCURRENCY=2`）+ 429 指数退避（2/8/18s）+ 超时降到 100s。
  副作用：三模板串行化后从 25s 变 126s。**下一步把三模板挪到 Markdown 之后异步生成**，主路径只看 Markdown。
- **同一账号并发登录会互相踢下线**（两个 probe 用同一账号，先登录的拿到 401）。
  → 测试脚本改用不同账号；产品侧后续要确认是否允许多会话。
- 模型偶发把标记写成 `*Content-[00:00]*`，替换后留裸星号 → 已在 `content_links/apply_screenshots` 清理。

### 10.4 尚未做（下一批，按优先级）

1. **设置中心前端页面**（供应商/模型/转录器/Cookie/诊断/监控 六个 tab）
2. **视频页三段式**（表单 / Markdown 预览 / 历史 + StepBar），`[mm:ss]` 点击跳转播放器
3. 三模板下沉为后台任务，不阻塞 Markdown 主路径
4. 整季 16P 批量入口（后端已能并发 5，缺一键提交 N 集）
5. 抽帧 63s → `-skip_frame nokey`
