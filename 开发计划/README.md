# 开发计划 · 文档索引（README）

> 本目录是 GFLC（GrowthForward 学习伴侣）的全部决策档案：计划、评审、验收、竞品调研。
> 索引编制：2026-11-23　｜　覆盖：`00`–`37` 共 **38 份** Markdown（编号连续无缺号）+ `mockups/` 原型目录
> 用途：新人接手 / 上下文恢复 / 追溯「某个结论是哪份文档、哪次验收定的」。
> 约定：**只增不改**——已验收的文档保留原结论，后续变更写新编号文档，不复写历史。

---

## 一、新人阅读顺序（建议 5 步）

| 步骤 | 读什么 | 为什么先读它 |
|---|---|---|
| 1 | [`00_开发总计划.md`](00_开发总计划.md) | 先建立范围感：做什么、不做什么、16 周节奏与验收口径 |
| 2 | [`02_多Agent协作开发规范.md`](02_多Agent协作开发规范.md) + [`14_多Agent开发约束与硬门禁.md`](14_多Agent开发约束与硬门禁.md) | 本项目是多人/多 Agent 并行，**文件所有权**是第一硬约束，不读会踩别人文件 |
| 3 | [`25_功能完成度阶段评审_2026-11-23.md`](25_功能完成度阶段评审_2026-11-23.md) | 一份文档看清「现在做到哪一步」，避免从 30 份历史里自己拼现状 |
| 4 | [`31_A+B全量交付验收报告_2026-11-23.md`](31_A+B全量交付验收报告_2026-11-23.md) | 最新一次验收的量化结论与遗留项，是当前基线 |
| 5 | [`15_评测集与部署门禁.md`](15_评测集与部署门禁.md) + 本文 [附录 A](#附录-a评测集evals-纳管方案) | 改动前后怎么证明「没退化」——评测集与回归门禁的用法 |

> 只想改前端：加读 `22`（布局规范）→ `29`（本地差距）→ `30`（收尾清单）。
> 只想动视频链路：加读 `18`（性能实测）→ `19`（对标 BiliNote 方案）。

---

## 二、文档索引

状态口径：**已验收** = 结论有实测数据且已回归；**进行中** = 已开工或待确认后继续；**仅调研** = 只产出结论，本身不改代码（结论已被后续计划吸收）。

### ① 总纲与规范（7 份）

| 编号 | 文件名 | 一句话说明 | 状态 |
|---|---|---|---|
| 00 | [00_开发总计划.md](00_开发总计划.md) | 项目总纲：范围、16 周排期、成本前置与「先闭环后增强」原则 | 已验收 |
| 01 | [01_前置资源清单.md](01_前置资源清单.md) | 本机环境核对（Docker/Python/Node），唯一外部依赖是 DeepSeek Key | 已验收 |
| 02 | [02_多Agent协作开发规范.md](02_多Agent协作开发规范.md) | 5 个 Agent 的角色分工与目录所有权，防并行踩踏 | 已验收 |
| 03 | [03_需求验收标准.md](03_需求验收标准.md) | 前两轮需求的逐条可测验收口径（试卷解析/公式保真等） | 已验收 |
| 04 | [04_第三轮优化验收标准.md](04_第三轮优化验收标准.md) | 第三轮（UI/问答质量/关键帧/成本管控）的验收口径 | 已验收 |
| 14 | [14_多Agent开发约束与硬门禁.md](14_多Agent开发约束与硬门禁.md) | 所有开发 Agent 的强制契约：所有权、回归不许削弱、完成度判定三类 | 已验收 |
| 15 | [15_评测集与部署门禁.md](15_评测集与部署门禁.md) | 离线评测集（32 资料 + 24 题、六指标）与 CI 回归门禁的落地记录 | 已验收 |

### ② 评审与报告（10 份）

| 编号 | 文件名 | 一句话说明 | 状态 |
|---|---|---|---|
| 05 | [05_阶段性报告.md](05_阶段性报告.md) | 第三轮迭代后的项目全景快照（定位/技术栈/已完成项） | 已验收 |
| 07 | [07_unslop改造报告.md](07_unslop改造报告.md) | 用 unslop 九道 pass 重做前端视觉，回归 95/95、9 页无 JS 报错 | 已验收 |
| 09 | [09_项目审查与优化报告_2026-11-22.md](09_项目审查与优化报告_2026-11-22.md) | 全量代码审计：判定「可演示 MVP 非可上线系统」，定位检索与视频慢的根因 | 已验收 |
| 12 | [12_技术产品报告进度差异评审_2026-11-22.md](12_技术产品报告进度差异评审_2026-11-22.md) | 报告蓝图 vs 实际实现的三根支柱差距（向量检索/进程隔离队列/生产数据栈） | 已验收 |
| 17 | [17_多维度评审报告_2026-11-22.md](17_多维度评审报告_2026-11-22.md) | 静态读码 + 动态实测的多维度评审，逐条附命令与行号 | 已验收 |
| 24 | [24_Wave1集成验收报告_2026-11-23.md](24_Wave1集成验收报告_2026-11-23.md) | Wave 1 四路 Agent 集成验收；如实记录 OCR 96.14s 未达 ≤90s | 已验收 |
| 25 | [25_功能完成度阶段评审_2026-11-23.md](25_功能完成度阶段评审_2026-11-23.md) | 全项目功能盘点 + 结构可维护性整理，学习闭环主链路全绿 | 已验收 |
| 31 | [31_A+B全量交付验收报告_2026-11-23.md](31_A+B全量交付验收报告_2026-11-23.md) | **A 层基线**：OCR 提速 + B 层 24 项收尾，全门禁通过 | 已验收 |
| 32 | [32_降级恢复与遗留补齐_2026-11-23.md](32_降级恢复与遗留补齐_2026-11-23.md) | 5 处降级全部恢复真实能力 + quality 档 DPI 180 已 A/B 证伪 | 已验收 |
| 33 | [33_遗留收尾与全量入库_2026-11-23.md](33_遗留收尾与全量入库_2026-11-23.md) | **最新基线**：5 项缺口补齐（热力图/告警/取消掌握/重试/测试）+ 全量入库 | 已验收 |

### ③ 计划与验收（12 份）

| 编号 | 文件名 | 一句话说明 | 状态 |
|---|---|---|---|
| 06 | [06_UI与体验改善计划.md](06_UI与体验改善计划.md) | 基于实拍的 UI 诊断与改法，后续由 07 / 11 分两轮落地 | 已验收 |
| 08 | [08_Dashboard重做_对标与验收.md](08_Dashboard重做_对标与验收.md) | Dashboard 重做的对标拆解与提案（`mockups/dashboard-v2.html`），待拍板 | 仅调研 |
| 10 | [10_真上线实施计划.md](10_真上线实施计划.md) | 真上线路径：打包链路修复 + S1–S6 安全加固；余下为买域名/服务器/备案 | 进行中 |
| 11 | [11_UX组件库重构_资源与验收.md](11_UX组件库重构_资源与验收.md) | 以体验为出发点、用现成组件库重构前端，零后端改动 | 已验收 |
| 13 | [13_架构设计优化与验收标准.md](13_架构设计优化与验收标准.md) | 先修行为保持型设计缺陷（已回归 95/95），再为架构欠账立门槛 | 已验收 |
| 16 | [16_评审测试与UI改造_执行计划.md](16_评审测试与UI改造_执行计划.md) | 评审 → 修文档 → 按参考图重做 UI → 全量复验的四段执行计划 | 已验收 |
| 18 | [18_视频解析性能架构重构.md](18_视频解析性能架构重构.md) | 60 分钟视频冷跑 39 分钟的实测诊断与架构改动（字幕优先/并行） | 已验收 |
| 19 | [19_视频模块对标BiliNote重构_计划.md](19_视频模块对标BiliNote重构_计划.md) | 对标 BiliNote 重构视频页 + 火山方舟接入方案，待确认后动代码 | 进行中 |
| 20 | [20_笔记解析仪表盘重构_计划.md](20_笔记解析仪表盘重构_计划.md) | 笔记/解析/仪表盘 W1–W4 重构，五条主路径端到端 5/5 | 已验收 |
| 21 | [21_一站学习闭环_差距与补齐计划.md](21_一站学习闭环_差距与补齐计划.md) | 真实材料压测定位「慢在生成卡片、扫描件解析不了」两大断点 | 已验收 |
| 23 | [23_多Agent续开发执行计划_2026-11-23.md](23_多Agent续开发执行计划_2026-11-23.md) | 按波次修闭环断点 + 借市面布局骨架，Wave 1 已由 24 号验收 | 已验收 |
| 30 | [30_补充执行plan_2026-11-23.md](30_补充执行plan_2026-11-23.md) | 竞品对齐 + 收尾 24 项的执行拆分，已由 31 号执行完毕 | 已验收 |

### ④ 竞品与专题（9 份）

| 编号 | 文件名 | 一句话说明 | 状态 |
|---|---|---|---|
| 22 | [22_市面学习闭环布局对标规范.md](22_市面学习闭环布局对标规范.md) | 7 个学习产品的逐页布局映射与验收清单（只借布局不抄皮肤） | 仅调研 |
| 26 | [26_背诵类竞品功能深挖.md](26_背诵类竞品功能深挖.md) | Anki/Quizlet/墨墨等背诵复习维度的机制深挖与可借鉴项 | 仅调研 |
| 27 | [27_笔记类竞品功能深挖.md](27_笔记类竞品功能深挖.md) | Obsidian/Notion/RemNote 等笔记与知识管理维度深挖 | 仅调研 |
| 28 | [28_PDF扫描解析质量速度诊断.md](28_PDF扫描解析质量速度诊断.md) | 扫描件「质量×速度」单页对照实验，定位瓶颈为模型排队（已用于 31） | 仅调研 |
| 29 | [29_布局UX与功能差距本地评审.md](29_布局UX与功能差距本地评审.md) | 纯本地代码层扫描：后端已就绪但前端零接线的差距清单 | 仅调研 |
| 34 | [34_刷题类竞品对标.md](34_刷题类竞品对标.md) | 粉笔/猿题库/考研帮等刷题类功能与三类页面骨架对比 | 仅调研 |
| 35 | [35_视频解析类竞品对标.md](35_视频解析类竞品对标.md) | 通义听悟/飞书妙记/BibiGPT 等视频转笔记能力与布局对比 | 仅调研 |
| 36 | [36_单词与AI笔记补充调研.md](36_单词与AI笔记补充调研.md) | 不背单词/欧路/Kimi/ima 补充，含闭环 10 条边连通性实测 | 仅调研 |
| 37 | [37_五大核心功能竞品对标与产品差距评审.md](37_五大核心功能竞品对标与产品差距评审.md) | **本轮竞品总结论**：五段齐全但 5 条边断裂 + RICE 缺口排序 + 6 项产品不足 | 待决策 |

### 附：`mockups/`

| 文件 | 说明 |
|---|---|
| `mockups/dashboard-v2.html` | 08 号的 Dashboard 提案稿（浏览器直接打开） |
| `mockups/dashboard-v3.html` | 后续 v3 布局定稿 |
| `mockups/00_对标对照板.html` | 竞品布局对照板 |
| `mockups/refs/` | 参考图资源目录 |

---

## 三、最近一次验收结论摘要（2026-11-23 · 31 号）

| 门禁 | 目标 | 实测 | 判定 |
|---|---|---|---|
| 前端构建 | 通过 | `✓ built in 1m 18s` | 通过 |
| 接口回归 | 95/95 | **95/95**，退出码 0 | 通过 |
| 端到端主路径 | 5/5 | **5/5**（解析 0.5s / 卡片 13.5s / 刷题 10.0s） | 通过 |
| UX 交互验收 | 全通过 | **17/17**（`ux_probe.py`） | 通过 |
| 三档视口 | 无横向滚动、无控制台错误 | 10 页 × 1440 + 4 页 × 430，`errors: []` | 通过 |
| 扫描件速度 | ≤75s（均值） | **66.72s**（65.80 / 67.63 两次均值） | 通过 |
| 扫描件质量 | 13/13 页、公式不丢 | 13/13 页，公式标记 884–895，可疑页 0 | 通过 |

**一句话结论**：学习闭环主链路（上传 → 解析 → 笔记 → 卡片 → 刷题 → 复习）已全绿；OCR 从 96.14s 提速到 66.72s（−30.6%）。
**仍未闭合**：真上线（10 号：域名/服务器/备案、S4 Key 轮换）、视频对标重构（19 号待确认）、依赖入库与 CI 门禁（见附录 A）。

---

## 附录 A：评测集（evals）纳管方案

> 结论先行：`gflc/backend/evals/` 目前 **41 个文件全部未入库，且没有任何一条 .gitignore 规则忽略它们**——纯粹是「从没 `git add` 过」。
> 这直接导致 CI 的 `eval-gate` job 在全新 checkout 下必然失败。本附录只给方案，**未执行任何 git add / commit**。

### A.1 证据：`git check-ignore -v` 逐个核验（工作区根目录执行）

```
$ git check-ignore -v gflc/backend/evals/offline_eval.py
（无输出，退出码 1 = 未被忽略）

gflc/backend/evals/offline_eval.py              => 无输出，exit 1（未忽略）
gflc/backend/evals/build_corpus.py              => 无输出，exit 1（未忽略）
gflc/backend/evals/questions.json               => 无输出，exit 1（未忽略）
gflc/backend/evals/VERSION                      => 无输出，exit 1（未忽略）
gflc/backend/evals/__init__.py                  => 无输出，exit 1（未忽略）
gflc/backend/evals/corpus/note-01.json          => 无输出，exit 1（未忽略）
gflc/backend/evals/reports/v1.0/report.json     => 无输出，exit 1（未忽略）
gflc/backend/evals/reports/v1.1probe/report.json=> 无输出，exit 1（未忽略）
```

递归复核：整个目录被忽略的文件数为 **0**。

```
$ git ls-files --others --ignored --exclude-standard gflc/backend/evals | wc -l
0
$ git ls-files --others --exclude-standard gflc/backend/evals | wc -l
41
```

规则侧复核：根 `.gitignore` 与 `gflc/.gitignore` 均无 `evals` 相关条目；`*.json`、`reports/`、`logs/` 等模式都不匹配该路径（`gflc/backend/logs/` 的规则只作用于 `logs/` 目录名）。

### A.2 为什么 `git ls-files gflc/backend/evals` 为 0

```
$ git ls-files gflc/backend/evals | wc -l
0
$ git status --porcelain -uall gflc/backend/evals | head -3
?? gflc/backend/evals/VERSION
?? gflc/backend/evals/__init__.py
?? gflc/backend/evals/build_corpus.py
```

`??` 前缀表明这些文件是**未跟踪（untracked）**，而不是被 ignore（被忽略的文件根本不会出现在 `git status` 里）。
因此原因只有一个：**目录从未被 `git add`，且没有任何提交包含过它**。

### A.3 三条结论

#### 结论 ①：`.gitignore` 不需要新增任何行

- `evals/` 下 41 个文件 0 命中忽略规则，说明现有规则**没有误伤**，无需「解锁」。
- 也**不建议**把 `evals/` 整体加白名单——`.gitignore` 里没有任何相关规则，加了是冗余。
- 唯一可选的可选优化（**不强制**）：如果不想让本地跑出的临时报告污染仓库，可在 `gflc/.gitignore` 追加精确两行：

  ```gitignore
  backend/evals/reports/ci-base/
  backend/evals/reports/ci-head/
  ```

  理由：CI 的 `eval-gate` 自建这两份基线/当前报告，属于每次运行的可再生产物；而 `reports/v1.0/`、`reports/v1.1probe/` 是**历史验收证据，应当入库**。
  → 若不采纳此可选项，则 `.gitignore` **保持零改动**，历史报告与临时报告一并入库也无功能危害。

#### 结论 ②：需要 `git add` 的路径清单

核心集（**37 个**，CI 门禁必需）：

```bash
git add gflc/backend/evals/VERSION
git add gflc/backend/evals/__init__.py
git add gflc/backend/evals/offline_eval.py
git add gflc/backend/evals/build_corpus.py
git add gflc/backend/evals/questions.json
git add gflc/backend/evals/corpus/          # 32 份资料（note-01..08 / pdf-01..10 / qbank-01..06 / video-01..08）
```

证据归档集（**4 个**，建议一并入库，作为六项指标的历史基线）：

```bash
git add gflc/backend/evals/reports/v1.0/report.json
git add gflc/backend/evals/reports/v1.0/report.md
git add gflc/backend/evals/reports/v1.1probe/report.json
git add gflc/backend/evals/reports/v1.1probe/report.md
```

合计 **41 个**，与 `git status` 的 `??` 条目数一致。

**额外必须补的两类（本附录最重要发现）**：

```bash
# 1) eval_gate.py 完全未入库 —— CI eval-gate 第三/四步直接找不到文件
git add gflc/backend/scripts/eval_gate.py

# 2) quality_eval.py 有 53 行未提交改动 —— 已入库的是旧版，不支持 --offline
git add gflc/backend/scripts/quality_eval.py
```

- `quality_eval.py` 已跟踪但处于 `M`（modified）状态：HEAD 版本仍是「在线 8 题打分」实现，**没有 `--offline` 参数**，且顶部 `import httpx` 为硬依赖。
- 31 号 / 24 号验收引用的 `ux_probe.py`（17/17）、`e2e_paths.py`（5/5）同样未入库；若希望 CI 复现这些结论，需一并 `git add`：

  ```bash
  git add gflc/backend/scripts/ux_probe.py
  git add gflc/backend/scripts/e2e_paths.py
  ```

  （非 eval-gate 必需，属「结论可复现性」范畴。）

#### 结论 ③：CI `eval-gate` 在全新 checkout 下会缺什么

| 缺失项 | 后果 | 触发位置 |
|---|---|---|
| `scripts/eval_gate.py` 未入库 | `python: can't open file 'scripts/eval_gate.py'`，job 直接失败 | 第 4 步 `eval_gate` 回归门禁 |
| `scripts/quality_eval.py` 的未提交改动 | 用的是旧版：`error: unrecognized arguments: --offline`；且旧版顶层 `import httpx` 与离线零依赖设计冲突 | 第 3 步 `quality_eval 生成当前报告` |
| `evals/__init__.py` + `evals/offline_eval.py` | `ModuleNotFoundError: No module named 'evals'` | `quality_eval.py:180` 的 `from evals.offline_eval import evaluate, write_report` |
| `evals/questions.json` + `evals/corpus/*.json`（32） | 评测样本缺失，六项指标无法计算 | `offline_eval.evaluate()` |
| `evals/VERSION` | `quality_eval.py:172` 读版本号失败（`--version auto` 的默认路径） | 第 3 步 |
| `evals/reports/` | **不缺**：CI 自己 `mkdir -p evals/reports/ci-base` 并写入冻结基线，再用 `--version ci-head` 生成新报告 | 第 2 步 |

**结论**：即便只修 `.gitignore`，`eval-gate` 也跑不起来——真实阻塞是「41 个 evals 文件 + `eval_gate.py` + `quality_eval.py` 改动」三者同时未入库。修复顺序建议：
`evals/` 核心 37 个 → `eval_gate.py` → `quality_eval.py` 改动 →（可选）历史报告 4 个 →（可选）`ux_probe.py` / `e2e_paths.py`。

---

## 附录 B：本 README 的验收自检

| 检查项 | 方法 | 结果 |
|---|---|---|
| 文档覆盖无遗漏 | `ls -1 *.md` 计数 32（不含本 README）；索引表 7+8+12+5 分组，合计 **32** | 一致 |
| 编号连续性 | 按文件名前缀取号 → 00…31，连续无缺号 | 一致 |
| 表格列数 | 9 个表块逐行校验竖线数：8 块内部完全一致；附录 B 表已改写规避单元格内管道符 | 一致 |
| 标题层级 | 全文仅第 1 行为 H1，章节统一 `##`、子节 `###`，无跳级（代码块内 `#` 注释不计） | 一致 |
| evals 证据 | 8 个关键路径 `git check-ignore -v` 全部 exit 1；递归忽略数 0；未跟踪数 41 | 已复核 |
| 未执行写操作 | 全程未 `git add` / `commit`，未改 `.gitignore`，未改任何代码 | 遵守 |

> 唯一「差异说明」：任务书中把文档计为 31 份且分组只列 28 份（缺 06/08/11/24）。实测为 **32 份**，本索引已按实际文件补齐：`06`/`11` → 类③，`08` → 类③，`24` → 类②。
