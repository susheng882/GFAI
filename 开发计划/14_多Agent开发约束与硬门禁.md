# GFLC 多 Agent 开发约束与硬门禁

> 制定时间：2026-11-22　｜　适用范围：本次"把 12 号评审差异全部修完"的多 Agent 并行开发
> 本文档是**所有开发 Agent 的强制契约**。任何 Agent 不得越过自己的文件所有权，不得为了通过自身测试而削弱全局回归。

---

## 0. 目标与判定口径

**唯一目标**：把 `开发计划/12_技术产品报告进度差异评审_2026-11-22.md` 中列出的 V1–V6、S1–S8、D1–D12、Q1–Q7、A1–A7 全部收敛。

**"修好"的判定**分三类，不允许混为一谈：

| 类别 | 判定标准 | 例子 |
|---|---|---|
| 代码可修 | 有实现 + 有可复现验证命令 + 通过全局回归 | 向量检索、字幕取材、来源跳转、导出注销 |
| 环境可修 | 有可运行配置 + 冒烟脚本 + 明确执行记录 | HTTPS、Redis/RQ、MinIO、备份演练 |
| 外部不可代劳 | 产出材料包 + 明确责任人与时间窗，**不得声称已完成** | ICP 备案、域名实名、生产密钥申请 |

> 任何 Agent 在报告里写"已完成"时，必须附上证据类型（命令输出 / 文件路径 / 截图 / 外部待办编号）。无证据一律按未完成计。

---

## 1. 全局不变量（任何 Agent 不得违反）

1. **回归红线**：`scripts/verify_all.py` 必须保持 **95/95、退出码 0**。Agent 阶段不得自行重启 8010 服务或并发运行全量回归（会互相污染端口与数据库）；只允许做编译级、纯函数级、独立临时 DB 级自测。全量回归由集成方统一执行。
2. **外部契约稳定**：`/api/*` 已有响应字段只允许**新增**，不得删除或改类型；新增字段必须可选/带默认值。前端 React 版必须兼容现有 API，不允许为了前端重写而改后端契约（除非在所有权内并同步更新回归脚本）。
3. **配置单一真源**：`app/core/config.py` 由集成方独占。Agent 需要一个新开关时，在自己模块内用 `os.getenv("NAME", default)` 读取，**并在交付报告里列出所有新增环境变量名、默认值、含义**，由集成方统一回填 config 与 `.env.example`。
4. **禁止静默失败**：任何截断、降级、兜底、超时、质量不达标，都必须有日志（带 user_id / document_id / task_id 之一）或 API 可见字段，不允许悄悄吞掉。
5. **凭据与原文**：不把密钥写进代码/文档/日志；日志不落用户原文与凭据；新增导出/注销功能必须留审计记录。
6. **中文界面与中文注释**：用户可见文案用简体中文；新增代码注释用简体中文；代码标识符用英文。
7. **零破坏性操作**：不得删除或覆盖项目内已有文档（09–13 号）、`.workbuddy/` 目录、git 历史；不得 `rm -rf` 任何目录。
8. **文件所有权**：只修改下表分配给自己的路径。需要别人的文件时，**不修改**，在报告中写清"需要 X Agent 在 Y 文件加 Z"。

---

## 2. Agent 分工与文件所有权（互不重叠）

| Agent | 代号 | 独占路径 | 负责差异编号 |
|---|---|---|---|
| 前端 React 重构 | `fe-react` | `gflc/web/**`（新建） | S1、D12、S4 前端、D10 前端 |
| 检索与问答质量 | `qa-retrieval` | `app/services/rag.py`、`app/services/query_opt.py`、`app/routers/qa.py`、`app/services/embedding.py`、`app/services/vector_index.py`、`app/services/entity_check.py`、`app/services/answer_cache.py` | V1、S3、D3、D5、D7、D11、Q1–Q7 |
| 视频解析链路 | `video-pipe` | `app/services/video.py`、`app/services/frames.py`、`app/worker/handlers.py` | S2、D8、D9、A1–A5 |
| 队列与进程隔离 | `queue-worker` | `app/worker/runner.py`、`app/worker/queue.py`、`app/worker/queue_worker.py` | V2、D2、A6、S8 队列侧 |
| 账号治理与学习闭环 | `gov-loop` | `app/routers/auth.py`、`app/routers/dashboard.py`、`app/routers/plans.py`、`app/routers/quiz.py`、`app/services/recommend.py`、`app/services/mastery.py`、`app/services/export_service.py`、`app/models/models.py`、`app/db/migrations.py` | V5、S6、D10 后端 |
| 评测集与部署门禁 | `eval-infra` | `scripts/quality_eval.py`、`scripts/eval_gate.py`、`evals/**`、`gflc/deploy/**`、`gflc/backend/Dockerfile`、`.dockerignore`、`scripts/backup_restore.py`、`scripts/drill.sh`、`开发计划/15_*.md` | V3、V4、V6、N4、N5、G1–G7 材料 |

**集成方（主 Agent）独占**：`app/core/config.py`、`app/main.py`、`gflc/backend/frontend/**`、`app/core/budget.py`、`.env`、`开发计划/14_*.md`、全部提交与全量回归。

> 冲突处理原则：发现别人已经改了你的文件 → 立即停止该文件的工作并在报告中说明，不得强行覆盖。

---

## 3. 技术栈锁定（按产品/技术报告，不走样）

| 层 | 锁定版本 / 方案 | 备注 |
|---|---|---|
| 前端 | **React 19 + Ant Design 5 + Vite**，TypeScript 可选 | npm 可用；构建产物放 `gflc/web/dist`；API base 为 `/api`，凭据走 HttpOnly Cookie |
| API | FastAPI（现有） | 不换框架 |
| 向量 | `sqlite-vec` + `sentence-transformers`，模型 `BAAI/bge-large-zh-v1.5`（本机已缓存） | sqlite-vec 需 pip 安装；模型加载失败必须降级到确定性哈希向量并打 WARNING，不得让问答整体失败 |
| 队列 | Redis + RQ，Worker 独立进程；`QUEUE_BACKEND=auto/memory/redis` | 本机 Redis 已运行；无 Redis 时自动回落内存队列并告警 |
| 存储 | MinIO 预签名直传（配置具备），本地后端保留 dev 用 | 不改已有上传契约 |
| 原文定位 | chunk 带 `page` / `ts_start` / `chunk_id`；播放器用 `seek` | 点击跳转偏差 ≤2s |

---

## 4. 各差异的验收门禁（逐条可测）

### 4.1 一票否决级

- **V1 向量检索**：双路召回（向量 Top20 + BM25 Top20）按 chunk_id 合并去重；关闭向量开关时行为与改前一致；评测集召回率/MRR 不低于 BM25 基线 -3pp。
- **V2 队列分进程**：`QUEUE_BACKEND=redis` 时 API 只入队不执行，独立 Worker 进程消费；20 并发提交 API 响应 P95 ≤3s；内存队列作为 dev 回退仍可用。
- **V3 评测集**：≥30 份标注资料 + ≥20 条问题（含 ≥3 条无答案诱饵），六项指标（召回率/命中率/MRR/忠实度/拒答准确率/卡片可用率）有数字，按版本号归档。
- **V4 HTTPS**：deploy 提供可用 TLS 覆盖层与 Cookie Secure 配置；给出申请/部署/验证三步命令；明确标注"未拿到证书前不得声称完成"。
- **V5 注销/导出**：`POST /api/auth/delete`、`GET /api/auth/export` 可用；注销级联清 chunk/任务/对象存储/缓存；导出为机器可读归档；两次操作均留审计日志。
- **V6 备份与回滚演练**：脚本可跑通备份→破坏→恢复→校验；记录 RPO/RTO 实测值；回滚演练给出 ≤10min 的计时方法与结果模板（未实跑不得填"通过"）。

### 4.2 严重级

- **S1 前端 React**：`npm run build` 成功；所有既有页面（登录、指挥台、资料、问答、三类笔记、卡片、刷题、计划、复习、任务、视频）在 React 版可用；单文件规模下降（最大源码文件 ≤600 行）。
- **S2 字幕取材**：有内嵌/外挂字幕的视频 0 次 Whisper 调用；无字幕视频行为不变。
- **S3 实体一致性**：答案中的数字/专名与引用块比对，不一致时标"存疑"或拒答，日志含 `不一致实体` 字段。
- **S4 来源跳转**：答案来源芯片可点击，文档跳页、视频跳时间轴；偏差 ≤2s。
- **S5 真断点续传**：按段 checkpoint，中断重试跳过已完成段；成本日志显示不重复调用。
- **S6 学习闭环**：掌握度字段与复习 due、错题、计划任务三者联动；"今日待办"合并展示。
- **S7 成本护栏**：已由集成方在 13 号修复，本轮保持 95/95 即可。
- **S8 dev/prod 收敛**：启动自检已由集成方加入；本轮队列侧补 Redis 实跑冒烟。

### 4.3 设计级

- **D2** queued 态不计入看门狗；**D3** 统一 0–1 置信度；**D5** 语义问法能召回（评测集新增 ≥3 条语义问法）；**D6** 已修；**D7** notes 入统一索引；**D8** 三通道时间轴锚点；**D9** low 质量不写 ready；**D10** 计划回流；**D11** 结构化 confidence/strategy 字段；**D12** 前端模块拆分。

---

## 5. 并行开发协议

1. **先读后写**：每个 Agent 开工前读本文档 + 12 号评审对应差异段；不得凭印象开发。
2. **自测边界**：只做 `py_compile`、纯函数断言、独立临时 SQLite/Redis DB、npm build；**不得启动 8010、不得跑 verify_all、不得改 `.env`**。
3. **交付报告格式**（每个 Agent 最终回复必须包含）：
   - 改了哪些文件（逐路径）
   - 每个差异编号如何收敛（一句话 + 证据）
   - 新增环境变量清单（名称/默认值/含义）
   - 未做完的项与原因（明确写"阻塞"而非"已完成"）
   - 自测命令与输出摘要
4. **集成顺序**：主 Agent 收齐 → 检查冲突 → 回填 config/.env.example → 重启 8010 → 跑 95/95 回归 → 修复回归 → 前端 build + Playwright 冒烟 → 写 15 号总验收 → 提交。
5. **失败策略**：任一 Agent 的改动导致回归失败且 30 分钟内无法修复，主 Agent 回滚该 Agent 的文件到改动前，保留其报告，不拖垮整体。

---

## 6. 明确不伪装完成的项

以下必须由主 Agent 在最终文档中标注为**外部待办**，即使代码侧已备好：

- ICP 备案、域名实名、证书签发（G7）
- 真实生产密钥轮换与保管（G3）
- 生产环境备份恢复的真实 RTO 计时（G4，本机演练只能给参考值）
- 线上灰度 20 并发压测（G2，本机数据不能顶替）

> 本文档随集成结果更新；任何"差异已全部修完"的表述，必须同时给出这四项仍待执行的声明。
