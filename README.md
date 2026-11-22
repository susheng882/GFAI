# GrowthForward · AI 学习伴侣

面向考研 / 自学人群的 AI 学习工作台：把 **PDF、视频、试卷**变成可背诵的卡片与题库，并用仪表盘盯着进度。

> 毕设项目 · 单体架构（FastAPI + SQLite/SQLite→PostgreSQL + 原生前端单页）

---

## 它解决什么问题

备考的人不缺资料，缺的是"把资料变成能背下来的东西"这一步：

| 痛点 | 这里怎么解 |
|---|---|
| PDF 看完就忘 | 解析 → 按大纲分章节卡包 → 生成背诵卡片 + FSRS 间隔重复 |
| 网课视频记不住重点 | 上传/B站链接 → 转写 → **摘要 / 大纲 / 问答 / 图文（关键帧 OCR）** 四种笔记 |
| 试卷题目要手抄 | 视觉识别 PDF 试卷，公式保真（LaTeX）、自动分科目章节 |
| 不知道今天该学什么 | 仪表盘给一个 hero 数字 + 队列 + 指标带；刷题按错题优先推荐 |
| 笔记散落各处 | 类 Obsidian 的「项目 → 科目 → 内容」文件夹树 + AI 协作补写 |

---

## 目录结构

```
.
├── gflc/                     # 应用主体
│   ├── backend/
│   │   ├── app/              # FastAPI：core / db / models / schemas / crud / services / ai / routers / worker
│   │   ├── migrations/       # Alembic（0001–0007）
│   │   ├── frontend/         # 单页前端 index.html + 本地 KaTeX
│   │   ├── scripts/          # verify_all.py（95 项接口验收）/ quality_eval.py（质量评分）
│   │   └── requirements.txt
│   ├── deploy/               # docker-compose / nginx / .env.example
│   └── docs/                 # 截图、QA 报告
├── 开发计划/                  # 需求、验收标准、迭代报告、设计提案
├── 开发提示词/                # 系统提示词与协作规范
├── 毕设材料/                  # 论文与答辩材料
└── 归档/                      # 历史版本交付物
```

---

## 快速开始

```bash
cd gflc/backend

# 1. 依赖（Python 3.11）
pip install -r requirements.txt

# 2. 配置
cp ../deploy/.env.example .env
# 填入 LLM_API_BASE / LLM_API_KEY（兼容 OpenAI 协议的任意服务）
# MOCK_AI=true 可完全不调模型，用假数据跑通全流程

# 3. 建库
alembic upgrade head

# 4. 起服务
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

打开 <http://127.0.0.1:8010>，注册账号即可。

**演示账号**（本地库自带）：`demo@gflc.com` / `demo123456`

---

## 验收怎么跑

```bash
cd gflc/backend
python scripts/verify_all.py      # 95 项接口断言，覆盖率见 docs/qa/
python scripts/quality_eval.py    # 问答质量五维打分（相关性/完整性/引用/时延/成本）
```

---

## 技术要点（踩过的坑都在这）

| 主题 | 做法 |
|---|---|
| 模型调用 | 自建 `LLM_API_BASE`；三档模型（light/mid/strong）；**推理模型必须显式 `reasoning_effort=low`**，否则 reasoning token 吃光 `max_tokens` 导致正文为空 |
| 检索增强 | BM25Plus 分数恒正，"有分数≠有依据" → 加关键词覆盖率 + 语义重排（0–5 分，<3 剔除）；笔记正文也参与召回 |
| 问答体验 | NDJSON 流式：先回 `status`，再回 `sources`，最后逐段 `delta`；首字节 0.01s |
| 后台任务 | 单线程队列 + 看门狗（600s 无进度判失败）+ 重启恢复（running→interrupted、pending 重入队）+ 可放弃可重试 |
| 视频转笔记 | yt-dlp 下载 → faster-whisper 转写（`initial_prompt` 引导简体 + opencc 兜底）→ 四模板并发生成 |
| 关键帧 | ffmpeg 场景检测抽帧（<6 张退化为等间隔）→ 感知哈希去重 → 文档帧判定 → 视觉 OCR → 图文笔记 |
| 试卷识别 | PDF 页渲染成图 → 视觉模型直读 → LaTeX 保真 → 按章节归并 |
| 成本 | 事前预算拦截（日 token / 日成本 / 单任务）+ 事后 `cost_ledger` 记账，流式也记账 |
| 前端 | 原生单页（无框架）；设计系统见 `.workbuddy/skills/gflc-design/`；KaTeX 本地托管（CDN 不可用） |

---

## 状态

- 接口验收：`95/95`
- 问答质量：`8.84 / 10`（五维加权，达标线 7.5）
- 未做：Docker 联调实跑、压测、CI、题目识别跨页漏题

详细迭代记录见 `开发计划/05_阶段性报告.md` 与 `开发计划/07_unslop改造报告.md`。

---

## 说明

- `.env`、`gflc/backend/data/`（数据库与上传文件）**不入库**，按 `deploy/.env.example` 自行配置。
- 设计系统与 UI 规范：`.workbuddy/skills/gflc-design/SKILL.md`
- 界面改造依据 [unslop](https://github.com/heydamir/unslop)（Damir Sokolovsky，CC BY 4.0）的方法论；布局决策对标 Stripe / Linear / Notion / Plausible 等公开设计，**未复制任何产品的像素、图标与文案**。
