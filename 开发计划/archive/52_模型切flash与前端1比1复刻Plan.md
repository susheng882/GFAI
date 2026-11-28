# 52 · 模型切换 flash + 前端 1:1 复刻 · 执行 Plan（等你确认后开工）

> 日期：2026-11-28　｜　基准原型：`F:/output/gflc_prototype_v7l.html`
> 三件事：① 后端模型全切 flash ② 前端按原型 1:1 复刻（纯 mock）③ 接口文档与后端对齐

---

## 一、现状侦察结论（已核实）

| 项 | 现状 |
|---|---|
| 后端 light/mid 档 | ✅ 已是 `deepseek-flash` |
| 后端 strong 档 | ⚠️ 还是 `deepseek-v4-pro`（需改 flash） |
| ARK 视觉/笔记模型 | ✅ 已是 `deepseek-v4-1-flash-261017` |
| 前端 proto | ✅ 15 页面，**已 100% 纯 mock**（107 个数据对象，零 API 调用） |
| 前端框架 | React 19 + Tailwind（Apple 白），无 antd 依赖 |
| 已有组件 | ui.jsx（Card/SectionTitle/Badge/Btn/Progress/Empty/Kpi/KeyCap）+ NavIcons.jsx |

## 二、执行步骤（4 阶段）

### 阶段 0：模型切 flash（10 分钟）
- `app/core/config.py`：LLM_STRONG_MODEL → `deepseek-flash`
- `.env`：LLM_STRONG_MODEL=deepseek-flash
- 跑 33 单测 + 95 回归确认不破

### 阶段 1：原型差距审计（产出逐页对照表）
- 用脚本提取 v7l 的 13 视图 DOM 结构 + 文案，与 proto 15 页面逐项对照
- 输出：`_52_复刻差距表.md`（每页：缺什么/差在哪/改什么）

### 阶段 2：逐页 1:1 复刻（Agent 分批）
| 批 | 页面 | 重点 |
|---|---|---|
| 1 | dash | 四指标/周目标/最近学习/热力图/卡片分布/系统信息/AI用量 7 块布局与文案 |
| 2 | notes/docs | 文件树整合（已做）+ 三态 + 存储条 |
| 3 | recite/review + packs/deck | 卡片墙 4×4 + 记忆轨道 + 卡包网格 |
| 4 | quiz/study + bank + upload | 答题卡 10 列 + 题库管理 + 解析上传 |
| 5 | plan + growth | 日历三视图 + 成长记录 |
| 6 | video + settings + auth + ai | 视频解析 + 设置中心 + 登录 + AI 伴侣 |

### 阶段 3：接口文档交付 + 后端对齐
- 按 mock 数据形状写 `53_前端接口契约.md`（每接口：路径/方法/入参/出参 JSON 示例）
- 与后端现有 21 路由模块对照，标注「已有/需改/需新增」
- 已对齐的接口本阶段不实现（等前端切真数据时再接）

### 阶段 4：验收 + PDF
- 跑 52 号验收标准全部门禁
- 13 页截图 + PDF

## 三、组件/Skill 使用决策

| 需求 | 方案 |
|---|---|
| 图标 | 已有 NavIcons.jsx（内联 SVG 线条图标，统一 1.5 stroke） |
| 动效 | 已有 CSS（animate-fade-up/slide-in + ease-apple） |
| 图表 | 自绘 div/flex（热力图 grid、柱状 flex、折线 SVG），不引图表库 |
| 日历 | 原型 c7 组件族为 Tailwind 自绘，proto 已有 planMonth/week/day mock，前端自绘对齐 |
| 拖拽调宽 | 已实现（侧栏/视频右栏） |
| 空态 | 已升级 Empty 组件（虚线框版） |

> 不新增 npm 包；组件全部用现有 ui.jsx + NavIcons.jsx + Tailwind utilities。

## 四、请拍板 3 件事

1. **strong 档也切 flash 吗？**（问答/出题质量会降一点，但省钱提速——你说了"改成 flash"，我理解是全切）
2. **复刻顺序**：按阶段 2 的 6 批做，还是你先指哪几页？
3. **接口文档**：先出文档不接真数据（推荐），还是文档+后端一起改？

确认后立即开工。
