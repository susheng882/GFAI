# GFLC 学习工作台 —— 代码层功能盘点（事实清单）

> 用途：供产品报告 / 技术报告引用的事实底稿。只陈述事实，不做评价。
> 核对基准：`F:/GrowthForward_AI学习伴侣/gflc`（backend + web 源码静态读取）。
> 统一前缀：所有业务路由挂载于 `settings.API_PREFIX = "/api"`（`app/core/config.py:14`、`app/main.py:140-154`）。

---

## 一、后端接口（按模块分组，路径 + 方法）

挂载方式：`app/main.py` 中 `app.include_router(<module>.router, prefix="/api")`。
以下路径为「router 内部路径」，最终完整路径需加 `/api` 前缀（除 `decks` 无 prefix）。

### auth（`/api/auth`）— `routers/auth.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /auth/register | 注册 |
| POST | /auth/login | 登录 |
| POST | /auth/logout | 登出 |
| GET | /auth/me | 当前用户 |
| GET | /auth/export | 账号导出（confirm/password 参数） |
| POST | /auth/delete | 注销账号 |

### documents（`/api/documents`）— `routers/documents.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /documents/upload | 直传文件 |
| POST | /documents/presign | 预签名上传 |
| POST | /documents | 创建文档记录 |
| GET | /documents | 文档列表 |
| GET | /documents/{doc_id} | 文档详情 |
| GET | /documents/{doc_id}/overview | 文档解析总览 |
| POST | /documents/{doc_id}/parse | 触发解析 |
| POST | /documents/{doc_id}/cards | 生成卡片 |
| GET | /documents/{doc_id}/cards | 列出卡片 |
| PATCH | /documents/{doc_id} | 重命名 |
| DELETE | /documents/{doc_id} | 删除 |
| GET | /documents/{doc_id}/notes | 文档笔记列表 |
| POST | /documents/{doc_id}/notes | 创建文档笔记（AI 生成，`generate_json` mid 档） |

### decks（无 prefix，路由直接 `/decks`、`/cards`）— `routers/decks.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /decks | 卡包列表 |
| POST | /decks | 创建卡包 |
| PATCH | /decks/{deck_id} | 重命名卡包 |
| DELETE | /decks/{deck_id} | 删除卡包 |
| GET | /decks/{deck_id}/cards | 卡包卡片 |
| POST | /cards/batch-delete | 批量删除卡片 |
| POST | /cards/batch-reset | 批量重置进度 |
| GET | /cards | 卡片列表（q/deck_id 筛选） |
| POST | /cards | 创建卡片 |
| GET | /cards/{card_id} | 卡片详情 |
| PATCH | /cards/{card_id} | 编辑卡片 |
| POST | /cards/{card_id}/reset | 重置单卡进度 |
| DELETE | /cards/{card_id} | 删除卡片 |

### notes（`/api/notes`）— `routers/notes.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /notes/folders | 文件夹列表 |
| POST | /notes/folders | 创建文件夹 |
| PATCH | /notes/folders/{folder_id} | 改文件夹 |
| DELETE | /notes/folders/{folder_id} | 删文件夹 |
| POST | /notes/tidy | 笔记整理建议（AI mid 档） |
| POST | /notes/tidy/apply | 应用整理 |
| GET | /notes/recent | 最近笔记 |
| GET | /notes | 笔记列表 |
| POST | /notes/ai-suggest | AI 续写建议 |
| POST | /notes/insert | 定位插入正文 |
| POST | /notes/{note_id}/to-cards | 笔记转卡片 |
| GET | /notes/vault | Vault 状态 |
| PUT | /notes/vault | 设置 Vault |
| POST | /notes/vault/export | Vault 导出 |
| POST | /notes/vault/import | Vault 导入 |
| GET | /notes/{note_id} | 笔记详情 |
| GET | /notes/{note_id}/anchors | 锚点列表 |
| POST | /notes/{note_id}/anchors/apply | 应用锚点同步 |
| POST | /notes | 创建笔记 |
| PATCH | /notes/{note_id} | 编辑笔记 |
| DELETE | /notes/{note_id} | 删除笔记 |
| GET | /notes/{note_id}/links | 双向链接 |
| POST | /notes/{note_id}/duplicate | 复制笔记 |
| GET | /notes/{note_id}/export | 导出笔记 |

### review（`/api/review`）— `routers/review.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /review/due | 到期复习队列 |
| POST | /review/preview | 复习预览 |
| POST | /review/{card_id}/defer | 延后 |
| POST | /review/{card_id} | 提交评分 |

### dashboard（`/api/dashboard`）— `routers/dashboard.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /dashboard/stats | 统计 |
| GET | /dashboard/heatmap | 学习热力图 |
| GET | /dashboard/today | 今日待办 |
| GET | /dashboard/loop | 闭环状态 |
| POST | /dashboard/generate | 生成仪表盘 |
| GET | /dashboard/latest | 最新仪表盘 |
| GET | /dashboard/list | 布局列表 |
| PUT | /dashboard/{layout_id}/order | 保存排序 |
| PATCH | /dashboard/{layout_id}/card | 编辑单卡 |
| POST | /dashboard/{layout_id}/default | 设为默认 |
| DELETE | /dashboard/{layout_id} | 删除布局 |

### mastery（`/api/mastery`）— `routers/mastery_insight.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /mastery/insight | 掌握度洞察 |
| GET | /mastery/reconcile/preview | 对账预览 |
| POST | /mastery/reconcile | 执行对账 |

### questions（`/api/questions`）— `routers/questions.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /questions/upload | 上传题库文件 |
| POST | /questions/{document_id}/generate | 生成题库 |
| POST | /questions/import | 导入题库 |
| GET | /questions/banks | 题库列表 |
| GET | /questions | 题目列表 |

### quiz（`/api/quiz`）— `routers/quiz.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /quiz/overview | 练习总览 |
| GET | /quiz/recommend | 推荐下一题 |
| GET | /quiz/chapters | 章节列表 |
| POST | /quiz/generate | 组卷 |
| POST | /quiz/submit | 提交作答 |
| GET | /quiz/wrong | 错题列表 |
| DELETE | /quiz/attempts/{question_id} | 重置作答记录 |
| POST | /quiz/questions/{question_id}/to-card | 题目转卡片 |

### ai（`/api/ai`）— `routers/ai_study.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /ai/weak-quiz | 薄弱点出题（纯 SQL，不调模型） |
| POST | /ai/explain | AI 讲解（mid 档） |
| POST | /ai/mock-paper | AI 组卷（mid 档） |

### plans（`/api/plans`）— `routers/plans.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /plans | 创建计划 |
| GET | /plans | 计划列表 |
| GET | /plans/{plan_id} | 计划详情 |
| POST | /plans/tasks/{task_id}/toggle | 勾选任务 |

### qa（`/api/qa`）— `routers/qa.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /qa | 问答（非流式） |
| POST | /qa/stream | 问答（NDJSON 流式） |
| POST | /qa/save-note | 沉淀为笔记 |
| POST | /qa/save-card | 沉淀为卡片 |
| GET | /qa/suggest | 追问建议 |

### videos（`/api/videos`）— `routers/videos.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | /videos/upload | 上传视频 |
| POST | /videos/url | 链接解析 |
| GET | /videos/frames/{filename} | 取关键帧 |
| GET | /videos | 视频列表 |
| GET | /videos/{document_id}/notes | 视频笔记 |
| GET | /videos/{document_id}/export | 导出 Markdown |
| GET | /videos/{document_id}/search | 转写搜索 |
| DELETE | /videos/{document_id} | 删除 |
| GET | /videos/{document_id}/stream | 视频流 |

### tasks（`/api/tasks`）— `routers/tasks.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /tasks | 任务列表 |
| GET | /tasks/health | worker 健康 |
| POST | /tasks/cleanup | 清理旧任务 |
| POST | /tasks/{task_id}/retry | 重试 |
| POST | /tasks/{task_id}/abort | 放弃 |
| GET | /tasks/{task_id} | 任务详情 |

### settings（`/api/settings`）— `routers/settings.py`
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /settings/providers | 供应商列表 |
| POST | /settings/providers | 创建供应商 |
| PATCH | /settings/providers/{pid} | 改供应商 |
| DELETE | /settings/providers/{pid} | 删供应商 |
| GET | /settings/models | 模型列表 |
| POST | /settings/models | 创建模型 |
| PATCH | /settings/models/{mid} | 改模型 |
| DELETE | /settings/models/{mid} | 删模型 |
| POST | /settings/models/{mid}/probe | 探活模型 |
| GET | /settings/runtime | 运行时配置 |
| PUT | /settings/runtime | 写运行时配置 |
| GET | /settings/cookies | 平台 Cookie 列表（掩码） |
| PUT | /settings/cookies | 写 Cookie |
| GET | /settings/diagnostics | 诊断 |
| GET | /settings/alerts | 告警阈值 |
| GET | /settings/monitor | 监控 |

### 顶层（`app/main.py`）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /health | 健康检查 |
| GET | /api/config | 客户端配置（mock_ai/storage/max_upload_mb） |

---

## 二、前端页面（`web/src/pages/`，文件名 + 职责）

共 18 个 `.jsx`：

| 文件 | 职责（据文件头注释 / 组件名） |
|---|---|
| AuthPage.jsx | 登录 / 注册，凭据走 HttpOnly Cookie |
| DashboardPage.jsx | 指挥台 v3：闭环条 + 热力图 + 指标 + 快速上传；二级 tab 挂 AI 看板 |
| AiBoard.jsx | AI 看板：主题生成 / 日周月切换 / 卡片渲染与单卡编辑 |
| DocumentsPage.jsx | 资料上传与列表；承接 `/docs?doc=&page=` 定位抽屉跳转 |
| DocumentDetailPage.jsx | 资料二级枢纽：掌握度总览 / 笔记 / 卡片 / 题目四块 |
| StudyPage.jsx | 刷题主入口：quiz/recite/test/wrong 四种模式（含答题卡、报告、错题） |
| QuizAnswerSheet.jsx | 答题卡浮层：题号四态、点格跳题、交卷（纯本地 state） |
| QuizResult.jsx | 交卷报告：得分 → 知识点分布 → 逐题回顾 |
| WrongBook.jsx | 错题本：按错次排序、重做、按章重试 |
| ReviewPage.jsx | 间隔复习：四档评分 + 延后 + 每日目标 |
| DecksPage.jsx | 卡包：章节卡片网格 + Anki 式卡片浏览器（表格/筛选/批量操作） |
| NotesPage.jsx | 三栏笔记编辑器（断点响应式）+ 文件夹 + AI 模式 |
| QAPage.jsx | 问答：NDJSON 流式 + 三阶段过程行 + 检索依据 + 来源芯片 |
| PlansPage.jsx | 学习计划：目标 → 逐日任务拆解 → 勾选完成 |
| TasksPage.jsx | 后台任务列表：进度、错误脱敏、放弃/重试/清理 |
| VideoPage.jsx | 视频解析：批量导入（单批上限 50）、转写/笔记/图文 tab |
| SettingsPage.jsx | 设置中心：供应商 / 模型 / 转录器 / Cookie / 诊断 / 监控 |

> 注：`WrongBook.jsx`、`QuizResult.jsx`、`QuizAnswerSheet.jsx`、`AiBoard.jsx` 为子组件形态（被 StudyPage / DashboardPage 引用），非独立路由页。

---

## 三、数据模型（`models/models.py`，表名 + 说明）

共 22 张表：

| 表名 | 说明 |
|---|---|
| users | 用户（邮箱、密码哈希、角色、状态） |
| documents | 资料（PDF/视频/题库，来源类型、状态、去重哈希） |
| tasks | 后台任务（类型、状态、进度、错误、断点、结果） |
| chunks | 文本分块（溯源：页码/视频时间戳） |
| card_decks | 卡包（root/chapter 层级） |
| cards | 卡片（问答、FSRS 排期、掌握度、笔记锚点） |
| question_banks | 题库 |
| questions | 题目（选项、答案、五段解析、掌握度） |
| cost_ledger | AI 成本账本（模型/token/花费） |
| plans | 学习计划 |
| plan_tasks | 计划任务（逐日、到期时间） |
| attempts | 答题记录 |
| review_logs | 复习日志（评分流水，驱动热力图） |
| note_folders | 笔记文件夹（project/subject/topic 三层） |
| notes | 笔记（Markdown 正文、要点、来源/类型） |
| card_anchors | 笔记↔卡片同源锚点（`正面 :: 背面` 行解析） |
| dashboard_layouts | 仪表盘布局（主题/配置/顺序/位置） |
| audit_logs | 审计日志（账号导出/注销，仅存 IP 摘要） |
| ai_providers | AI 供应商（密钥密文存储） |
| ai_models | AI 模型（按 purpose 分类：note/vision/long/transcribe/chat） |
| app_settings | 运行时开关（key-value 字符串） |
| platform_cookies | 平台登录态（B 站 SESSDATA 等，密文） |

---

## 四、后台任务类型（`worker/handlers/`，`register_all` 注册）

共 7 个任务类型（`handlers/__init__.py:26-33`）：

| 任务类型 | 处理函数 | 位置 |
|---|---|---|
| pdf_parse | handle_pdf_parse | handlers/parse.py |
| card_generate | handle_card_generate | handlers/parse.py |
| question_import | handle_question_import | handlers/parse.py |
| plan_generate | handle_plan_generate | handlers/plan.py |
| video_upload | handle_video_upload | handlers/video.py |
| video_url | handle_video_url | handlers/video.py |
| dashboard_generate | handle_dashboard_generate | handlers/dashboard.py |

---

## 五、迁移版本（`migrations/versions/`）

共 11 个迁移文件，链式 `down_revision` 连续，最新版本 **0011**：

| revision | 文件 | 说明（据文件名） |
|---|---|---|
| 0001 | 0001_init.py | 初始建表（down_revision=None） |
| 0002 | 0002_plans_attempts.py | 计划 + 答题记录 |
| 0003 | 0003_dashboard.py | 仪表盘 |
| 0004 | 0004_task_result.py | 任务结果字段 |
| 0005 | 0005_question_banks.py | 题库 |
| 0006 | 0006_decks_crud.py | 卡包 CRUD |
| 0007 | 0007_note_folders.py | 笔记文件夹 |
| 0008 | 0008_mastery_due_audit.py | 掌握度 + 到期 + 审计 |
| 0009 | 0009_settings_center.py | 设置中心 |
| 0010 | 0010_card_anchors.py | 卡片锚点 |
| 0011 | 0011_review_logs.py | 复习日志（最新） |

---

## 六、AI 能力点（`app/ai/` 与 `app/services/`）

### 模型通道（`app/ai/`）
- **三档 JSON 路由** `router.generate_json(tier, ...)`：light/mid/strong 三档（`TIERS`，模型见 `config.py`：light=deepseek-flash、mid=deepseek-flash、strong=deepseek-v4-pro），带 Pydantic 契约校验 + 纠正性重试一次。
- **DeepSeek 官方通道** `deepseek.py`：`chat`、`chat_stream`（流式）、`extract_json`。
- **火山方舟 Ark 通道** `ark.py`：`chat`、`generate_json`、`probe`（探活）。方舟优先、失败回落 DeepSeek。
- **Mock 兜底** `mock.py`：无 Key 时规则抽取问答。

### 能力点清单（调用位置 → 用途）

| 能力 | 调用点 | 说明 |
|---|---|---|
| 问答（RAG + 联网 + 流式） | routers/qa.py（chat_stream + websearch + rag） | 多策略（auto/knowledge/web/model/hybrid）问答 |
| 查询改写 | services/query_opt.py `rewrite`（light 档） | 检索前改写 query |
| 检索重排 | services/query_opt.py `rerank`（light 档） | 重排候选片段 |
| 卡片生成 | services/cards.py（generate_json） | 文档→卡片 |
| 笔记 AI 续写 / 转卡片 | services/note_ai.py（mid 档） | suggest / to_cards |
| 题库批量解析 | services/question_parse.py（strong 档） | 文本→结构化题目 |
| 扫描件视觉 OCR | services/question_vision.py（Ark 视觉） | PDF 无文字层兜底逐页转录 |
| 视频帧 OCR / 网格拼图 OCR | services/frames.py（Ark 视觉） | 关键帧文字识别 + 图文笔记 |
| 视频笔记生成 | worker/handlers/video.py（generate_json） | 摘要/大纲/问答模板 |
| 语音转写 | services/video.py（whisper 本地 ASR） | 音频转写 |
| 云端转写 | services/bcut.py `transcribe_bcut` | 必剪云端转写 |
| 内嵌字幕提取 | services/video.py | 字幕优先于 ASR |
| 向量嵌入 | services/embedding.py（BGE 本地 / hash 降级） | 语义检索向量化 |
| 学习计划生成 | worker/handlers/plan.py（mid 档） | 目标→逐日任务 |
| 仪表盘生成 | worker/handlers/dashboard.py（mid 档） | 主题→卡片配置 |
| AI 讲解 | routers/ai_study.py `explain`（mid 档） | 错题解析 |
| AI 组卷 | routers/ai_study.py `mock-paper`（mid 档） | 模考试卷 |
| 笔记整理 | routers/notes.py `tidy`（mid 档） | 文件夹内容整理 |
| 文档笔记生成 | routers/documents.py（mid 档） | 文档→笔记 |

---

## 核对方式

- 后端接口：Grep `@router.(get|post|put|patch|delete)` 于 `backend/app/routers/*.py`，并 Grep 各文件 `APIRouter(prefix=...)` 确认前缀；`main.py` 确认挂载与 `/api` 前缀。
- 前端页面：Glob `web/src/pages/*.jsx`（18 个），逐个读文件头注释 / 组件名。
- 数据模型：Read `backend/app/models/models.py` 全文，枚举 `__tablename__`。
- 后台任务：Read `worker/handlers/__init__.py` 的 `register_all`，交叉核对各 `handle_*` 定义。
- 迁移版本：Grep 各文件 `revision` / `down_revision`。
- AI 能力：Grep `generate_json` / `chat` / `chat_stream` / `transcribe` / `embed` / `ocr` 等调用点于 `app/ai/` 与 `app/services/`。

## 发现的问题 / 不一致（仅陈述，不评价）

1. **decks router 无 prefix**：`routers/decks.py:16` 为 `APIRouter(tags=["decks"])`，未设置 `prefix`，故其路径为顶层 `/decks`、`/cards`；而 `settings.py:26` 也无 `tags` 参数（`APIRouter(prefix="/settings")`）。其余模块均有 prefix+tags，风格不统一。
2. **decks 前缀依赖全局 /api**：`/decks`、`/cards` 仍需 `main.py` 的 `prefix="/api"` 兜底，最终为 `/api/decks`、`/api/cards`，但 router 层无自身前缀，与 documents/notes 等不一致。
3. **models.py 文件头注释过期**：文件头写「P0 建 7 张表；plan/review/error_case 进 P1 迁移补」，但实际已有 22 张表，注释未随代码更新。
4. **无 error_case 表**：文件头提到的 `error_case` 表在 `models.py` 中不存在（可能是历史计划，未落地）。
5. **Task.type 注释**：`Task.type` 字段注释列举 `pdf_parse / video_parse / card_generate`，但实际注册任务类型为 `pdf_parse / card_generate / question_import / plan_generate / video_upload / video_url / dashboard_generate`，`video_parse` 未注册（video 拆为 upload/url 两个类型）。
6. **前端页面 18 个中 4 个为子组件**：`WrongBook`、`QuizResult`、`QuizAnswerSheet`、`AiBoard` 为被引用的组件而非独立路由页，目录命名（pages/）与实际职责不完全一致。
7. **`app/ai/__init__.py` 为空文件**（1 行），`app/routers/__init__.py` 亦为空，模块无导出说明。
8. **API 版本号**：`main.py:101` 声明 `version="0.2.0"`，与迁移链 0011、功能规模并存，属可留意的版本标注信息。
