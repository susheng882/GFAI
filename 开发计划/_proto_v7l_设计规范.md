# GFLC 原型 v7l 重构设计规范

> 分析对象：`F:/output/gflc_prototype_v7l.html`（706KB 单文件，5653 行，内联 Tailwind CDN + 自定义 CSS + 原生 JS）
> 对标现有：`F:/GrowthForward_AI学习伴侣/gflc/web/src`（React 19 + antd 5 + 自定义 app.css/theme.css，14 页面）
> 生成时间：2026-11-27

---

## 一、布局骨架（ASCII 图）

### 1.1 全局骨架（AppShell）

```
┌─────────────────────────────────────────────────────────────────────────┐
│ body.bg-base-200.text-ink  (背景 #F5F5F7)                              │
│ ┌──────────────┬────────────────────────────────────────────────────┐   │
│ │  #sb 侧栏     │  div.flex-1.min-w-0.flex.flex-col 主区            │   │
│ │  w-[228px]   │ ┌────────────────────────────────────────────────┐ │   │
│ │  (收起64px)  │ │ header.h-12 (48px) 顶栏                        │ │   │
│ │  bg 雾面毛玻璃│ │  面包屑 | 搜索框260px | 铃铛 | 用户菜单        │ │   │
│ │  ─────────── │ ├────────────────────────────────────────────────┤ │   │
│ │  品牌区 58px │ │ main.flex-1.min-h-0.p-3 (内边距12px)           │ │   │
│ │  工作区切换  │ │  ┌──────────────────────────────────────────┐  │ │   │
│ │  nav 导航    │ │  │ section.view.on.flexv.h-full.gap-3      │  │ │   │
│ │  (概览/资料/ │ │  │  各视图按需 flex / grid 布局             │  │ │   │
│ │   练习/系统) │ │  │  (gap-3 = 12px)                        │  │ │   │
│ │  ─────────── │ │  └──────────────────────────────────────────┘  │ │   │
│ │  连续天数卡  │ └────────────────────────────────────────────────┘ │   │
│ │  用户信息    │                                                    │   │
│ │  收起侧栏按钮│                                                    │   │
│ └──────────────┴────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**层级关系（三栏结构）**
- **左侧第一栏**：`#sb`（工作区列表 + 导航 + 用户区），宽 `228px`，可折叠至 `64px`（`body.sb-mini` / `html[data-sbmini="1"]` 双通道驱动，`v7l` 样式块）。
- **顶栏**：`header.h-12`，高 48px，半透明白 + 毛玻璃（`backdrop-filter: saturate(180%) blur(22px)`）。
- **主内容区**：`main`，内边距 `p-3`（12px），视图间 `gap-3`（12px）。

**视图切换机制**：`.view{display:none}` / `.view.on{display:block}` / `.view.on.flexv{display:flex}`，由 JS `show(v)` 控制；`growth` 视图是 `plan` 的别名（滚动到底部）。

### 1.2 各视图栅格布局（几栏 / 比例）

| 视图 | 结构 | 栅格 |
|---|---|---|
| **dash** 仪表盘 | 左 flex-1 + 右 rail 320px | `dashSystem` 内 `grid-cols-2 grid-rows-2`；统计卡 `grid-cols-4`；`#v-dash aside.rail` 默认 `display:none`（v7a 收敛为纯系统信息态） |
| **plan** 学习计划 | 上下两大区块 + 右 rail 320px | `#v-plan.on{grid-template-columns:minmax(0,1fr) 320px; grid-template-rows:100% calc(100%+224px)}`；成长记录区块内 `grid-cols-5`、`grid-cols-[1fr_248px]`、热力图 `grid-flow-col grid-rows-7` |
| **analyze** 视频解析 | flex + 右栏 248px | 播放器 `aspect-ratio:16/9`；字幕区 + 时间轴；右栏 AI 笔记（大纲/图文/背记三 tab） |
| **vidup** 解析上传管理 | flex + 右栏 248px | 任务列表 `grid-cols-[46px_1fr_84px_96px_64px_132px]`（6 列定宽）；右栏队列概览 `grid-cols-2` |
| **notes** 资料笔记 | 树 228px + 主 flex-1 | 列表态 `grid-cols-[26px_1fr_64px_112px_50px_92px_62px]`（7 列）；网格态 `grid-cols-4 grid-rows-3`；分栏态 `grid-cols-[1fr_1.3fr_256px]`（三态由 `data-seg` 切换） |
| **packs** 卡片包 | flex-1 + 右 rail 320px | 卡包卡 `grid-cols-3 grid-rows-2`；右栏复习计划/掌握度分布 |
| **recite** 背诵 | 卡包树 218px + 主 flex-1 | 卡片墙 `grid-cols-4 grid-rows-4`；单卡精背态 flip-card + 右 196px 评分栏 |
| **quiz** 刷题 | 左 flex-1 + 右 rail 320px | 答题卡 `grid-cols-10`（10 列）；进度 `qSeg` 10 段 flex |
| **bank** 题库管理 | 树 168px + 表格 flex-1 + 右 rail 320px | 表格 `<table>`；右栏概览 `grid-cols-2` |
| **upload** 上传解析 | 树 168px + 主 flex-1 + 右 rail 320px | 拖拽区 + 解析队列 |
| **settings** 系统设置 | set-tabs 168px + 主 flex-1 | 表格型；transcriber `grid-cols-2` |
| **auth** 登录账号 | flex-1 + 右 rail 320px | 账号信息 `grid-cols-3` |
| **ai** AI 伴侣 | 会话列表 190px + 聊天 flex-1 + 引用 236px | 三栏 |

### 1.3 顶栏结构（header.h-12）

```
[面包屑: 工作区名 > 返回按钮(隐藏) > crumb标题] ── 搜索框(260px ⌘K) ── 铃铛 ── 分隔线 ── 用户头像+菜单
```

---

## 二、设计 Token 表（全部具体值）

### 2.1 颜色

**主色（苹果蓝）**

| Token | 值 | 用途 |
|---|---|---|
| `--p` / `bg-primary` / `text-primary` | `#0071E3` | 主按钮、选中态、链接、图表主色 |
| `bg-primary-soft` | `#E3ECFF`（近 `#E8F1FD`） | 选中/徽标底色 |
| `bg-primary-hover` | 深一档 | 主按钮 hover |
| `bg-primary-mid` | 中阶蓝 | 进度条次级 |
| `bg-primary-pale` | 浅阶蓝 | 进度条弱级 |
| `bg-primary-wash` | 最浅蓝 | 热力图最浅格 |
| `border-primary-line` | 蓝描边 | 卡片描边、高亮框 |
| `bg-primary-line-2` | 蓝描边 2 | 刷题进度未答段 |

**中性色（纸白 / 灰阶）**

| Token | 值 | 用途 |
|---|---|---|
| `bg-base-100` | `#FFFFFF` | 卡片背景 |
| `bg-base-200` | `#F5F5F7` | 页面背景 |
| `bg-base-300` / `bg-soft-deep` | `#F2F2F5` | 内嵌分段容器底 |
| `bg-sunken` | `#EFEFF3` 附近 | 凹槽/进度槽底 |
| `text-ink` | `#1D1D1F` | 主文字 |
| `text-ink-subtle` | `#6E6E73` | 次级文字 |
| `text-ink-muted` | `#86868B` | 弱化文字 |
| `text-ink-faint` | `#A1A1A6` | 最弱文字/占位 |
| `border-line` | `rgba(0,0,0,.07)` | 常规描边 |
| `border-line-soft` | `rgba(0,0,0,.045)` | 极淡描边 |
| `border-line-strong` | 深一档 | 输入框/强调描边 |
| `bg-neutral` / `bg-ink` | `#1D1D1F` | 深色按钮、浮动条底 |

**语义色**

| Token | 值 | 用途 |
|---|---|---|
| `--su` / `bg-ok` / `text-ok` | `#1A7F43` | 成功/已解析 |
| `bg-ok-wash` / `bg-ok-soft` | 绿浅底 | 成功徽标底 |
| `--er` / `bg-danger` / `text-danger` | `#D70015` | 危险/删除/错题 |
| `bg-danger-soft` / `bg-rose-soft` | 红浅底 | 危险徽标底 |
| `--wa` / `bg-sand` / `text-sand-ink` | `#B25000` | 警告/待处理 |
| `bg-sand-soft` / `bg-sand-deep` | 橙浅底 | 警告徽标底 |
| `bg-rose-wash` / `text-rose-ink` | `#C8453A` 系 | 视频/图片类型标识 |
| `text-secondary` | 次强调蓝 | 思路标签 |

**毛玻璃 / 浮层**

| 位置 | 值 |
|---|---|
| `#sb` 侧栏 | `rgba(255,255,255,.66)` + `backdrop-filter: saturate(180%) blur(24px)` + `border-right: rgba(0,0,0,.055)` |
| `header.h-12` 顶栏 | `rgba(255,255,255,.70)` + `blur(22px)` |
| `.overlay` 遮罩 | `rgba(0,0,0,.26)` + `blur(3px)` |
| `.overlay .pop/.sheet` 浮层 | `rgba(255,255,255,.80)` + `blur(30px)` |
| `#toast>div` | `rgba(29,29,31,.82)` + `blur(18px) saturate(180%)` |

### 2.2 圆角（Tailwind 档）

| 档位 | 值 | 典型用途 |
|---|---|---|
| `rounded-[4px]` | 4px | 小徽标、检查点、进度小格 |
| `rounded-[5px]` | 5px | 内联按钮、状态标签 |
| `rounded-[6px]` | 6px | 图标底座、小输入 |
| `rounded-[7px]` | 7px | 图标容器、次级按钮 |
| `rounded-[8px]` | 8px | 输入框、tab、列表行 |
| `rounded-[9px]` | 9px | 内嵌统计卡、分段 |
| `rounded-[10px]` | 10px | 导航项、按钮、卡包分组 |
| `rounded-lg` / `rounded-xl` | 12px | **卡片主圆角** |
| `rounded-2xl` | 16px | 弹窗、翻转卡、大区块 |
| `rounded-full` | 9999px | 胶囊、头像、进度条 |

### 2.3 阴影

| 场景 | 值 |
|---|---|
| 常规卡片 | `0 1px 2px rgba(29,29,31,0.06)` |
| 卡片 hover / 选中 | `0 6px 18px rgba(0,113,227,0.10)`（+ `border-primary/45`） |
| 浮层（下拉/抽屉/弹窗） | `0 1px 2px rgba(0,0,0,.05), 0 12px 40px rgba(0,0,0,.12)` |
| 弹窗 dialog | `0 24px 64px -12px rgba(29,29,31,0.28)` |
| 命令面板 | `0 16px 48px rgba(29,29,31,0.18)` |
| toast / 浮条 | `0 8px 24px rgba(29,29,31,0.24)` |
| 深色操作条（已选） | `0 8px 24px rgba(29,29,31,0.30)` |
| 选中 chip | `0 2px 6px rgba(0,113,227,.22)` |
| 分段选中（seg-on） | `0 1px 2px rgba(29,29,31,.10)`（v7k 覆盖 `0 1px 3px rgba(0,0,0,.10)`） |

### 2.4 字号体系

| 档位 | 值 | 用途 |
|---|---|---|
| `text-[10px]` | 10px | 徽标、表格、辅助说明、次级元数据（**主力档**） |
| `text-[11px]` | 11px | 列表正文、tab、按钮文字 |
| `text-[12px]` | 12px | 卡片标题、表头、导航正文 |
| `text-[13px]` | 13px | 区块标题、卡包名、菜单项 |
| `text-[14px]` | 14px | 品牌名、大标题 |
| `text-[16px]`/`text-[19px]` | 16/19px | 指标大数值、弹窗标题 |
| 数字统一 `font-variant-numeric: tabular-nums`（`.num`） | — | 所有时间/数量/百分比 |

### 2.5 间距体系

| 档位 | 值 | 用途 |
|---|---|---|
| `gap-1` / `p-1` | 4px | 紧凑图标间距 |
| `gap-1.5` / `p-1.5` | 6px | 内联元素、列表行 |
| `gap-2` / `p-2` | 8px | 卡片内、工具条 |
| `gap-2.5` / `p-2.5` | 10px | 卡包卡内边距 |
| `gap-3` / `p-3` | 12px | **视图/卡片主间距、主区内边距** |
| `gap-3.5` / `p-3.5` | 14px | 大区块 |
| `gap-4` / `p-4` | 16px | 刷题题干区 |
| `px-3` / `px-3.5` | 12/14px | 卡片头水平内边距 |
| 栅格 4px 基准；图标 `w-6/h-6`(24px)、`w-7/h-7`(28px)、`w-9/h-9`(36px) | — | — |

---

## 三、组件清单（每个含 class 与样式要点）

### 3.1 卡片 Card
- **class**：`rounded-xl bg-base-100 border border-line shadow-[0_1px_2px_rgba(29,29,31,0.06)] flex flex-col overflow-hidden`
- **要点**：头 `h-9/h-10 shrink-0 px-3 flex items-center border-b border-line-soft`（标题 12px + 右侧操作链接）；体 `flex-1 min-h-0 p-2/2.5`。
- **变体**：`bg-card`（白底无边框阴影）、`bg-soft`（浅灰内嵌）。

### 3.2 按钮 Button
- **主按钮**：`h-8 px-3 rounded-md bg-primary text-white font-medium hover:bg-primary-hover`
- **次按钮**：`h-8 px-3 rounded-md border border-line bg-base-100 text-ink-muted hover:bg-soft`
- **幽灵/文字**：`text-[10px] text-primary hover:underline`、`hover:bg-soft` 图标钮
- **危险**：`bg-danger text-white` 或 `text-danger`
- **深色条内**：`bg-white/12 border-white/25 hover:bg-white/20`
- **尺寸**：`h-6/h-7/h-8/h-9`（24/28/32/36px），圆角 6-8px。

### 3.3 分段控件 / Tab
| 组件 | class | 选中态 |
|---|---|---|
| 视图级 tab（dash） | `.dash-tab h-7 px-2.5 rounded-[7px]` | `aria-selected` + `bg-white shadow-[0_1px_3px]` |
| 笔记 tab | `.note-tab h-[22px]`（grid 3 等分） | 同上 |
| 刷题 tab | `.qtab h-[26px] rounded-[8px]` | `.qtab.on` 白底加粗 |
| 设置 tab | `.set-tab h-8 rounded-[8px]` | `.set-tab.set-on bg-primary text-white` |
| 日历分段 | `.c7-seg h-6 px-2 rounded-[6px]` | `.c7-seg.on bg-white shadow` |
| 通用分段 | `.seg-on` | `bg-white color-primary shadow` |
| 容器 | `bg-soft-deep p-0.5 rounded-[8px]`（`data-seg-group`） | — |

### 3.4 树 Tree
- **资料树**：`.tree-row`（`h-[25-28px] rounded flex gap-1.5 hover:bg-soft`）+ `.tree-kids pl-4` + 展开箭头 `.ln.tw`（`.tree-node.closed` 旋转 -90°）
- **文件夹树（通用 ft）**：`.ft-row`（`h-[24px] rounded-[6px] text-[11px]`，`.on bg-EFEFF2 font-600`，`.dropping bg-EFF6FF ring`）+ `.ft-kids`（`margin-left:10px; border-left:1px solid #EFEFF2`）+ `.ft-caret`（transition .2s）
- **要点**：数量 `.ft-cnt` 灰色 tabular-nums；支持拖拽投递（`.dropping`）。

### 3.5 抽屉 / 弹窗 / Toast
| 组件 | class | 样式要点 |
|---|---|---|
| 抽屉 sheet | `.overlay.justify-end` + `.sheet w-[340px] h-full bg-card-warm-2` | 右滑入 `slideIn .26s cubic-bezier(.32,.72,0,1)` |
| AI 整理面板 | `#aiTidy .sheet w-[420px]` | z-index 80（高于 streak 70） |
| 弹窗 dialog | `<dialog class="modal rc-modal">` + `.modal-box rounded-2xl` | `rcBoxIn .24s cubic-bezier(.16,1,.3,1)` |
| 路径选择弹窗 | `#pathDlg` 固定居中，`w-[420px] rounded-xl` | 内嵌 ft 树 + 新建/取消/确定 |
| Toast | `#toast` 底部居中，`h-9 rounded-md bg-ink text-white shadow` | 1.6s 自动消失 |
| 提示条 | `#noteTip` / `#streakTip` 右下角胶囊 | 可关闭 + 记忆关闭状态 |

### 3.6 进度条 / 徽标 / 状态
- **进度条**：`.h-1/.h-1.5/.h-[5px]/.h-[6px] rounded-full bg-sunken overflow-hidden`，内 `.block h-full rounded-full bg-primary`（宽 = 百分比）
- **徽标 badge**：`h-[15-20px] px-1.5 rounded-full bg-{color}-soft text-{color} text-[10px] grid place-items-center`
- **状态胶囊**：`.inline-flex items-center gap-1` + 圆点 `w-1.5 h-1.5 rounded-full`
- **标签 chip**：`h-[19px] px-1.5 rounded-full border border-line text-[10px] text-primary`

### 3.7 图表（SVG 内联）
- 折线/面积图：`<svg viewBox="0 0 268 92" preserveAspectRatio="none">` + `linearGradient`（`#0071E3` 22% → 0）
- 柱状图：flex + `bg-primary/bg-primary-pale` 高度百分比
- 热力图：`grid grid-flow-col grid-rows-7 gap-[3px]` + 四阶蓝（wash/pale/mid/primary）
- 能力热力条：五维，每维 5 段 `h-[9px] rounded-[2px]`

### 3.8 其他
- **下拉菜单**：`#menu-ws/#menu-user`，`rounded-[12px]/rounded-md shadow-[0_10px_30px]`，毛玻璃
- **命令面板**：`#cmdk`，`w-[560px] rounded-xl`，快捷动作 + 最近 + 快捷键提示
- **翻转卡**：`.flip-card .flip-inner`（`transition transform .46s cubic-bezier(.32,.72,0,1)` + `preserve-3d`），`.flip-face/.flip-back backface-hidden`
- **选择操作条**：`#selBar` 底部固定深色胶囊（笔记多选、卡包多选）
- **空态/新建卡**：`.rc-add` 虚线框 `border-dashed border-line` + hover 变蓝
- **文件类型图标**：`w-[26px] h-[26px] rounded-md` + 类型色底（PDF 红/笔记蓝/图片橙/视频 sand）

---

## 四、动效规范（名称/时长/缓动/场景）

### 4.1 @keyframes 定义

| 名称 | 定义 | 场景 |
|---|---|---|
| `rcCardIn` | `from{opacity:0;translateY(6px)} to{opacity:1;none}` | 背诵卡墙卡片入场 |
| `rcBoxIn` | `from{opacity:0;translateY(10px) scale(.965)}` | dialog 弹窗入场 |
| `rcBoxOut` | `to{opacity:0;translateY(6px) scale(.985)}` | dialog 弹窗出场 |
| `rcFadeIn` / `rcFadeOut` | opacity 0↔1 | dialog 背景遮罩 |
| `fadeIn` | opacity 0→1 | overlay 遮罩 |
| `popIn` | `scale(.97)→scale(1)` | 命令面板 pop |
| `slideIn` | `translateX(100%)→0` | 抽屉 sheet |
| `pulseAn` | `opacity 1→.45→1`（1.8s 无限） | 脉冲指示（`.pulse`） |
| `v7lIco` | `opacity .35 scale(.86)→1` | 侧栏收起后图标淡入 |

### 4.2 缓动曲线 & 时长

| 时长 | 缓动 | 场景 |
|---|---|---|
| 150ms | `ease-out` | 按钮 hover、chip、分段切换（`transition-colors`） |
| 160ms | `ease-out` | 卡片/模式 hover 色变 |
| 180ms | `ease-out` | pop、侧栏文字淡出 |
| 200ms | `ease-out` | 卡片/列表 hover 位移+阴影（**主力**） |
| 220ms | `ease-out` | 侧栏折叠图标旋转 |
| 240ms | `cubic-bezier(.16,1,.3,1)` | 卡片/弹窗入场（指数缓出） |
| 260ms | `cubic-bezier(.32,.72,0,1)` | 抽屉滑入 |
| 300ms | `ease-out` | 进度条宽度、掌握度条 |
| 460ms | `cubic-bezier(.32,.72,0,1)` | 翻转卡翻面 |

### 4.3 硬约束（v7l 明确声明）
- 过渡**仅 transform / opacity**，150–280ms ease-out，避免布局抖动。
- 所有动效受 `@media (prefers-reduced-motion: reduce)` 保护（关闭动画/过渡）。
- 键盘可达：`focus-visible` 统一 `outline: 2px solid rgba(0,113,227,.45)`。
- 卡片 hover 统一模式：`hover:border-primary/45 + hover:shadow-[0_6px_18px_rgba(0,113,227,0.10)] + hover:-translate-y-px`。

---

## 五、14 视图功能清单（每视图 5-10 行）

### 1. dash 仪表盘（v-dash，行 555-734）
- 顶部 dashTabs（系统信息/学习），默认且仅「系统信息」态（v7a 收敛，隐藏 dashStudy 与右 rail）。
- 系统信息卡：版本/运行环境/后端服务/索引状态/数据库/向量库 + CPU/内存/磁盘三进度条。
- 模型配置卡：豆包 1.5 Pro、DeepSeek V3、本地 Whisper、网格 OCR 四行（已连接/待同步徽标）。
- 最近上传解析卡：视频/PDF 列表 + 已解析/识别中徽标。
- 系统 AI 用量卡：今日调用/tokens/成本/失败率 + 双线柱状图 + 模型成本分布条。
- 状态徽标：索引已就绪、同步 09:42、运行正常。

### 2. plan 学习计划（v-plan，行 736-963）
- 上区块「学习计划」：本周目标条（62% 进度）+ 周报/新建任务按钮。
- 日历三视图：月/周/日（`c7-*` 组件族），月视图 7×6 网格、周视图时段网格+任务条、日视图时间轴+日程块+右侧统计。
- 右 rail：计划模板 4 个（艾宾浩斯/真题驱动/每日2h/章节通关）+ AI 生成计划输入。
- 下区块「成长记录」：学习天数/累计时长/背卡/正确率/达成率五指标 + 等级进度。
- 能力热力图（五维记忆/理解/速度/正确率/坚持）+ 今日任务 6 项勾选 + 学习热力图（84 天）+ 计划联动 + 学习日记 4 条 + 成就与等级/里程碑/成长建议。

### 3. analyze 视频解析（v-analyze，行 965-1173）
- 顶条：BV 号/分辨率/已切段/卡片数徽标 + 重新切片/复制链接/转为笔记。
- 视频播放器（16:9 深色）+ 段指示（第3段/共8段）+ 字幕/倍速/播放控制 + 进度条（8 段刻度）。
- 时间轴：8 个段缩略卡（时间+卡数）+ 全选/反选/仅未学。
- 字幕条目：ASR 转写 133 条 + 中/EN/复制 + 点击 seek。
- 右栏 AI 笔记：大纲/图文/背记三 tab + 笔记风格 select（学术/口语/考点/思维导图）+ 保存/生成/导出。
- 底部：已选段数 + 生成练习题/背诵卡/AI 讲解。

### 4. vidup 解析上传管理（v-vidup，行 1175-1344）
- 上传视频区：拖拽区（mp4/mov/mkv/webm ≤4GB）+ 选择文件 + 粘贴 B站/慕课链接。
- 解析任务表（6 列定宽）：文件/名称/时长状态/进度/耗时/操作（重跑/删除/笔记）。
- 6 个任务态：处理中 62%/28%/9%、排队中、已完成、失败（音轨缺失）。
- 右栏：解析设置（切片粒度/识别语言/完成后自动生成/并发上限）+ 队列概览（处理中/排队/完成/失败）+ 今日解析统计 + 失败提示。

### 5. notes 资料笔记（v-notes，行 1346-1791）
- 左树 228px：资料库（专业课/公共课/错题与复盘/速记卡/视频课程/复盘）+ 存储占用条。
- 工具条：列表/网格/分栏三态切换 + 搜索 + 类型/排序筛选 + AI 出题/解释/整理文档/整理笔记 + 上传资料。
- 列表态：7 列（复选/名称/类型/文件夹/卡片/更新时间/大小），18+ 条真实文件。
- 网格态：`grid-cols-4 grid-rows-3` 卡片（类型徽标 + 卡数 + 掌握度进度条）。
- 分栏态：目录列表 + 预览正文 + 属性（类型/页数/进度/标签/关联卡片）。
- 视频解析笔记面板（vnotePane）：章节时间轴 + 笔记正文 + 导出/重跑/生成卡。
- 底部选择操作条（selBar）：已选 N 项 + 加标签/移动/生成卡片/取消。

### 6. packs 卡片包（v-packs，行 1792-1913）
- 顶部：卡包分段筛选（全部/OS/CN/DS/CO/数学/英语）+ 掌握度/排序 + AI 出题/解释 + 新建卡包。
- 卡包卡 `grid-cols-3 grid-rows-2`：学科徽标 + 卡数 + 掌握度进度条 + 复习时间 + 进入背诵（6 个卡包）。
- 底部深色操作条：已选 N 包 + 合并/导出/开始背诵。
- 右 rail：今日复习计划（4 项 71 张 + 时间线）+ 掌握度分布（熟练/记得/模糊/忘记）+ 调度建议（优先/其次/跟进）。

### 7. recite 背诵（v-recite，行 1914-2325）
- 左卡包树 218px：4 组（DS/OS/CN/CO）+ 子章节 + 记忆轨道（R1-R4 分布）+ 今日队列（新卡/到期/生疏/已熟）。
- 工具条：卡片墙/单卡精背模式切换 + 搜索 + 筛选 chip（全部/到期/易错/新卡）。
- 卡片墙：`grid-cols-4 grid-rows-4` 15 张卡（学科徽标 + R 轮次 + 标题 + 摘要 + 章节 + 复习时间）+ 生成新卡入口。
- 单卡精背：flip-card 翻面（正面回忆三点 + 背面核心要点/口诀）+ 右栏回忆质量 1-4 评分（忘记1天/模糊3天/记得7天/熟练14天）+ 本卡易错 + 记忆强度条。
- 弹窗预览（rcPreview 820px）：核心要点/易错点/例题/口诀/关联知识点 + 上一张/下一张/标记掌握。

### 8. quiz 刷题（v-quiz，行 2326-2412）
- 顶条：返回题库列表 + 题库名/标签/统计 + 今日进度。
- 题干区：题型/学科/第 N 题/计时器/正确率/难度 + 10 段进度条。
- 选项 4 个（A/B/C/D 圆形字母 + 悬停变蓝）+ 答题提示（三点引导）+ 相关跳转。
- 解析区：回答正确/标准答案/用时/全站正确率 + 考点/思路/推导/易错/延伸五标签 + 同类真题。
- 底部：上一题/收藏/AI 讲解/提交答案 + 答题卡 `grid-cols-10`。
- 右 rail：本组题况（正确率/错题/剩余）+ 错题分布 + 智能提示（生成抽查卡）+ 本题统计（选项分布）+ 关联知识点。

### 9. bank 题库管理（v-bank，行 2413-2481）
- 顶条：题库数/题量 + 上传解析/新建题库。
- 左文件夹树 168px：全部/学科/年份/类型（`ft-row` 组件，可新建文件夹）。
- 筛选条：搜索 + 来源/状态筛选 + 当前路径 + 解析保存路径（pickPath 弹窗）。
- 题库表格：复选/名称/题量/来源/状态/正确率/更新时间/操作（进入刷题/删除/重试），6 个题库 + 分页。
- 右 rail：题库概览（总数/题目/已解析/待校对）+ 解析队列（后台 worker）+ 来源分布。

### 10. upload 上传题库解析（v-upload，行 2482-2547）
- 顶条：返回题库列表 + 解析中 N 文件 M 题徽标。
- 左文件树 168px（按学科/年份/类型分组）。
- 拖拽区：PDF/DOCX/JPG/PNG/TXT 支持 + 解析队列（6 文件 524 题 + 进度/状态）。
- 底部：解析保存路径选择 + 自动去重/AI 补全解析/错题进错题本勾选 + 暂停全部/开始解析。
- 右 rail：解析规则 4 条（版面还原/题干切分/AI 补全/去重校验）+ 最近解析记录 + 解析预览（抽取第 2 题 + 答案置信度）。

### 11. settings 系统设置（v-settings，行 2547-2828）
- 顶条：后端 /api/settings 连接状态 + 密钥 Fernet 加密徽标 + 新增模型。
- 左 set-tabs 168px：供应商/模型/转录器/Cookie/本地文件库/数据备份/诊断/监控/账号 + 版本号。
- providers：供应商表格（名称/类型/Base URL/Key 掩码/默认/启用）+ 模型表格（用途默认/探活）。
- models：用途维度绑定 + 探活状态（连通 ms/超时/未探活）+ 全部探活。
- transcriber：取材策略/Whisper 模型/并行片数/并发 + toggle 开关组。
- cookie：bilibili/youtube/douyin 三平台 Cookie 配置（已配置/未配置）。
- diag：FFmpeg/Whisper 权重/B站 Cookie/供应商/向量库/OCR/磁盘 7 项检测。
- monitor：系统状态（失败率/队列积压/成本）+ 用量趋势图 + 模型调用分布 + 成本明细表。
- vault：本地文件库同步（目录/同步状态）+ backup：备份/校验/恢复命令 + account：导出/账号信息/注销。

### 12. auth 登录与账号（v-auth，行 2828-2910）
- 顶条：已登录 + 会话剩余时间。
- 账号卡：头像/昵称/邮箱 + Free 计划徽标 + 登录方式/首次登录/累计在线三格。
- 会话令牌：复制/吊销 + JWT 展示 + 登录设备列表（Windows/iPhone/iPad）。
- 右 rail：安全设置（改密/双因素/邮箱验证）+ 账号数据（导出/退出/删除账号）+ 注销确认 dialog（输入密码二次确认）。

### 13. ai AI 伴侣（v-ai，行 2911-3007）
- 左会话列表 190px：新建对话 + 搜索 + 今天/昨天分组 + 未读计数。
- 中间聊天区：用户/AI 气泡（圆角 + 小尾角）+ 引用标签 + 步骤轨迹（details 展开 4 步）+ 追问建议 chip。
- 深度思考 toggle + @资料/@错题/@计划 上下文 + ⌘Enter 发送。
- 右栏 236px：资料卡命中 4 篇（相关度）+ 引用明细（教材/真题页码）+ 置信度。

### 14. 全局浮层（非视图，行 3012-3132）
- 命令面板 cmdk（⌘K）：快捷动作（开始背诵/继续训练/解析视频）+ 最近 + 上下/回车键提示。
- 通知抽屉：27 张卡片到期 / 视频解析完成 / 连续 42 天达标。
- 连续天数浮层（streakTip 右下角胶囊）：连续 42 天 · 最佳 47，可关闭记忆。

---

## 六、现有项目差距清单（按「视觉/布局/功能/动效」分类）

> 现有：`gflc/web/src`（React 19 + antd 5 + ConfigProvider + 自定义 theme.css/app.css，14 页）。导航：概览/笔记/学习/复习/计划/任务/资料/题库/卡包/视频/问答/设置。

### 6.1 视觉差距

| # | 原型有 / 现有缺 | 说明 |
|---|---|---|
| V1 | **苹果白设计语言** vs 纸墨暖色 | 原型 `#F5F5F7` 白底 + `#0071E3` 苹果蓝 + 毛玻璃；现有是 `#f7f4ee` 暖纸 + `#1f4d6b` 墨蓝。两套设计系统完全冲突。 |
| V2 | **毛玻璃侧栏/顶栏** | 原型 `backdrop-filter: saturate(180%) blur(24px/22px)`；现有纯色 `var(--sidebar)`。 |
| V3 | **阴影体系** | 原型 6 档分层阴影（含苹果蓝 hover `0_6px_18px`）；现有几乎无卡片阴影。 |
| V4 | **圆角档位** | 原型 12 档（4-16px + full）；现有单一 `--radius:8px` 派生。 |
| V5 | **字号下沉** | 原型主力 10-12px（紧凑密集）；现有 antd fontSize 13.5px 偏大。 |
| V6 | **悬浮卡片交互** | 原型卡片 `hover:-translate-y-px` + 蓝描边 + 蓝阴影；现有仅背景色 hover。 |
| V7 | **苹果蓝状态徽标族** | 原型 `bg-ok-wash/bg-sand/bg-rose-soft` 圆点胶囊；现有语义色不同色相。 |

### 6.2 布局差距

| # | 原型有 / 现有缺 | 说明 |
|---|---|---|
| L1 | **三栏 AppShell**（228px 侧栏 + 主区 + 视图内 168-320px 右 rail） | 现有仅「固定侧栏 240px + 内容区」两栏，无视图内右 rail 概念。 |
| L2 | **侧栏收起动画（228→64px）** | 原型 `#sb` 双通道收起 + 图标淡入 `v7lIco`；现有 `.gflc-sider.collapsed` 有折叠但无同款动效细节。 |
| L3 | **工作区切换下拉（multi-workspace）** | 原型侧栏顶部「408 计算机冲刺」+ 下拉切英一/数一；现有无工作区概念。 |
| L4 | **顶栏内嵌搜索框（260px + ⌘K kbd）** | 原型顶栏常驻全局搜索；现有顶栏仅标题，搜索在命令面板内。 |
| L5 | **网格三态（列表/网格/分栏）** | 原型 notes 支持三种视图布局；现有 Documents/Notes 单态列表。 |
| L6 | **日历三视图（月/周/日）** | 原型 plan 内置 `c7-*` 月/周/日完整日历；现有 PlansPage 仅「目标→逐日任务列表」，无日历。 |
| L7 | **三栏聊天布局（会话190 + 聊天 + 引用236）** | 原型 ai 视图三栏；现有 QAPage 无会话列表、无右引用栏。 |

### 6.3 功能差距

| # | 原型有 / 现有缺 | 说明 |
|---|---|---|
| F1 | **AI 伴侣独立页（会话 + 引用溯源 + 步骤轨迹 + 深度思考）** | 现有 QAPage 是问答（三阶段流式 + 来源芯片），无会话历史、无引用明细栏、无「@资料/@错题/@计划」上下文、无步骤轨迹展开。 |
| F2 | **解析上传管理页（vidup）** | 原型独立「解析上传管理」视图（视频上传/链接/任务队列/设置/队列概览）；现有视频解析散落在 VideoPage，无独立上传管理队列视图。 |
| F3 | **成长记录/成就系统** | 原型 plan 下半区含成就等级（Lv/XP/里程碑/成长建议/能力五维热力图）；现有完全无成就/等级/里程碑模块。 |
| F4 | **答题卡（grid-cols-10 + 逐题定位）** | 原型刷题底部答题卡；现有 StudyPage 有 QuizAnswerSheet 但非 10 列胶囊形态。 |
| F5 | **卡片墙背诵模式（15 卡 4×4 + 筛选 chip + 记忆轨道）** | 原型 recite 有「卡片墙」与「单卡精背」双模式 + 记忆轨道 R1-R4 分布；现有 ReviewPage/StudyPage 仅单卡翻面 + 二元评分，无卡片墙、无 4 级评分（忘记/模糊/记得/熟练对应 1/3/7/14 天）。 |
| F6 | **背诵弹窗预览（核心要点/易错/例题/口诀/关联）** | 原型 rcPreview 五段式详览；现有翻卡无此深度预览。 |
| F7 | **题库解析保存路径（pickPath 文件夹树弹窗）** | 原型 bank/upload 有「解析保存路径」+ 拖拽归类树；现有无。 |
| F8 | **系统诊断页（FFmpeg/Whisper/OCR/磁盘检测）** | 原型 settings diag 7 项检测；现有 SettingsPage 有监控但无同款诊断表格。 |
| F9 | **本地文件库 vault 同步 + 数据备份命令** | 原型 settings vault/backup；现有无 vault 同步 UI 与备份命令展示。 |
| F10 | **通知抽屉 + 连续天数浮层（streakTip）** | 原型顶栏铃铛抽屉 + 右下角可关闭连续天数胶囊；现有无。 |
| F11 | **命令面板快捷动作（开始背诵/继续训练/解析视频）** | 原型 cmdk 有带图标快捷动作；现有 cmdk 仅「前往页面 + 新建笔记 + AI 整理 + 主题」命令。 |
| F12 | **工作区多账号/工作区切换** | 见 L3，功能层亦缺。 |

### 6.4 动效差距

| # | 原型有 / 现有缺 | 说明 |
|---|---|---|
| M1 | **卡片入场动画（rcCardIn 240ms 指数缓出）** | 现有 `pageIn/numPop` 命名不同、无卡片墙入场。 |
| M2 | **弹窗进出场（rcBoxIn/rcBoxOut + 背景 rcFade）** | 现有 antd Modal 默认动效，无自定义指数缓出曲线 `cubic-bezier(.16,1,.3,1)`。 |
| M3 | **抽屉 slideIn（260ms 弹性缓出）** | 现有无右滑抽屉组件（仅移动端侧栏 translateX）。 |
| M4 | **hover 位移 + 蓝阴影（-translate-y-px + 200ms ease-out）** | 现有 hover 仅背景色，无位移/阴影过渡。 |
| M5 | **翻转卡 460ms preserve-3d** | 现有 AiBoard/ReviewPage 有翻面（`dflip`），但缓动曲线与 3D 细节待对齐。 |
| M6 | **侧栏图标淡入（v7lIco）** | 现有折叠侧栏无图标淡入动画。 |

---

## 附：数据来源与核对方式

**原型文件（只读，未修改）**
- `Read F:/output/gflc_prototype_v7l.html` 分段通读：行 1-245（全部 `<style>` 块，含 tw-css/v5 背诵/v7j-tokens/v7k 文件夹树/apple-white-v6a/nav-compact/v7l 日历与侧栏）、行 379-590（侧栏+顶栏+仪表盘）、行 555-964（dash/plan 全文）、行 965-1344（analyze/vidup）、行 1346-1791（notes）、行 1792-1913（packs）、行 1914-2325（recite）、行 2326-2412（quiz）、行 2413-2547（bank/upload）、行 2547-2910（settings/auth）、行 2911-3007（ai）、行 3012-3132（cmdk/drawer/aiTidy/toast/streakTip）、行 3342-3420（rcPreview dialog + 卡片数据脚本）。
- `grep -n 'id="v-'` 定位 14 视图 section 行号。
- `grep -n 'keyframes\|animation:'` 提取全部动效定义（共 12 个 keyframes）。
- `grep -c 'grid-cols'`（57 处）+ `grep -o 'duration-*|ease-*'`（duration-200 出现 75 次为动效主力）统计栅格与动效频次。
- `grep -n 'id="toast"|id="rcModal"|id="pathDlg"|...'` 定位浮层组件。

**现有项目（只读，未修改）**
- `Read F:/GrowthForward_AI学习伴侣/gflc/web/src/theme.css`（229 行，纸墨 token 全量）。
- `Read F:/GrowthForward_AI学习伴侣/gflc/web/src/App.jsx` 行 280-311（antd ConfigProvider token：colorPrimary `#1f4d6b`、colorBgBase `#f7f4ee`、borderRadius 8、fontSize 13.5、controlHeight 34）。
- `grep -n 'Route|nav'` App.jsx 确认 14 页路由与菜单结构。
- `grep -rn '成就|日历|AI 伴侣|答题卡|卡片墙|上传管理'` 确认现有功能覆盖缺口（成就/日历/上传管理/AI 伴侣均无命中）。
- `wc -l` 各页面文件确认规模（现有总 6045 行源码，原型单文件 5653 行）。

**核对结论**：原型为「苹果白 + 毛玻璃」设计语言（主色 `#0071E3`、白底 `#F5F5F7`、圆角 12px、阴影分层、字号 10-12px、200ms ease-out 动效），现有项目为「纸墨暖色」设计语言（主色 `#1f4d6b`、暖纸底 `#f7f4ee`、圆角 8px、字号 13.5px）。两者在设计 Token、布局骨架（三栏 vs 两栏）、动效系统三个层面均需系统对齐；功能层面存在 12 项原型独有、6 项布局独有、7 项视觉独有、6 项动效独有的差距。
