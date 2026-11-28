# GFLC 成长向前 · 项目文档中心

> 考研 11408 学习闭环：资料 → 笔记/卡片 → 刷题 → 复习
> 文档精简后：12 份核心文档 + archive/ 52 份过程归档

---

## 📁 项目结构

```
GrowthForward_AI学习伴侣/
├── gflc/
│   ├── backend/              # FastAPI 后端
│   │   ├── app/
│   │   │   ├── main.py       # 入口（21 路由模块挂载，/api 前缀）
│   │   │   ├── routers/      # 21 个路由：auth/documents/notes/decks/review/
│   │   │   │                 #   dashboard/questions/quiz/ai_study/plans/qa/videos/
│   │   │   │                 #   tasks/settings/mastery_insight/conversations/
│   │   │   │                 #   workspaces/achievements/notifications
│   │   │   ├── services/     # 业务：cards/notes/video/embedding/query_opt/parse...
│   │   │   ├── ai/           # 模型通道：router(三档)/ark/deepseek/mock
│   │   │   ├── core/         # config/errors/security/budget
│   │   │   ├── worker/       # 后台任务：runner + 7 类 handler
│   │   │   └── models/       # 25 张表（迁移 0001-0012）
│   │   ├── tests/            # 33 单测（5 文件）
│   │   ├── scripts/          # verify_all(95接口)/e2e_paths(8路径)/ci_smoke(10冒烟)
│   │   ├── migrations/       # Alembic 0001-0012
│   │   └── data/gflc.db      # SQLite
│   ├── web/                  # 前端（唯一）
│   │   └── src/
│   │       ├── proto/        # Tailwind React 前端
│   │       │   ├── App.jsx / AppShell.jsx / main.jsx
│   │       │   ├── ui.jsx    # 组件体系（Card/Badge/Btn/Progress/Empty...）
│   │       │   ├── NavIcons.jsx  # 内联 SVG 图标
│   │       │   ├── mock/index.js # 107 数据对象（纯 mock）
│   │       │   └── pages/    # 14 页面
│   │       └── styles/tailwind.css  # Apple 白 token
│   └── docs/screenshots/     # 页面截图 + PDF 全览
├── 开发计划/                  # 12 份核心文档 + archive/
└── .workbuddy/memory/        # 会话记忆
```

## 📚 核心文档（12 份）

| 文档 | 内容 |
|---|---|
| **00_开发总计划** | 项目愿景与阶段划分 |
| **42_产品报告** | 定位/六大模块/市场差异/设计语言 |
| **43_技术报告** | 技术栈/架构/质量/技术债 |
| **51_项目完整输出报告** | 最新全貌（14页清单/优化总览/验收） |
| **53_前端接口契约文档** | 107 mock 形状 → 接口契约（37已有/7对齐/8缺失 + P0-P2 优先级） |
| **55_前端框架与代码规范** | 技术栈/目录/命名/组件规则/门禁 |
| **56_后端测试用例清单** | 146 项测试逐条（33单测/95接口/8e2e/10冒烟） |
| **57_全量测试报告** | 测试结果/发现的问题/遗留建议 |
| **_proto_v7l_设计规范** | Apple 白设计 token（颜色/圆角/阴影/动效） |
| **交付验收汇总** | 历轮验收结论一览 |
| **历史阶段记录** | 11-22~11-28 开发历程 + 关键决策 |
| **README**（本文件） | 项目结构总入口 |

> archive/ 保存 52 份过程文档（早期计划/竞品调研/临时 plan），可随时查阅。

## 🚀 快速开始

```bash
# 后端（8011 端口，服务 web/dist）
cd gflc/backend
D:\anaconda3\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8011

# 前端构建
cd gflc/web && npm run build

# 测试
pytest tests/                                     # 33 单测
python scripts/verify_all.py http://127.0.0.1:8011  # 95 接口
python scripts/e2e_paths.py http://127.0.0.1:8011   # 8 e2e
SMOKE_BASE_URL=http://127.0.0.1:8011 python scripts/ci_smoke.py  # 10 冒烟
```

## 🔑 登录

http://127.0.0.1:8011 · `cfg_probe@gflc.com` / `password123`

## 📌 当前状态（2026-11-28）

- 前端 14 页纯 mock 展示，布局占满视口，Apple 白设计语言
- 后端 25 表 / 21 路由 / 146 项测试全过（视频 URL 预检已修假阳性）
- 待办：按 53 号文档 P0-P2 补接口 → 前端切真数据
