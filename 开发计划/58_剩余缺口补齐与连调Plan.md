# 58 · 剩余缺口补齐 Plan + 前后端连调验收标准

> 日期：2026-11-28　｜　目标：5 个缺失接口实现 + 前后端连调测试 + 收尾

---

## 一、缺口盘点（已核实）

| # | 接口 | 用途 | 前端 mock 数据源 |
|---|---|---|---|
| 1 | GET /api/questions/folders | 题库文件夹树 | bankTree |
| 2 | GET /api/review/upcoming | 未来7天到期柱状图 | upcomingReviews |
| 3 | GET /api/quiz/related/{id} | 同类题+选项分布+知识点 | quizRelated/quizOptionStats/quizRelatedPoints |
| 4 | GET /api/plans/events | 日历月/周/日事件 | planMonth/planWeek/planDay |
| 5 | GET /api/documents/storage | 存储占用条 | docStorage |

已完成待连调：banks overview ✅、notes tidy/apply ✅、conversations ✅、workspaces ✅、achievements ✅、notifications ✅、dashboard/v7 ✅

## 二、执行 Plan

### 批 1：实现 5 个接口（后端）
每个接口：路由 + 数据聚合（真实 SQL，非 mock）+ 入参数校验

### 批 2：接口测试（每接口 ≥2 条用例）
tests/test_gap_apis.py，覆盖正常/边界/越权

### 批 3：前后端连调
- proto 前端加 `api.js` 适配层（mock 与真实接口可切换：`USE_REAL_API` 开关）
- 5 个新接口的 mock 引用处改为走真实接口（降级回 mock）
- Playwright 实测：登录 → 各页数据来自后端

### 批 4：验收 + 收尾
- 全量测试（33+5新单测 / 95+5接口 / 8 e2e / 10 smoke）
- PDF 更新 + 文档同步（53/56/57 更新）

## 三、验收标准

| # | 项 | 标准 |
|---|---|---|
| V1 | 5 接口实现 | 路径/方法/出参形状与 53 号契约一致（JSON 字段名逐一对齐） |
| V2 | 接口测试 | 每接口 ≥2 用例（正常+边界），全部通过 |
| V3 | 越权保护 | 访问他人数据返回 404/403（user_id 过滤下推 SQL） |
| V4 | 连调验证 | Playwright 登录后前端请求真实接口（network 可见 /api/ 请求返回 200） |
| V5 | 降级回退 | USE_REAL_API=false 时前端仍正常（mock 全通过） |
| V6 | 零回归 | 全量 146+ 测试全绿 |
| V7 | 文档同步 | 53/56/57/README 状态更新 |

## 四、连调策略（关键决策）

前端**渐进式切换**：加 `api.js` 统一层 + `USE_REAL_API` 开关（localStorage 或常量）。默认 **mock**（保证展示稳定），验收时打开开关验证真实接口，全部通过后再默认切真实。

> 理由：mock 版已通过全部视觉验收，一次性切真数据风险大；开关式切换让前后端可以独立演进。
