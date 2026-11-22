# GFLC — GrowthForward AI Learning Companion

面向备考/自学人群的 AI 学习伴侣。把视频、PDF、题库加工成可复习、可追溯的学习物料，并用「计划—执行—复盘」闭环让学习持续。

> 当前进度：**P0 骨架**（鉴权 + 预签名上传 + PDF 解析切块 + 卡片生成）。
> 规格与约束见 `../开发提示词/01_系统提示词.md`，计划见 `../开发计划/00_开发总计划.md`。

## 目录

```
gflc/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── core/            # 配置 / 安全 / 错误码
│   │   ├── db/              # 连接与会话
│   │   ├── models/          # 数据模型
│   │   ├── schemas/         # 请求响应 + AI 契约
│   │   ├── crud/            # 数据访问
│   │   ├── services/        # 切块 / 解析 / 存储 / 卡片 / 管线
│   │   ├── ai/              # DeepSeek 客户端 / 三档路由 / Prompt
│   │   └── routers/         # auth / documents
│   ├── migrations/          # Alembic
│   ├── tests/               # 单测
│   └── requirements.txt
├── deploy/                  # docker-compose / nginx / .env.example
└── docs/                    # 设计决策留痕
```

## 功能一览（9 个页面）

| 页面 | 能力 |
|---|---|
| 仪表盘 | **AI 按主题 + 月/周/日粒度生成**；**双击翻转改数据**（含**柱状/折线逐行改数值、增删行**）；**hover 右下角拖拽改大小**；拖动换位；数值取真实学习数据 |
| 笔记 | **Obsidian 式**：左侧「项目 → 科目 → 内容」文件夹树、卡片式列表预览、Markdown 编辑/预览、右侧 **AI 协作**（生成后由你决定插入/替换）；**AI 整理文件夹**（归类建议/去重/缺失点）；一键转卡片 |
| 文档 | PDF 上传解析、生成卡片、重命名/删除 |
| 卡包 | 按 PDF 大纲分「大卡包 → 章节卡包」；卡片增删改 |
| 学习 | **刷题 / 背诵一页切换**：左侧章节树（进度+正确率+错题）、中间推荐与章节掌握度、右侧学习进度与错题本；**背诵模式**为翻面卡片 |
| 复习 | 间隔重复闪卡（FSRS），1–4 评分 |
| 问答 | **流式输出**（首字节 0.01s）；知识库（含你的笔记）优先带页码 → 联网带 URL → 学科知识兜底；资料不符时自动补答 |
| 视频 | **四种笔记**（摘要 / 大纲 / 问答 / 图文关键帧）一次生成；左视频播放器 + 关键帧缩略图条，右**树状大纲**（仿网盘）；文档类画面自动 OCR；历史可回看 |
| 任务 | 后台任务管理与进度：实时进度、**看门狗超时自动失败**、**失败任务可重试** |

## 后台任务与进度（重要）

所有耗时操作（PDF 解析、卡片生成、题库导入、计划、仪表盘、视频转写）都是**后台任务**：

1. 接口立即返回 `{task_id}`（实测 0.05–0.07s，**不再阻塞服务**）
2. 前端右下角出现进度坞，轮询 `/api/tasks/{id}` 显示真实进度
3. 「任务」页可查看最近 30 条任务的状态/进度/结果
4. 任务失败会记录 `error_code` 与原因

> 这解决了早期"长任务占满事件循环导致整个服务卡死"的问题。

## 多平台视频支持

下载统一走 **yt-dlp**（自动识别站点），转写走 **faster-whisper**（默认 `base`，可用 `WHISPER_MODEL` 调）。

| 平台 | 状态 | 说明 |
|---|---|---|
| **B站** | ✅ 已实测 | 链接 → 下载 → 转写 → 笔记 全链路通过（198s 科普视频约 200s，含首模型加载） |
| YouTube | ⚠️ 受网络限制 | 本机 SSL EOF；代码支持，配置代理即可 |
| 抖音 | ⚠️ 需分享短链 | 域名可达；建议用 `v.douyin.com/…` 短链，失败请本地上传 |
| 快手 | ⚠️ 受网络限制 | 本机不可达；代码支持 |
| 本地上传 | ✅ | 常见视频/音频格式，最稳 |

> 首次转写会自动下载 whisper 模型（默认走 `hf-mirror.com` 镜像）。

## 本地零依赖运行（推荐先试）

不用 Docker、不用 PostgreSQL、不用 MinIO、不用 API Key，直接跑起来看效果：

```bash
cd backend
pip install -r requirements.txt
mkdir -p data/uploads
cp .env.dev .env          # sqlite + 本地存储 + Mock AI
alembic upgrade head
uvicorn app.main:app --port 8000
```

打开 **http://localhost:8000** → 注册 → 上传 PDF → 自动解析并生成卡片 → 去「复习」过一遍。

> 该模式用 SQLite（`data/gflc.db`）、本地文件（`data/uploads`）、规则生成卡片（Mock）。
> 填了 `LLM_API_KEY` 后自动切 DeepSeek 真模型，无需改代码。

## 快速启动（Docker 一键）

```bash
cd deploy
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（DeepSeek）
docker compose up -d --build
```

- API: http://localhost:8000/docs
- 网关: http://localhost （/api 走 nginx）
- MinIO 控制台: http://localhost:9001 （minioadmin / minioadmin）

启动时 app 容器会自动 `alembic upgrade head` 建表。

## 本地开发（不经 Docker）

需要本机有 PostgreSQL、Redis、MinIO，或改 `.env` 指向已有实例。

```bash
cd backend
pip install -r requirements.txt
cp ../deploy/.env.example .env      # 把 host 改成 localhost
alembic upgrade head
uvicorn app.main:app --reload
```

跑测试：
```bash
cd backend
pytest -q
```

## 最小验证流程（四条命令）

```bash
# 1. 注册（自动种下会话 Cookie）
curl -c c.txt -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"a@b.com","password":"password123"}'

# 2. 申请预签名上传地址
curl -b c.txt -X POST http://localhost:8000/api/documents/presign \
  -H 'Content-Type: application/json' \
  -d '{"filename":"demo.pdf","size":123456}'

# 3. 用返回的 upload_url PUT 上传 PDF 后，确认建档
curl -b c.txt -X POST http://localhost:8000/api/documents \
  -H 'Content-Type: application/json' \
  -d '{"storage_key":"<上一步 storage_key>","title":"演示文档"}'

# 4. 解析 + 生成卡片
curl -b c.txt -X POST http://localhost:8000/api/documents/1/parse
curl -b c.txt -X POST http://localhost:8000/api/documents/1/cards
curl -b c.txt http://localhost:8000/api/documents/1/cards
```

## P0 已知边界（P1 补齐）

- 解析为**同步**执行（P1 改 Redis 队列 + Worker 异步，接口不变）
- 去重键暂用 `storage_key+size`（P1 改流式内容哈希）
- 仅支持 PDF（视频/题库进 P1/P3）
- 无 pgvector 向量列（P1 加 `embedding` + HNSW）
- 前端未接入（先看 `/docs` 调试）

## 安全与合规底线
- 密码 Argon2id，会话 HttpOnly Cookie，越权按 `user_id` 过滤
- 上传走预签名直传，字节流不进 API 内存
- 失败必返错误码 + 可读原因，禁止静默
