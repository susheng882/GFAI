# -*- coding: utf-8 -*-
"""商业计划书式 A4 学术图表册：封面 + 双页目录 + 10 章扉页 + 40 图页 + 封底。
结构：卷首品牌 → ① 执行摘要 → ② 市场与机会 → ③ 产品与解决方案 → ④ 系统架构与核心流程
      → ⑤ 模型选型与 AI 治理 → ⑥ 工程落地与质量保障 → ⑦ 商业模式与财务
      → ⑧ 团队与资源 → ⑨ 项目进度与风险控制
输出 PDF 与统一 1588×2246 页图，页边距全册一致。
"""
import re
import html
from pathlib import Path
from playwright.sync_api import sync_playwright
import _gf_brand as B

SRC = Path(r"F:\GrowthForward_AI学习伴侣\毕设材料\学术图表\src")
OUT = Path(r"F:\GrowthForward_AI学习伴侣\毕设材料\学术图表\统一版式")
OUT.mkdir(parents=True, exist_ok=True)

C0 = "卷首 · 品牌篇"
C1 = "第一章 执行摘要"
C2 = "第二章 市场与机会"
C3 = "第三章 产品与解决方案"
C4 = "第四章 系统架构与核心流程"
C5 = "第五章 模型选型与 AI 治理"
C6 = "第六章 工程落地与质量保障"
C7 = "第七章 商业模式与财务可行性"
C8 = "第八章 团队与资源"
C9 = "第九章 项目进度与风险控制"


def P(no, f, name, chap, src, *pts):
    return dict(no=no, f=f, name=name, chap=chap, src=src, pts=list(pts))


F = [
    # 卷首 · 品牌
    P("图 0-1", "图0-1_品牌形象与设计理念.svg", "品牌形象与设计理念", C0, "品牌设计规范",
      "几何 G 形开口圆环＝可延展的学习闭环，火花橙箭头冲出开口＝持续向前，前进蓝结构＝可验证。",
      "六色主题系统（石墨 / 前进蓝 / 冰蓝 / 云雾 / 银线 / 火花橙）与字体、图标规范统一；全册白纸底 + 细银线圆角卡，封面封底同为白底。"),
    # ① 执行摘要
    P("图 1-1", "图1-1_执行摘要与项目全貌一页通览.svg", "执行摘要与项目全貌一页通览", C1, "全册总览",
      "七问七答覆盖痛点、方案、差异化、市场、成本、落地、排期与团队，全部给关键数字与出处。",
      "项目亮点三条：学术可验证、工程可运行、经济可持续；后续九章逐层展开。"),
    # ② 市场与机会
    P("图 2-1", "图2-1_目标人群画像与使用场景.svg", "目标人群画像与使用场景", C2, "产品报告第二章 · 设计假设",
      "三类人群（考研自学 / 高校课程 / 职业认证）均以视频与讲义为主、有明确考核目标。",
      "五阶段用户旅程与获客留存假设；画像为设计假设，内测 20 人样本待验证。"),
    P("图 2-2", "图2-2_市场痛点与需求缺口.svg", "市场痛点与需求缺口", C2, "产品报告第二章 · 技术方案 1.4",
      "六大痛点逐条给出「现有方案为何失效」与 GFLC 对策，痛点编号 ①–⑥ 在功能域图中复用。",
      "结论：上半场已拥挤、下半场只做一半，空白在「解析→溯源→调度→回炉」同一条数据链。"),
    P("图 2-3", "图2-3_市场规模测算TAM-SAM-SOM.svg", "市场规模测算与口径对照", C2, "CNNIC / 教育部 / 多鲸 / 艾瑞 / 中国教育在线",
      "并列四种公开口径（850 亿 / 4800 亿 / 6820 亿 / 9750 亿），取窄口径保守测算。",
      "TAM 3.27 亿用户、SAM 备考自学细分、SOM 500 付费用户；渗透率与用户数为显式规划假设。"),
    P("图 2-4", "图2-4_已上线产品实证对比与差异化定位矩阵.svg", "已上线产品实证对比与差异化定位矩阵", C2, "技术方案 1.4",
      "11 款真实上线产品 × 核心能力矩阵，含 2026-11-14 官网实采定价与上线状态。",
      "GFLC 差异化不是功能数量，而是可验证的数据链；所有竞品至少缺 2 项能力。"),
    P("图 2-5", "图2-5_已上线竞品定价对照与能力覆盖分析.svg", "已上线竞品定价对照与能力覆盖分析", C2, "技术方案 1.4 / 5.8",
      "公开定价统一折算为元/月，工具层集中在 $0–20/月；配 6×5 能力覆盖热图。",
      "价格口径、新客与学生优惠、续费差异均在注释标注，可逐条追溯。"),
    P("图 2-6", "图2-6_差异化定位与竞争壁垒.svg", "差异化定位与竞争壁垒", C2, "技术方案 1.4 · 产品报告第二章",
      "价格 × 能力完整度散点 + SWOT 四象限 + 四层护城河（数据链 / 理论 / 工程 / 成本）。",
      "L1 数据链最难复制；L4 成本优势易被跟随，答辩陈述以 L1–L3 为主。"),
    # ③ 产品与解决方案
    P("图 3-1", "图3-1_价值主张与产品全貌.svg", "价值主张与产品全貌", C3, "产品报告第一、四章",
      "价值主张画布四要素 + 四层能力地图 + 三条不可让步原则（可溯源 / 可调度 / 可负担）。",
      "痛点编号、四条主路径与 G1–G7 门禁口径贯穿后续所有功能域图。"),
    P("图 3-2", "图3-2_功能全景流程图.svg", "功能全景流程图（38 项功能 × 五阶段泳道）", C3, "产品报告第四章（八）",
      "F01–F38 共 38 个功能节点逐项落位五条泳道，编号与功能清单一一对应。",
      "框型区分版本：主线 27 / V1.5 8 / 规划池 3；K1–K3 与错题回炉朱红闭环回授。"),
    P("图 3-3", "图3-3_功能模块设计理论依据矩阵.svg", "功能模块的设计理论依据矩阵", C3, "技术方案 3.9 · 产品报告第四章",
      "10 组功能按「设计理论 → 经典文献与关键数据 → 落地参数」映射，配矢量图标。",
      "覆盖遗忘曲线 / 测试效应 / BKT / 认知负荷 / 双重编码 / 工作记忆 / 合意困难 / 元认知。"),
    P("图 3-4", "图3-4_功能域一_素材接入与多源解析.svg", "功能域一：素材接入与多源解析", C3, "产品报告第四章（八）F01–F06",
      "6 项功能逐项给说明与落点；统一入口 + 预签名直传，1 GB 文件不占 API 内存。",
      "理论：认知负荷、工作记忆 4±1、经济性原则；验收为三条解析链路各 10 个真实样本。"),
    P("图 3-5", "图3-5_功能域二_内容解析与知识生成.svg", "功能域二：内容解析与知识生成", C3, "产品报告第四章（八）F07–F16",
      "10 项功能覆盖取材降本、转写、切片、三档路由、契约校验、断点续传与溯源硬字段。",
      "取材链决定数量级、路由决定单价、契约与断点决定返工率；模型与治理细节后置至第四、五章。"),
    P("图 3-6", "图3-6_功能域三_知识产物与多格式导出.svg", "功能域三：知识产物与多格式导出", C3, "产品报告第四章（八）F17–F23",
      "7 项产物共享 knowledge_units 主键，不重复调用模型；含版本快照与多格式导出。",
      "理论：测试效应（80% vs 34%）、双重编码、合意困难；支撑 G3 数据可携带与 G4 可回滚。"),
    P("图 3-7", "图3-7_功能域四_学习闭环与间隔复习.svg", "功能域四：学习闭环与间隔复习", C3, "产品报告第四章（八）F24–F29",
      "6 项主线功能构成计划 → 排程 → 今日任务 → 测验 → 掌握度 → 回炉的可演示闭环。",
      "R1–R4 = 1/3/7/14 天由 Cepeda 2006 元分析确定，R*=0.90、θ=0.85 为可配置常量。"),
    P("图 3-8", "图3-8_功能域五_检索问答与可视化仪表盘.svg", "功能域五：检索问答与可视化仪表盘", C3, "产品报告第四章（八）F30–F33",
      "带来源问答、历史任务、NL 问数（P2）、成长记录；答案必带时间戳可跳原文。",
      "白名单模板 + 图表契约双保险：模型只填参数，越权 / 空集 / 契约失败统一降级提示。"),
    P("图 3-9", "图3-9_功能域六_账号体系与平台治理.svg", "功能域六：账号体系与平台治理", C3, "产品报告第四章（八）F34–F38",
      "HttpOnly Cookie + Argon2id、配额护栏、全量数据导出、供应商管理与外链图片本域代理。",
      "治理阈值与第 5 章 AI 治理、第 7 章成本细目共用同一组配置常量。"),
    P("图 3-10", "图3-10_学习闭环与遗忘曲线调度机制.svg", "学习闭环与遗忘曲线调度机制（公式级理论）", C3, "技术方案 3.9 · 产品报告第七章（三）",
      "Ebbinghaus R(t)=e^(−t/S) → SM-2 的 EF 与 I(n) 递推 → FSRS-6，三代模型公式全链。",
      "曲线簇画出 R1–R4 复习抬升、目标保持率 R* 与回炉阈值 θ，附参数表与 6 条经典文献。"),
    # ④ 系统架构与核心流程
    P("图 4-1", "图4-1_系统技术架构图.svg", "系统技术架构图（七层 · 架构评审修订版）", C4, "技术方案 2 / 5",
      "七层编号式分层：接入 → 网关 → 应用 → 异步 Worker → AI 管线 → 持久 → 基础设施。",
      "K1–K3 关键链路编号直接嵌在对应模块中，◆ 标记架构评审新增项，可跨图引用。"),
    P("图 4-2", "图4-2_数据模型与知识产物关系图.svg", "数据模型与知识产物关系图（ER）", C4, "技术方案 2.1 / 2.5 / 2.7",
      "九类实体与 1:N 关系；pgvector 与业务表同库，JOIN 即可溯源，时间戳为 P0 硬字段。",
      "PG 存业务与产物、Redis 只存小状态、MinIO 存对象、tmp 存中间产物，职责边界明确。"),
    P("图 4-3", "图4-3_长任务异步执行链路流程图.svg", "长任务异步执行链路流程图拆解", C4, "技术方案 2.5",
      "四泳道 13 个标准流程符号 + 四条阶段带 + 7 行参数矩阵，拆解提交到产物落库全过程。",
      "API 不跑 CPU 密集管线；BRPOPLPUSH + 心跳回收 + 60 min 硬超时 + 死信队列。"),
    P("图 4-4", "图4-4_大文件预签名直传协议流程图.svg", "大文件预签名直传协议流程图拆解", C4, "技术方案 2.6 / 5.6 / 5.7",
      "三步协议 + 12 个流程符号 + 7 行安全边界矩阵；字节流不进 API 进程。",
      "评审动机：1 GB 视频流经 API，两个并发上传即可打爆 4 GB 内存；失败分支完整。"),
    P("图 4-5", "图4-5_AI内容处理管线与三档模型路由.svg", "AI 内容处理管线与三档模型路由", C4, "技术方案 3.1 / 3.2",
      "五级管线 + 三档路由实价矩阵 + 三级取材降本链 + 双索引 RAG + 输出契约表。",
      "按体积预算二分切块、JSON Schema 契约、Chroma 双索引、RAG 限 50 段。"),
    P("图 4-6", "图4-6_NL问数仪表盘五步链路流程图.svg", "NL 问数仪表盘五步链路流程图拆解", C4, "技术方案 3.8（P2）",
      "四泳道 10 个流程符号 + Step 1–5 阶段带 + 双保险约束表，异常汇流为朱红总线。",
      "数据查询由后端白名单生成、模型只填参数；图表配置走输出契约校验。"),
    # ⑤ 模型选型与 AI 治理
    P("图 5-1", "图5-1_三档模型选型决策矩阵与真实单价.svg", "三档模型选型决策矩阵与真实单价", C5, "技术方案 5.8 · 2026-11-14 实采",
      "六款候选模型公开单价与能力对照；轻 / 中 / 强三档按任务难度路由，强档单独配额。",
      "★ 百炼 Token Plan Lite ¥39/月起，池内 150+ 模型共享额度；两项商用/抵扣待核对。"),
    P("图 5-2", "图5-2_AI调用成本护栏与四级降级流程图.svg", "AI 调用成本护栏与四级降级流程图", C5, "技术方案 3.3 / 3.4",
      "护栏判定链 + 四级降级阶梯 + 三重护栏阈值表 + 降级演练验收清单。",
      "触发上限自动降档而非失败：用户感知「慢一点」，不是「用不了」。"),
    P("图 5-3", "图5-3_AI调用优化策略与成本节省机理.svg", "AI 调用优化策略与成本节省机理", C5, "技术方案 3.1 / 3.4",
      "六维优化：取材降本、体积预算分块、三档路由、Prompt 缓存、断点续传、契约校验。",
      "字幕优先取材链降一个量级；缓存命中零模型成本；断点续传不重复计费。"),
    P("图 5-4", "图5-4_AI治理与风险管控总纲.svg", "AI 治理与风险管控总纲", C5, "技术方案 3.3 / 5.7",
      "成本 / 质量 / 安全 / 可观测四域控制矩阵，逐项给阈值、触发动作与留痕证据。",
      "事前配额契约 → 事中路由降级 → 事后评测审计 → 人工兜底，形成治理闭环。"),
    # ⑥ 工程落地与质量保障
    P("图 6-1", "图6-1_服务器选型与六服务矩阵部署架构.svg", "服务器选型与六服务矩阵部署架构", C6, "技术方案 2.3 / 5.3 / 5.8",
      "六款候选服务器全宽实证对比：★ 腾讯云轻量 2C4G5M ¥188/年 ≈¥15.7/月。",
      "3×2 六服务卡片 + 6×6 依赖矩阵 + K1–K3 关键路径 + 贯穿运维面，无流程箭头。"),
    P("图 6-2", "图6-2_测试体系分层与G1-G7上线门禁.svg", "测试体系分层与 G1–G7 上线门禁", C6, "技术方案 4.1–4.4",
      "测试金字塔五层 + 四指标闸门 + G1–G7 七域判定表 + Go/No-Go 流程 + 回滚机制。",
      "任一指标较上版下降 >3 pp 触发回滚；发布前 48 小时逐域核验。"),
    P("图 6-3", "图6-3_上线运维治理与可观测性.svg", "上线运维治理与可观测性", C6, "技术方案 5.7",
      "磁盘 / 备份 / 证书 / 迁移 / 观测 / 回滚六域治理矩阵 + SLO 与门禁映射。",
      "水位 80% 冻结、certbot 自动续期、Alembic 版本化、轻量告警（云监控 + cron + webhook）。"),
    # ⑦ 商业模式与财务可行性
    P("图 7-1", "图7-1_盈利模式四层结构与单位经济模型.svg", "盈利模式四层结构与单位经济模型", C7, "产品报告第九章",
      "免费额度 → 个人订阅 → 团体授权 → 增值服务，逐层以前一层数据为开通条件。",
      "单用户月成本 ¥1.5–2.5 vs 客单价 ¥10–12，毛利约八成；成本表已按实价校准。"),
    P("图 7-2", "图7-2_运行成本解析与服务器云服务选型.svg", "运行成本解析与服务器云服务选型（图表版）", C7, "技术方案 5.8",
      "服务器实价对比 + 月度成本堆叠柱 + 占比条 + 用户规模敏感度折线 + LLM 单价表。",
      "20 用户内测月度合计 ≈¥82（区间 52–192）；续费由 ¥15.7 跳至 ¥65/月（×4.2）。"),
    P("图 7-3", "图7-3_采购清单与一次付费多模型方案.svg", "采购清单与一次付费多模型方案", C7, "技术方案 5.8 · 2026-11-14 实采",
      "只买三样：服务器 ¥188/年、Token Plan 订阅、域名 ¥60–80/年；SSL/备案/自建存储 ¥0。",
      "毕设 8 个月总账 ¥560–880；叠加学生 ¥300 抵扣金实付可低至 ¥260 量级。"),
    P("图 7-4", "图7-4_收入测算与盈亏平衡分析.svg", "收入测算与盈亏平衡分析", C7, "产品报告第九章 · 规划假设",
      "定价分层 + 单位经济 + 三年推演 + 盈亏平衡折线 + 保守/基准/乐观三情景。",
      "基准情景约 11 个付费用户覆盖平台固定支出；用户数为规划假设，口径显式声明。"),
    P("图 7-5", "图7-5_资金需求用途与阶段成果交付.svg", "资金需求、用途与阶段成果交付", C7, "技术方案 5.8 · 毕设简化",
      "资金需求与来源、用途分配、四阶段投放、成果交付与「退出」安排五段式。",
      "单人毕设不编造估值与股权；保留 BP 的「需求—用途—里程碑—交付」逻辑骨架。"),
    # ⑧ 团队与资源
    P("图 8-1", "图8-1_团队与资源配置.svg", "团队与资源配置", C8, "技术方案 6 · 毕设场景",
      "单人角色合一 RACI、能力矩阵与缺口补齐、云厂商 / 开源 / 学术三类外部依赖。",
      "最大风险是单点依赖与范围膨胀：文档化全部设计决策 + 可牺牲项第 11 周降级。"),
    P("图 8-2", "图8-2_能力证据与外部依赖.svg", "能力证据与外部依赖可替换性评估", C8, "技术方案 5.8 / 6 · 图 8-1 续",
      "五项能力主张绑定可核验交付物、验收口径与 BP 图号，形成答辩可逐图回溯的证据链。",
      "外部依赖逐项评估替换成本与切换触发条件；学术 / 工程 / 合规三类依据并列，诚实边界显式披露。"),
    # ⑨ 项目进度与风险控制
    P("图 9-1", "图9-1_16周工程里程碑与排期映射甘特图.svg", "16 周工程排期甘特图（WBS 14 项）", C9, "技术方案 6",
      "WBS 14 项任务条对齐 16 周刻度，P0–P6 八阶段、M1–M6 里程碑与四条门禁周虚线。",
      "单人周工时曲线峰值 W10 为 40 h、均值约 32 h；P3 溯源为可牺牲项，W11 未达标降 V1.5。"),
    P("图 9-2", "图9-2_风险矩阵与分级对策.svg", "风险矩阵与分级对策", C9, "技术方案 5.7 / 6",
      "5×5 概率 × 影响热力矩阵 + R1–R10 风险登记册 + Ⅰ/Ⅱ/Ⅲ 三级对策与责任。",
      "R7 挂 W11 门禁周、R8 挂 G1–G7、R3/R4 挂成本细目，风险与排期/门禁形成联动。"),
]

CHAPTERS = [
    dict(no="00", cn="品牌篇", en="BRAND & DESIGN RATIONALE", key=C0,
         logic="在进入商业论证之前，先建立品牌识别与设计语言。几何 G 形开口圆环与冲出开口的箭头分别对应「可延展、可验证的学习闭环」与「持续向前」；全册以白纸底为骨、石墨文字为体，前进蓝作唯一主色，火花橙仅点睛向前箭头，风险项保留砖红独立语义色。",
         pts=["品牌不是装饰，而是产品原则的可视化：可溯源、可调度、可负担三条原则在标识里先立住。",
              "视觉规范（色彩 / 字体 / 图标 / 应用）与全册 40 张插图的版式规范共用同一套参数。",
              "本册所有图页统一 A4 竖版、统一页边距与 680×960 标准画布，保证打印与答辩投影一致。"]),
    dict(no="01", cn="执行摘要", en="EXECUTIVE SUMMARY", key=C1,
         logic="用一页回答投资人/评委最关心的七个问题：为什么做、做什么、凭什么、市场多大、花多少钱、怎么落地、多久交付。后续九章都是这一页的逐层展开，任何结论都能在分图里找到证据链。",
         pts=["一句话价值主张：把「看过」变成「学会」，以溯源为底线、间隔重复为节奏、成本护栏为边界。",
              "关键数字：38 项功能、11 款竞品、¥82/月、16 周排期、¥560–880 毕设总账。",
              "三条亮点：学术可验证（公式级理论）、工程可运行（六容器 + 门禁）、经济可持续（实价报价单）。"]),
    dict(no="02", cn="市场与机会", en="MARKET & OPPORTUNITY", key=C2,
         logic="先证明需求真实存在：从人群画像到六大痛点，再到市场规模与已上线竞品实证。本章刻意并列四种互相矛盾的公开口径，并显式标注哪些是数据、哪些是假设——这比取一个漂亮数字更经得起追问。",
         pts=["Why：11 款真实上线产品证明上半场（转写/摘要）已被验证，下半场（调度/回炉）仍空白。",
              "How big：TAM 锚定 CNNIC 3.27 亿在线教育用户；2027 研考官方人数未公布，机构测算 315–335 万仅作参考区间。",
              "Why us：差异化落在「同一条可验证数据链」，护城河以 L1 数据模型最难复制。"]),
    dict(no="03", cn="产品与解决方案", en="PRODUCT & SOLUTION", key=C3,
         logic="回答「所以你做了什么」。先用价值主张画布与能力地图给出产品全貌，再用 38 项功能全景流程图与理论依据矩阵建立总账，最后按六大功能域逐域展开：功能清单 → 核心流程 → 解决什么痛点 → 如何优化 → 具体理论 → 验收口径。本章刻意只讲功能与用户价值；模型选型、调用优化与 AI 治理统一后置到第四、五章，让「做什么」先于「用什么模型」被看见。",
         pts=["What：38 项功能按 6 域组织（主线 27 / V1.5 8 / 规划池 3），编号 F01–F38 全册一致。",
              "Why it works：每个功能域都锚定学习科学理论（Ebbinghaus / SM-2 / BKT / 测试效应 / 认知负荷等）。",
              "How to verify：理论参数写成可配置常量并落库，验收口径接入 G1–G7 门禁。"]),
    dict(no="04", cn="系统架构与核心流程", en="SYSTEM ARCHITECTURE & FLOWS", key=C4,
         logic="从「做什么」进入「怎么算」。七层架构给出全局骨架，ER 图给出数据契约，四条泳道流程图把最关键、最容易出事故的链路逐一拆到可实现的步骤：长任务、大文件直传、AI 管线、自然语言问数。",
         pts=["How-1：API 与 Worker 分进程、预签名直传、checkpoint 续跑，均来自架构评审的缺口补齐。",
              "每张流程图配阶段带、参数矩阵与设计依据卡，异常分支以朱红标出。",
              "K1 直传 / K2 入队 / K3 任务态反馈跨图编号一致，答辩可跨图引用。"]),
    dict(no="05", cn="模型选型与 AI 治理", en="MODEL SELECTION & AI GOVERNANCE", key=C5,
         logic="本章回答三件事：选哪个模型、为什么便宜、怎么管住。选型用 2026-11-14 官网实采单价，优化讲少花钱的六种机理，治理讲花超了/出错了/越权了分别由谁兜底——三者合起来才使 ¥82/月成立。",
         pts=["选谁：轻档 qwen-flash / 中档 qwen-plus / 强档 qwen-max，强档单独配额并限流。",
              "怎么省：字幕优先取材链 + 体积预算分块 + 缓存 + 断点续传，单位成本降一个量级。",
              "怎么管：成本 / 质量 / 安全 / 可观测四域控制矩阵，阈值—动作—留痕三列对齐。"]),
    dict(no="06", cn="工程落地与质量保障", en="ENGINEERING & QUALITY ASSURANCE", key=C6,
         logic="把设计变成能长期跑起来的系统：服务器选型与六容器矩阵回答「跑在哪」，测试金字塔与 G1–G7 门禁回答「怎么验」，运维治理与可观测性回答「上线后怎么活」。三张图构成一条完整的工程化证据链。",
         pts=["跑在哪：2C4G 单机、境内节点（G7 备案）、无 GPU、六容器、API/Worker 分进程。",
              "怎么验：字段完整率 / 知识点召回率 / 幻觉率 / 人工可用率四指标，下降 >3 pp 回滚。",
              "怎么活：磁盘水位 80% 冻结、certbot 自动续期、Alembic 迁移、轻量告警闭环。"]),
    dict(no="07", cn="商业模式与财务可行性", en="BUSINESS MODEL & FINANCIAL FEASIBILITY", key=C7,
         logic="把钱一次讲透：盈利模式（收入侧）、运行成本与采购清单（支出侧）、收入测算与盈亏平衡（单位经济）、资金需求与阶段交付（资金结构）。所有支出数字来自真实报价，所有收入数字显式标注为规划假设。",
         pts=["How much：内测月支出 ≈¥82（区间 52–192），硬上限 ¥250；只买服务器、订阅、域名三样。",
              "Unit economics：客单 ¥10–12、单用户成本 ¥1.5–2.5、约 11 个付费用户盈亏平衡。",
              "可信度：报价采集日期与来源全部标注；续费跳涨 ×4.2 与学生抵扣金并列披露。"]),
    dict(no="08", cn="团队与资源", en="TEAM & RESOURCES", key=C8,
         logic="融资 BP 必答「谁来做」与「凭什么相信能交付」。本项目为单人毕设，不虚构团队：前图拆解角色合一的职责、能力矩阵与缺口补齐；后图把能力主张绑定到可核验交付物、验收口径与全册图号，并给出外部依赖的替换成本与切换条件，形成答辩可回溯的证据链。",
         pts=["Who：产品 20% / 后端与 AI 40% / 前端 20% / 运维测试 12% / 文档答辩 8%（16 周估计）。",
              "Evidence：五项能力主张绑定交付物、验收口径与图号；外部依赖逐项给出替换成本与切换阈值。",
              "诚实边界：无一手调研、无模型微调、无高并发经验；不虚构团队，全部决策文档化并保留供应商切换能力。"]),
    dict(no="09", cn="项目进度与风险控制", en="SCHEDULE & RISK CONTROL", key=C9,
         logic="最后回答「什么时候交付、出问题怎么办」。16 周甘特图把 WBS 14 项任务、里程碑、门禁周与单人周工时放在同一时间轴上；风险矩阵把 R1–R10 逐条绑定到排期、门禁与成本证据，形成可执行的处置闭环。",
         pts=["When：P0–P6 八阶段、M1–M6 里程碑、四条门禁周；峰值 W10 为 40 h/周。",
              "What if：R1–R10 按概率 × 影响分三级，高危项前置演练、中危项设阈值告警。",
              "范围护栏：可牺牲项第 11 周未达标即降 V1.5，避免范围膨胀拖垮主线交付。"]),
]

# 章扉页数据：q 本章回答的 BP 问题 / kpi 关键数据 / extra 图数少时的延展卡。
# 数值全部沿用正文与已交付图页口径，不新编数据。
CH_META = {
    "00": dict(q="我们是谁，用什么设计语言说话",
        kpi=[("680×960", "标准画布"), ("A4", "统一幅面"), ("10 章", "BP 结构"), ("40 图", "全册插图")],
        extra=[("品牌语义与人格", ["Growth＝知识沉淀与能力增长，Forward＝按节奏持续向前",
                             "口号：Learn. Grow. Keep Moving Forward.",
                             "人格：安静、可信赖、不催不吵的学习伙伴"]),
               ("在全册中的作用", ["先立住可溯源 / 可调度 / 可负担三条产品原则",
                             "前进蓝作唯一主色，火花橙仅点睛向前箭头",
                             "全册 40 张插图共用同一套版式与页边距参数"]),
               ("与后续章的呼应", ["第三章把三条原则落成 38 项功能与 6 个功能域",
                             "第五章用成本护栏兑现「可负担」",
                             "第六章用门禁与可观测性兑现「可验证」",
                             "第七章以实价采购与盈亏平衡复核「可负担」",
                             "第九章用 R1–R10 风险矩阵兜住交付不确定性"])]),
    "01": dict(q="一页回答投资人 / 评委的七个问题",
        kpi=[("38 项", "功能总账"), ("11 款", "竞品实证"), ("¥82", "内测月支出"), ("16 周", "交付周期")],
        extra=[("七问对应章节", ["Why / How big → 第二章 市场与机会",
                             "What / Why it works → 第三章 产品与理论",
                             "How → 第四～六章 架构 / AI / 工程",
                             "How much / When → 第七、九章 财务 / 进度"]),
               ("数字口径声明", ["支出与采购为 2026-11-14 官网实采",
                             "收入与用户数显式标注为规划假设",
                             "市场规模并列四种公开口径，不做单一取值"]),
               ("证据回溯方式", ["每个结论标注出处章节或图号",
                             "后续九章均为本页的逐层展开",
                             "答辩可沿图号从结论回溯到原始依据"])]),
    "02": dict(q="需求是否真实，凭什么轮到我们",
        kpi=[("3.27 亿", "在线教育用户"), ("315–335 万", "2027 研考测算"), ("11 款", "已上线竞品"), ("4 种", "市场口径并列")],
        extra=[]),
    "03": dict(q="做了什么，每个功能凭什么这么设计",
        kpi=[("38 项", "F01–F38"), ("6 域", "功能域"), ("27 / 8", "主线 / V1.5"), ("10 组", "理论映射")],
        extra=[]),
    "04": dict(q="怎么算，关键链路如何不失控",
        kpi=[("7 层", "系统架构"), ("4 条", "关键链路"), ("6 容器", "常驻服务"), ("K1–K3", "跨图链路编号")],
        extra=[]),
    "05": dict(q="选哪个模型，怎么省，怎么管住",
        kpi=[("3 档", "模型路由"), ("4 域", "AI 治理"), ("¥250", "月支出硬上限"), ("字幕优先", "取材链")],
        extra=[]),
    "06": dict(q="跑在哪，怎么验，上线后怎么活",
        kpi=[("2C4G", "单机部署"), ("G1–G7", "上线门禁"), ("40 份", "评测集"), ("80%", "磁盘冻结水位")],
        extra=[("工程化证据链", ["跑在哪：境内节点 2C4G 单机、无 GPU、六容器",
                             "怎么验：字段完整率 / 知识点召回率 / 幻觉率 / 人工可用率",
                             "怎么活：磁盘水位 80% 冻结、certbot 续期、Alembic 迁移",
                             "指标下降 > 3 pp 即回滚，发布前 48h Go/No-Go"])]),
    "07": dict(q="钱从哪来，花在哪，何时打平",
        kpi=[("¥82", "内测月支出"), ("¥560–880", "毕设总账"), ("¥10–12", "客单价"), ("≈11 人", "盈亏平衡")],
        extra=[("可信度约定", ["只买服务器、订阅、域名三样，一次付费覆盖多模型",
                             "报价采集日期与来源全部标注在采购清单",
                             "续费跳涨 ×4.2 与学生抵扣金并列披露，不隐藏"])]),
    "08": dict(q="谁来做，凭什么相信能交付",
        kpi=[("5 类", "角色合一"), ("40%", "后端与 AI"), ("3 类", "外部依赖"), ("20 人", "内测规划")],
        extra=[("证据链构成", ["5 项能力主张绑定可核验交付物与验收口径",
                             "逐项标注全册 BP 图号，答辩可逐图回溯",
                             "外部依赖给出替换成本与切换触发条件"]),
               ("诚实边界", ["无一手用户调研、无模型微调、无高并发经验",
                             "三项缺口均给出补齐或规避方式",
                             "不虚构团队规模，不以外包填充履历"])]),
    "09": dict(q="何时交付，出问题怎么办",
        kpi=[("16 周", "总周期"), ("14 项", "WBS 任务"), ("M1–M6", "里程碑"), ("R1–R10", "风险登记")],
        extra=[("门禁与降级机制", ["四条门禁周虚线对齐 W11 关键判定",
                             "可牺牲项 P3 溯源第 11 周未达标即降 V1.5",
                             "峰值 W10 为 40 h/周，均值约 32 h"]),
               ("风险与排期联动", ["R7 挂 W11 门禁周，R8 挂 G1–G7 上线门禁",
                             "R3 / R4 挂运行成本细目与采购清单",
                             "高危项前置演练，中危项设阈值告警"])]),
}

# 关键数据的口径释义：把每个数字从「标签」变成可核验的一句话，避免扉页只剩空框。
KPI_NOTE = {
    "00": ["40 张图共用同一画布，无异形页", "A4 竖版；页边距 12 / 10 / 8 mm",
           "卷首品牌篇 + 九章 BP 逻辑", "1 张卷首品牌图 + 39 张分章图"],
    "01": ["F01–F38，主线 27 / V1.5 8 / 规划池 3", "11 款真实上线产品，2026-11-14 实采",
           "内测月支出，区间 ¥52–192", "P0–P6 八阶段，M1–M6 里程碑"],
    "02": ["CNNIC 第 57 次报告，截至 2025-12", "官方未公布；315–335 万为机构测算",
           "含国内外 11 款，均为已上线状态", "850 / 4800 / 6820 / 9750 亿并列不取单一值"],
    "03": ["38 项功能统一编号 F01–F38", "六大功能域各自成图 3-4～3-9",
           "主线 27 项 / V1.5 8 项", "10 组「理论 → 参数 → 验收」映射"],
    "04": ["七层骨架：接入到运维全覆盖", "长任务 / 直传 / AI 管线 / NL 问数",
           "API、Worker、Redis、MinIO、PG、Nginx", "K1 直传 / K2 入队 / K3 任务态反馈"],
    "05": ["LIGHT / MID / HEAVY + LOCAL 兜底", "成本 / 质量 / 安全 / 可观测四域",
           "GFLC_DAILY_COST_CNY 日阈值硬上限", "字幕优先取材，命中即短路降本"],
    "06": ["2C4G 境内节点，无 GPU", "四项质量指标，下降 >3 pp 即回滚",
           "40 份人工标注评测集", "达阈值即冻结上传并触发告警"],
    "07": ["2026-11-14 官网实采，含续费价", "服务器 + 订阅 + 域名三类支出",
           "客单与用户数均为规划假设", "按 ¥82 月支出与 ¥10–12 客单推算"],
    "08": ["产品 / 后端 AI / 前端 / 运维 / 文档", "单人毕设，角色合一，不虚构团队",
           "模型 / 存储 / 语音 / 云四类外部依赖", "内测规划人数，非已完成用户数"],
    "09": ["P0–P6 八阶段，单人周均约 32 h", "WBS 14 项任务逐周落位",
           "M1–M6 与四条门禁周对齐", "R1–R10 全部落位 5×5 热力矩阵"],
}

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; background:#fff; color:#212121;
  font-family:'Noto Serif SC','Source Han Serif SC','SimSun',serif; }
.page { width:210mm; height:297mm; max-height:297mm; overflow:hidden;
  padding:10mm 12mm 8mm; margin:0; background:#fff;
  display:flex; flex-direction:column; page-break-after:always; break-after:page; }
.page:last-child { page-break-after:auto; break-after:auto; }
.phead { display:flex; justify-content:space-between; align-items:baseline; gap:3mm;
  font-size:9pt; letter-spacing:.2pt; border-bottom:.5pt solid #212121; padding-bottom:1mm; }
/* 页眉强制单行：左侧书名可弹性收缩并省略，右侧章节/图号/图名始终完整不折行 */
.phead > span:first-child { flex:0 1 auto; min-width:0; white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; color:#555; }
.phead .r { flex:0 0 auto; color:#333; white-space:nowrap; }
.figbox { flex:1 1 auto; min-height:0; border:.3pt solid #CCC; padding:0.8mm;
  display:flex; align-items:center; justify-content:center; }
.figbox svg { width:100%; height:100%; display:block; }
.keypts { flex:0 0 auto; margin-top:1.2mm; border:.4pt solid #CCC; padding:1.1mm 2mm;
  font-size:8pt; line-height:1.35; color:#333; }
.keypts b { font-size:8.4pt; }
.pfoot { flex:0 0 auto; margin-top:1.2mm; border-top:.5pt solid #212121; padding-top:1mm;
  display:flex; justify-content:space-between; font-size:8.4pt; color:#333; }
.cover { justify-content:flex-start; align-items:center; text-align:center; }
.c-kicker { margin-top:24mm; font-size:9pt; letter-spacing:2pt; color:#666; }
.c-title { margin-top:10mm; font-size:29pt; font-weight:bold; line-height:1.35; }
.c-sub { margin-top:4mm; font-size:18pt; letter-spacing:4pt; }
.c-line { width:60mm; border-top:1pt solid #212121; margin:7mm auto; }
.c-meta { font-size:10pt; color:#444; line-height:1.9; }
.c-list { margin-top:8mm; width:176mm; text-align:left; font-size:8.3pt; line-height:1.75;
  border:.5pt solid #212121; padding:3.5mm 5mm; }
.c-list b { font-size:8.8pt; }
.c-list div { display:inline-block; width:48%; vertical-align:top; margin-bottom:1mm; }
.c-chain { margin-top:7mm; width:176mm; text-align:left; }
.c-chain .lb { font-size:8.2pt; letter-spacing:1.6pt; color:#666; margin-bottom:2mm; }
.c-chain .row { display:flex; gap:1.3mm; }
.c-chain .nd { flex:1; border:.4pt solid #212121; padding:2mm .8mm; text-align:center;
  font-size:7.8pt; line-height:1.45; }
.c-chain .nd b { display:block; font-size:9pt; }
.c-chain .nd:first-child { background:#212121; color:#FFFFFF; }
.c-facts { margin-top:5mm; width:176mm; display:grid; grid-template-columns:repeat(4,1fr); gap:2mm; }
.c-facts .f { border:.4pt solid #C9C9C9; padding:2.5mm 2mm; text-align:left; }
.c-facts .f .v { font-size:15pt; font-weight:bold; }
.c-facts .f .l { font-size:8pt; color:#666; margin-top:1mm; }
.c-foot { margin-top:auto; margin-bottom:5mm; font-size:8.5pt; color:#555; line-height:1.8; }
.toc h2 { text-align:center; font-size:16pt; margin:3mm 0 2mm; }
.toc .lead { text-align:center; font-size:8.8pt; color:#555; margin-bottom:4mm; }
.toc table { width:100%; border-collapse:collapse; font-size:8.6pt; }
.toc th { border-top:.6pt solid #212121; border-bottom:.6pt solid #212121; padding:1.8mm 2mm; text-align:left; }
.toc td { border-bottom:.3pt solid #CCC; padding:1.5mm 2mm; }
.toc .grp td { background:#F0F8FC; font-weight:bold; padding:1.5mm; font-size:8.5pt; }
.toc .pg { text-align:right; width:14mm; }
.toc .no { width:17mm; }
.toc .ch { width:38mm; color:#555; font-size:8pt; }
.toc .note { margin-top:4mm; font-size:8.1pt; color:#555; line-height:1.7; }
.part { justify-content:flex-start; }
.part .phero { display:flex; align-items:center; gap:5mm; margin-top:6mm;
  border-bottom:1.2pt solid #212121; padding-bottom:3mm; }
.part .phero .num { font-size:38pt; font-weight:bold; line-height:1; color:#D8E9F1;
  letter-spacing:-1.5pt; min-width:24mm; }
.part .phero .cn { font-size:20pt; font-weight:bold; line-height:1.15; }
.part .phero .en { font-size:8.4pt; letter-spacing:1.4pt; color:#666; margin-top:1mm; }
.part .phero .q { margin-left:auto; text-align:right; font-size:9.2pt; line-height:1.5;
  color:#212121; max-width:64mm; }
.part .phero .q b { display:block; font-size:8pt; color:#888; letter-spacing:.6pt; margin-bottom:1mm; }
.part .plabel { font-size:8.6pt; font-weight:bold; letter-spacing:1.2pt; margin:3.2mm 0 1.4mm;
  border-left:2.2pt solid #B4472F; padding-left:2mm; }
.part .plogic { font-size:9.2pt; line-height:1.7; color:#333; }
.part .kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:2mm; margin-top:1mm; }
.part .kpis .k { border:.4pt solid #C9C9C9; background:#F3FAFD; padding:2mm 2.4mm; }
.part .kpis .k .v { font-size:13pt; font-weight:bold; line-height:1.2; color:#212121; }
.part .kpis .k .l { font-size:7.8pt; color:#666; margin-top:.8mm; }
.part .kpis .k .n { font-size:7pt; color:#888; margin-top:1.2mm; line-height:1.45;
  border-top:.3pt dotted #CCC; padding-top:.9mm; }
.part .figgrid { flex:1 1 auto; min-height:0; display:grid; grid-template-columns:repeat(2,1fr);
  grid-auto-rows:1fr; gap:2mm; margin-top:1mm; }
.part .fcard { border:.4pt solid #BFBFBF; border-left:2.2pt solid #212121; background:#FDFDFD;
  padding:2.2mm 2.8mm; display:flex; flex-direction:column; overflow:hidden; }
.part .fcard.x { border-left-color:#B4472F; background:#F8F8F8; }
.part .figgrid .fcard:last-child:nth-child(odd) { grid-column:1 / -1; }
.part .figgrid.dense .fcard { padding:1.8mm 2.4mm; }
.part .figgrid.dense .fcard ul { font-size:9pt; line-height:1.5; }
.part .fcard .fh { display:flex; align-items:baseline; gap:2mm; border-bottom:.3pt solid #DDD;
  padding-bottom:1.2mm; margin-bottom:1.5mm; }
.part .fcard .no { font-size:9pt; font-weight:bold; color:#B4472F; white-space:nowrap; }
.part .fcard .nm { font-size:9.2pt; font-weight:bold; line-height:1.35; }
.part .fcard ul { margin:0; padding-left:4.2mm; font-size:8.4pt; line-height:1.6; color:#333; }
.part .fcard li { margin-bottom:1mm; }
.part .fcard .anch { margin-top:2.4mm; padding:1.1mm 1.8mm; background:#F2F2F2;
  border-left:1.8pt solid #B4472F; font-size:8.2pt; color:#212121; }
.part .fcard .anch b { color:#B4472F; margin-right:1mm; }
.part .fcard .anote { margin-top:1.4mm; font-size:7.9pt; line-height:1.5; color:#555; }
.part .figgrid.dense .fcard .anch { margin-top:1.2mm; padding:.8mm 1.4mm; font-size:7.8pt; }
.part .figgrid.dense .fcard .anote { display:none; }   /* 10 卡密集章：保证出处行不被裁 */
.part .figgrid.dense .fcard .src { padding-top:.8mm; }
.part .fcard .src { margin-top:auto; padding-top:1.2mm; border-top:.3pt dashed #CCC;
  font-size:7.8pt; color:#777; display:flex; justify-content:space-between; gap:2mm; }
.part .plink { margin-top:2mm; border-top:.5pt dashed #999; padding-top:1.8mm;
  font-size:8.2pt; color:#555; line-height:1.5; }
.back h2 { text-align:center; font-size:16pt; margin-top:20mm; }
.back .blk { margin-top:7mm; font-size:9pt; line-height:1.85; }
.back .blk b { display:block; margin-bottom:1.5mm; }


/* ============================================================
   Apple 极简视觉体系 · 2026-11-16
   白纸底 / 石墨文字 / 单一前进蓝 / 银线圆角 / 火花橙点睛
   ============================================================ */
html, body { background:#FFFFFF; color:#1D1D1F;
  font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue","Segoe UI","PingFang SC","Microsoft YaHei","Noto Sans CJK SC",sans-serif;
  -webkit-font-smoothing:antialiased; }
.page { background:#FFFFFF; position:relative; padding:10mm 12mm 8mm; }
.phead { display:flex; justify-content:space-between; align-items:center; gap:3mm;
  font-size:8.4pt; letter-spacing:.1pt; border-bottom:.6pt solid #D2D2D7; padding-bottom:1.5mm; }
.phead > span:first-child { flex:0 1 auto; min-width:0; white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; color:#6E6E73; font-weight:400; display:flex; align-items:center; gap:1.8mm; }
.phead .pm { display:inline-flex; width:4.4mm; height:4.4mm; flex:0 0 auto; }
.phead .pm svg { width:100%; height:100%; display:block; }
.phead .r { flex:0 0 auto; color:#1D1D1F; white-space:nowrap; font-weight:500; }

/* ---- 图页 ---- */
.figbox { position:relative; flex:1 1 auto; min-height:0; border:.5pt solid #E5E5EA;
  border-radius:2.6mm; padding:1mm; background:#FFFFFF; display:flex;
  align-items:center; justify-content:center; box-shadow:0 1px 6px rgba(0,0,0,.035); }
.figbox > svg { width:100%; height:100%; display:block; }
.figwm { position:absolute; right:4mm; bottom:4mm; width:34mm; height:34mm;
  opacity:.045; pointer-events:none; z-index:0; }
.figwm svg { width:100%; height:100%; display:block; }
.figtag { position:absolute; right:2.8mm; top:2.2mm; font-size:7pt; letter-spacing:.9pt;
  color:#A1A1A6; z-index:2; }
.keypts { flex:0 0 auto; margin-top:1.6mm; border:.5pt solid #E5E5EA;
  border-left:1.4mm solid #0071E3; border-radius:2mm; padding:1.5mm 2.4mm;
  font-size:8pt; line-height:1.45; color:#3A3A3C; background:#F5F7FA; }
.keypts b { color:#0071E3; font-size:8.2pt; letter-spacing:.4pt; }
.pfoot { flex:0 0 auto; margin-top:1.4mm; border-top:.6pt solid #D2D2D7; padding-top:1.2mm;
  display:flex; justify-content:space-between; font-size:8pt; color:#86868B; }

/* ---- 目录 ---- */
.toc { justify-content:flex-start; }
.tmark { display:flex; align-items:center; justify-content:center; gap:2.4mm; margin:5mm 0 1mm; }
.tmark .ic { width:8mm; height:8mm; }
.tmark .ic svg { width:100%; height:100%; display:block; }
.tmark span { font-size:8pt; letter-spacing:2.2pt; color:#86868B; font-weight:500; }
.toc h2 { text-align:center; font-size:19pt; font-weight:600; letter-spacing:.4pt; margin:2mm 0 1.5mm; }
.toc .lead { text-align:center; font-size:8.6pt; color:#6E6E73; margin-bottom:5mm; }
.toc table { border-collapse:collapse; font-size:8.6pt; }
.toc th { border-top:.7pt solid #1D1D1F; border-bottom:.6pt solid #D2D2D7;
  padding:2mm; color:#6E6E73; font-weight:500; font-size:8pt; letter-spacing:.6pt; }
.toc td { border-bottom:.4pt solid #EDEDEF; padding:1.7mm 2mm; }
.toc .grp td { background:#F5F7FA; color:#0071E3; font-weight:600; font-size:8.4pt;
  border-left:1.2mm solid #0071E3; }
.toc .ch, .toc .note, .toc .lead { color:#6E6E73; }
.toc .note { margin-top:5mm; background:#F5F7FA; border-radius:2.4mm;
  padding:2.6mm 3mm; font-size:8.2pt; line-height:1.75; }

/* ---- 章节扉页 ---- */
.part { justify-content:flex-start; }
.partwm { position:absolute; right:-10mm; top:22mm; width:86mm; height:86mm;
  opacity:.038; pointer-events:none; }
.partwm svg { width:100%; height:100%; display:block; }
.part .phero { position:relative; display:flex; align-items:center; gap:5mm; margin-top:7mm;
  border-bottom:.8pt solid #D2D2D7; padding-bottom:4mm; }
.part .phero .num { font-size:44pt; font-weight:600; line-height:1; color:#DCEBFB;
  letter-spacing:-2pt; min-width:26mm; }
.part .phero .cn { font-size:21pt; font-weight:600; letter-spacing:.2pt; }
.part .phero .en { font-size:8pt; letter-spacing:1.6pt; color:#86868B; margin-top:1.4mm; }
.part .phero .q { margin-left:auto; text-align:right; font-size:9pt; line-height:1.6;
  color:#3A3A3C; max-width:62mm; }
.part .phero .q b { display:block; font-size:7.6pt; color:#86868B; letter-spacing:.8pt;
  margin-bottom:1mm; font-weight:500; }
.part .plabel { font-size:8pt; font-weight:600; letter-spacing:1.6pt; margin:3.6mm 0 1.6mm;
  border-left:1.2mm solid #0071E3; padding-left:2.4mm; color:#0071E3; }
.part .plogic { font-size:9pt; line-height:1.75; color:#3A3A3C; }
.part .kpis { gap:2.2mm; }
.part .kpis .k { border:.5pt solid #E5E5EA; border-top:1.2mm solid #0071E3;
  border-radius:2.4mm; background:#FFFFFF; padding:2.4mm 2.6mm;
  box-shadow:0 1px 5px rgba(0,0,0,.03); }
.part .kpis .k:nth-child(even) { border-top-color:#A8CEF7; }
.part .kpis .k .v { font-size:15pt; font-weight:600; color:#1D1D1F; }
.part .kpis .k .l { color:#6E6E73; font-size:7.8pt; }
.part .kpis .k .n { border-top:.4pt solid #EDEDEF; color:#86868B; font-size:7pt; }
.part .figgrid { gap:2.2mm; }
.part .fcard { border:.5pt solid #E5E5EA; border-left:1.2mm solid #A8CEF7;
  border-radius:2.6mm; background:#FFFFFF; padding:2.4mm 3mm;
  box-shadow:0 1px 5px rgba(0,0,0,.028); }
.part .fcard.x { border-left-color:#0071E3; background:#FAFCFF; }
.part .fcard .fh { border-bottom:.4pt solid #EDEDEF; }
.part .fcard .no { color:#0071E3; font-weight:600; }
.part .fcard .nm { font-weight:600; }
.part .fcard ul { color:#3A3A3C; }
.part .fcard .anch { background:#F5F7FA; border-left:1.2mm solid #0071E3;
  border-radius:1.6mm; color:#3A3A3C; }
.part .fcard .anch b { color:#0071E3; }
.part .fcard .src { border-top:.4pt dashed #E5E5EA; color:#86868B; }
.part .plink { border-top:.5pt solid #E5E5EA; color:#6E6E73; }
/* 卡片内距收紧：保证每卡底部「出处 / 第 N 图」完整显示，不被 overflow 裁掉 */
.part .fcard .fh { padding-bottom:.9mm; margin-bottom:1mm; }
.part .fcard ul { font-size:8.3pt; line-height:1.5; padding-left:3.8mm; }
.part .fcard li { margin-bottom:.6mm; }
.part .fcard .anch { margin-top:1.6mm; padding:.9mm 1.6mm; font-size:8pt; line-height:1.4; }
.part .fcard .anote { margin-top:.9mm; font-size:7.7pt; line-height:1.4; }
.part .fcard .src { padding-top:.9mm; font-size:7.6pt; line-height:1.35; }
.part .figgrid.dense .fcard { padding:1.5mm 2.2mm; }
.part .figgrid.dense .fcard .fh { padding-bottom:.6mm; margin-bottom:.6mm; }
.part .figgrid.dense .fcard ul { font-size:8.2pt; line-height:1.4; padding-left:3.4mm; }
.part .figgrid.dense .fcard .anch { margin-top:.8mm; padding:.6mm 1.2mm; font-size:7.5pt; line-height:1.35; }
.part .figgrid.dense .fcard .src { padding-top:.5mm; font-size:7.3pt; line-height:1.3; }

/* ---- 封面：白纸底 + 极细彩色带 ---- */
.cover { position:relative; justify-content:flex-start; align-items:stretch; text-align:left;
  padding:0; background:#FFFFFF; color:#1D1D1F; }
.cv-band { height:1.6mm; flex:0 0 auto;
  background:linear-gradient(90deg,#0071E3 0%,#7FB8F2 62%,#FF9F0A 100%); }
.cv-body { flex:1 1 auto; min-height:0; padding:7mm 12mm 5mm; display:flex;
  flex-direction:column; position:relative; }
.cv-topline { display:flex; align-items:center; justify-content:space-between; }
.cv-logo { width:96mm; }
.gf-logo { display:flex; align-items:center; gap:3mm; }
.gf-mark { width:13mm; height:13mm; flex:0 0 auto; }
.gf-mark svg { width:100%; height:100%; display:block; }
.gf-name { font-size:17pt; font-weight:600; letter-spacing:-.5pt; color:#1D1D1F; line-height:1.1; }
.gf-name span { color:#0071E3; }
.gf-sub { font-size:7pt; letter-spacing:1.5pt; color:#86868B; margin-top:1mm; }
.gf-logo.sm .gf-mark { width:6mm; height:6mm; }
.gf-logo.sm .gf-name { font-size:10pt; }
.gf-logo.sm .gf-sub { display:none; }
.cv-topline .side { display:flex; align-items:center; gap:2mm; }
.cv-topline .side .ic { width:9mm; height:9mm; }
.cv-topline .side .ic svg { width:100%; height:100%; display:block; }
.cv-topline .side span { font-size:7.6pt; letter-spacing:1.4pt; color:#86868B; }
.cv-mascot { position:absolute; right:11mm; top:24mm; width:31mm; background:#F5F7FA;
  border:.5pt solid #E5E5EA; border-radius:6mm; padding:1mm; }
.cv-mascot svg { width:100%; height:auto; display:block; }
.cv-gwatermark { position:absolute; right:-8mm; bottom:26mm; width:78mm; height:78mm;
  opacity:.035; pointer-events:none; }
.cv-gwatermark svg { width:100%; height:100%; display:block; }
.cv-kicker { margin-top:6mm; font-size:8.2pt; letter-spacing:2.6pt; color:#0071E3; font-weight:600; }
.cv-title { margin-top:3.2mm; font-size:34pt; font-weight:600; line-height:1.18;
  letter-spacing:-1.1pt; color:#1D1D1F; }
.cv-title em { font-style:normal; color:#0071E3; font-weight:600; }
.cv-sub { margin-top:2.4mm; font-size:14pt; letter-spacing:2.8pt; color:#6E6E73; font-weight:400; }
.cv-tagline { margin-top:2.6mm; font-size:9pt; color:#86868B; letter-spacing:.2pt; }
.cv-rule { width:100%; height:.6pt; background:#D2D2D7; margin:5mm 0 0; }
.cv-meta { margin-top:3mm; font-size:8.6pt; color:#6E6E73; line-height:1.8; }
.cv-sec { margin-top:4.2mm; font-size:7.8pt; font-weight:600; letter-spacing:1.8pt;
  color:#6E6E73; border-left:1.2mm solid #0071E3; padding-left:2.2mm; }
.cv-chain { display:flex; gap:1.2mm; margin-top:2mm; }
.cv-chain .nd { flex:1; background:#F5F7FA; border:.5pt solid #E5E5EA; border-radius:2mm;
  padding:1.9mm .5mm; text-align:center; font-size:7.4pt; line-height:1.35; color:#3A3A3C; }
.cv-chain .nd:first-child { background:#0071E3; border-color:#0071E3; color:#FFFFFF; }
.cv-chain .nd b { display:block; font-size:9.2pt; font-weight:600; color:#0071E3; }
.cv-chain .nd:first-child b { color:#FFFFFF; }
.cv-facts { display:grid; grid-template-columns:repeat(4,1fr); gap:2mm; margin-top:2mm; }
.cv-facts .f { background:#FFFFFF; border:.5pt solid #E5E5EA; border-radius:2.6mm;
  padding:2.8mm 3.2mm; box-shadow:0 1px 6px rgba(0,0,0,.035); }
.cv-facts .f .v { font-size:19pt; font-weight:600; color:#0071E3; line-height:1.1; letter-spacing:-.6pt; }
.cv-facts .f .l { font-size:7.8pt; color:#6E6E73; margin-top:1.4mm; }
.cv-list { display:grid; grid-template-columns:repeat(5,1fr); gap:1.4mm; margin-top:2mm;
  background:#F5F7FA; border-radius:2.6mm; padding:2.8mm 3.2mm; }
.cv-list div { font-size:7.9pt; line-height:1.6; color:#3A3A3C; }
.cv-list b { color:#0071E3; font-size:8.2pt; font-weight:600; }
.cv-palette { display:flex; gap:1.6mm; margin-top:2mm; }
.cv-palette .sw { flex:1; background:#FFFFFF; border:.5pt solid #E5E5EA;
  border-radius:2mm; padding:1.6mm 1.4mm; }
.cv-palette .chip { height:6mm; border-radius:1.4mm; margin-bottom:1.4mm; }
.cv-palette .nm { font-size:7.4pt; font-weight:600; color:#1D1D1F; }
.cv-palette .hx { font-size:6.9pt; color:#86868B; margin-top:.5mm; }
.cv-more { display:grid; grid-template-columns:1fr 1fr; gap:2mm 2.4mm; margin-top:2mm; }
.cv-more .m { background:#F5F7FA; border-radius:2.4mm; padding:2.4mm 3mm;
  color:#3A3A3C; font-size:7.8pt; line-height:1.55; }
.cv-more .m b { display:block; color:#1D1D1F; font-size:8.6pt; letter-spacing:.4pt;
  margin-bottom:1.1mm; font-weight:600; }
.cv-more .m span { color:#86868B; font-size:7.2pt; }
.cv-foot { margin-top:auto; padding-top:3mm; border-top:.6pt solid #D2D2D7;
  font-size:7.8pt; color:#86868B; line-height:1.7; }

/* ---- 封底：白纸底 ---- */
.back { position:relative; background:#FFFFFF; color:#1D1D1F; padding:10mm 12mm 8mm; }
.back .phead { border-bottom-color:#D2D2D7; color:#6E6E73; }
.back .phead .r { color:#1D1D1F; }
.back .phead .pm { display:inline-flex; width:4.4mm; height:4.4mm; }
.back .phead .pm svg { width:100%; height:100%; display:block; }
.bk-logo { width:96mm; margin-top:8mm; }
.bk-slogan { margin-top:2mm; font-size:8.6pt; letter-spacing:2.2pt; color:#0071E3; font-weight:600; }
.bk-rule { width:100%; height:.6pt; background:#D2D2D7; margin:5mm 0 0; }
.bk-h { text-align:center; font-size:17pt; font-weight:600; letter-spacing:4pt;
  margin:5mm 0 3mm; color:#1D1D1F; }
.bk-fast { display:flex; gap:1.8mm; margin-top:3mm; }
.bk-fast .f { flex:1; background:#F5F7FA; border:.5pt solid #E5E5EA; border-radius:2.4mm;
  padding:2.4mm 1mm; text-align:center; color:#1D1D1F; }
.bk-fast .f b { display:block; font-size:15pt; font-weight:600; line-height:1.1; color:#0071E3; }
.bk-fast .f span { font-size:7.1pt; color:#6E6E73; }
.bk-grid { display:grid; grid-template-columns:1fr 1fr; gap:2.4mm 4mm; }
.bk-blk { border-top:.6pt solid #D2D2D7; padding-top:2mm; font-size:8.3pt;
  line-height:1.7; color:#3A3A3C; }
.bk-blk b { display:block; color:#0071E3; font-size:9pt; margin-bottom:1mm;
  letter-spacing:.4pt; font-weight:600; }
.bk-blk.wide { grid-column:1 / -1; }
.bk-mascot { position:absolute; right:13mm; top:23mm; width:27mm; background:#F5F7FA;
  border:.5pt solid #E5E5EA; border-radius:5mm; padding:1mm; }
.bk-mascot svg { width:100%; height:auto; display:block; }
.bk-gwatermark { position:absolute; left:-14mm; bottom:36mm; width:80mm; height:80mm;
  opacity:.035; pointer-events:none; }
.bk-gwatermark svg { width:100%; height:100%; display:block; }
.bk-pal { display:flex; gap:1.6mm; margin-top:5mm; }
.bk-pal .sw { flex:1; border:.5pt solid #E5E5EA; border-radius:2mm;
  padding:1.6mm 1.4mm; background:#FFFFFF; }
.bk-pal .chip { height:6mm; border-radius:1.4mm; margin-bottom:1.2mm; }
.bk-pal .nm { font-size:7.6pt; font-weight:600; color:#1D1D1F; }
.bk-pal .hx { font-size:7pt; color:#86868B; margin-top:.4mm; }
.bk-foot { margin-top:auto; padding-top:3mm; border-top:.6pt solid #D2D2D7;
  display:flex; justify-content:space-between; font-size:8pt; color:#86868B; }
.bk-foot b { color:#0071E3; }
.bk-more { display:grid; grid-template-columns:repeat(4,1fr); gap:2mm; margin-top:3mm; }
.bk-more .m { background:#F5F7FA; border:.5pt solid #E5E5EA; border-radius:2.2mm;
  border-top:1.2mm solid #0071E3; padding:2.4mm 2.6mm; }
.bk-more .m:nth-child(even) { border-top-color:#A8CEF7; }
.bk-more .m .k { font-size:11pt; font-weight:600; color:#0071E3; }
.bk-more .m .t { font-size:7.5pt; color:#6E6E73; margin-top:1mm; line-height:1.55; }
.bk-honest { margin-top:3mm; background:#F5F7FA; border-radius:2.2mm;
  border-left:1.4mm solid #FF9F0A; padding:2.6mm 3mm;
  font-size:7.8pt; line-height:1.62; color:#3A3A3C; }
.bk-honest b { display:block; color:#1D1D1F; font-size:8.6pt; letter-spacing:.6pt;
  margin-bottom:1mm; font-weight:600; }
.bk-honest span { display:block; margin-top:1mm; color:#86868B; font-size:7.2pt; }

"""


PALETTE = [('石墨 Graphite', '#1D1D1F'), ('前进蓝 Forward', '#0071E3'), ('冰蓝 Ice', '#EAF3FF'), ('云雾 Mist', '#F5F5F7'), ('银线 Silver', '#D2D2D7'), ('火花橙 Spark', '#FF9F0A')]

BRAND = Path(r"F:\GrowthForward_AI学习伴侣\brand_assets")


BRAND = Path(r"F:\GrowthForward_AI学习伴侣\brand_assets")


def brand_svg(name, prefix="b", white=False, recolor=True):
    """兼容旧调用：统一返回新的 Apple 极简品牌资产。"""
    if name.startswith("mascot"):
        return B.mascot(prefix)
    if name.startswith("logo"):
        return B.mark(stroke='#FFFFFF' if white else B.BLUE,
                      arrow='#FFFFFF' if white else B.SPARK)
    return B.mark()


def svg_inline(path: Path) -> str:
    s = path.read_text(encoding="utf-8")
    def fix(m):
        attrs = m.group(1)
        attrs = re.sub(r'\s(?:width|height|preserveAspectRatio)\s*=\s*"[^"]*"', '', attrs)
        return '<svg' + attrs + ' preserveAspectRatio="xMidYMid meet">'
    return re.sub(r'<svg([^>]*)>', fix, s, count=1)


def head(right):
    return (f'<div class="phead"><span>{B.head_mark()}GrowthForward · 商业计划书图表册</span>'
            f'<span class="r">{html.escape(right)}</span></div>')


def figure_page(idx, d):
    pts = '　'.join(f'{i}. {html.escape(p)}' for i, p in enumerate(d['pts'], 1))
    foot = (f'<div class="pfoot"><span>{html.escape(d["no"])}　{html.escape(d["name"])}</span>'
            f'<span>出处：{html.escape(d["src"])}　·　第 {idx} 图 / 共 {len(F)} 图</span></div>')
    return (f'<div class="page">{head(d["chap"] + "　|　" + d["no"] + "　" + d["name"])}'
            f'<div class="figbox"><div class="figwm">{B.mark()}</div>{svg_inline(SRC / d["f"])}</div>'
            f'<div class="keypts"><b>要点</b>　{pts}</div>{foot}</div>')


def chapter_page(c, i):
    meta = CH_META[c["no"]]
    figs = [d for d in F if d['chap'] == c['key']]
    seq = {d['no']: k for k, d in enumerate(F, 1)}
    nxt = CHAPTERS[i + 1]['cn'] if i + 1 < len(CHAPTERS) else '封底 · 编制说明'
    prev = '承接上一章' if i else '作为全册起点'

    kpin = KPI_NOTE.get(c["no"], [""] * 4)
    kpis = ''.join(f'<div class="k"><div class="v">{html.escape(v)}</div>'
                   f'<div class="l">{html.escape(l)}</div>'
                   f'<div class="n">{html.escape(kpin[j] if j < len(kpin) else "")}</div></div>'
                   for j, (v, l) in enumerate(meta["kpi"]))

    def anch(j):
        """把关键数据与其口径绑定到具体图卡，卡片内不再只剩两三行字。"""
        v, l = meta["kpi"][j % 4]
        note = kpin[j % len(kpin)] if kpin else ""
        return (f'<div class="anch"><b>关键数据</b>　{html.escape(v)} · {html.escape(l)}</div>'
                f'<div class="anote">口径：{html.escape(note)}</div>')

    # 图卡矩阵：每张图一卡，直接给要点而非空表格导航；图数少的章用延展卡补足密度
    n_cards = len(figs) + (1 if len(figs) < 8 else 0) + len(meta["extra"])
    dense = n_cards >= 8                 # 卡片多时行高变小，每卡只给一条完整要点避免裁字
    cards_html = []
    if len(figs) < 8:
        concl = ''.join(f'<li>{html.escape(p)}</li>' for p in c['pts'])
        cards_html.append(
            '<div class="fcard x"><div class="fh"><span class="no">结论</span>'
            '<span class="nm">本章核心结论</span></div>'
            f'<ul>{concl}</ul>{anch(0)}'
            '<div class="src"><span>章级结论</span>'
            '<span>后续图页逐条展开</span></div></div>')
    for j, d in enumerate(figs):
        pts = ''.join(f'<li>{html.escape(p)}</li>' for p in d['pts'][:1 if dense else 2])
        cards_html.append(
            f'<div class="fcard"><div class="fh"><span class="no">{html.escape(d["no"])}</span>'
            f'<span class="nm">{html.escape(d["name"])}</span></div><ul>{pts}</ul>'
            f'{anch(j + (0 if len(figs) >= 8 else 1))}'
            f'<div class="src"><span>出处：{html.escape(d["src"])}</span>'
            f'<span>第 {seq[d["no"]]} 图 / 共 {len(F)} 图</span></div></div>')
    for k, (title, lines) in enumerate(meta["extra"], 1):
        pts = ''.join(f'<li>{html.escape(p)}</li>' for p in lines)
        cards_html.append(
            f'<div class="fcard x"><div class="fh"><span class="no">延展 {k}</span>'
            f'<span class="nm">{html.escape(title)}</span></div><ul>{pts}</ul>'
            f'{anch(len(figs) + k + (0 if len(figs) >= 8 else 1))}'
            '<div class="src"><span>本章补充信息</span><span>与前后章证据互引</span></div></div>')

    # 删掉「承接 → 本章回答 → 向后衔接」的导航套话，换成可回溯的证据出处索引
    srcs = []
    for d in figs:
        for s in re.split(r"[/·、（）]", d["src"]):
            s = s.strip()
            if s and s not in srcs:
                srcs.append(s)
    link = (f'本章证据出处：{" · ".join(html.escape(s) for s in srcs[:5])}'
            f'　｜　{len(figs)} 张图可沿「出处」回溯正文 → 「{html.escape(nxt)}」。')
    return f'''<div class="page part"><div class="partwm">{B.mark()}</div>{head("章 扉 页 · " + c["no"])}
      <div class="phero">
        <div class="num">{c["no"]}</div>
        <div><div class="cn">{html.escape(c["cn"])}</div>
             <div class="en">{html.escape(c["en"])}</div></div>
        <div class="q"><b>本章回答的 BP 问题</b>{html.escape(meta["q"])}<br/>共 {len(figs)} 张图</div>
      </div>
      <div class="plabel">本 章 逻 辑 定 位</div>
      <div class="plogic">{html.escape(c['logic'])}</div>
      <div class="plabel">本 章 关 键 数 据</div>
      <div class="kpis">{kpis}</div>
      <div class="plabel">本 章 图 页 与 核 心 结 论</div>
      <div class="figgrid{' dense' if dense else ''}">{''.join(cards_html)}</div>
      <div class="plink">{link}</div>
      <div class="pfoot"><span>{html.escape(c["key"])}</span><span>章节扉页 {i+1} / {len(CHAPTERS)}</span></div></div>'''


def cover_page():
    groups = {}
    for d in F:
        groups.setdefault(d['chap'], []).append(d['no'])
    lines = ''.join(f'<div><b>{html.escape(k)}</b>　{len(v)} 图</div>' for k, v in groups.items())
    chain = ''.join(f'<div class="nd"><b>{no}</b>{html.escape(nm)}</div>'
                    for no, nm in [("00", "品牌"), ("01", "摘要"), ("02", "市场"),
                                   ("03", "产品"), ("04", "架构"), ("05", "AI 治理"),
                                   ("06", "工程"), ("07", "财务"), ("08", "团队"), ("09", "进度")])
    facts = ''.join(f'<div class="f"><div class="v">{v}</div><div class="l">{html.escape(l)}</div></div>'
                    for v, l in [("38 项", "功能总账 F01–F38"), ("11 款", "已上线竞品实证"),
                                 ("¥82", "内测月支出 · 官网实采"), ("16 周", "交付排期")])
    sw = ''.join(f'<div class="sw"><div class="chip" style="background:{c}"></div>'
                 f'<div class="nm">{html.escape(n)}</div><div class="hx">{c}</div></div>'
                 for n, c in PALETTE)
    return f'''<div class="page cover">
      <div class="cv-band"></div>
      <div class="cv-body">
        <div class="cv-gwatermark">{B.mark()}</div>
        <div class="cv-topline">
          <div class="cv-logo">{B.logo()}</div>
          <div class="side"><div class="ic">{B.icon("cvic")}</div><span>GFLC · 2026</span></div>
        </div>
        <div class="cv-mascot">{B.mascot("cvm")}</div>
        <div class="cv-kicker">BUSINESS PLAN · ACADEMIC FIGURE BOOKLET</div>
        <div class="cv-title">GrowthForward<br/><em>AI 学习伴侣</em></div>
        <div class="cv-sub">商业计划书学术图表册</div>
        <div class="cv-tagline">把「看过」变成「学会」　·　Learn. Grow. Keep Moving Forward.</div>
        <div class="cv-rule"></div>
        <div class="cv-meta">40 张学术插图　·　卷首品牌篇 + 九章 BP 逻辑　·　统一 A4 竖版与页边距<br/>
          真实报价与已上线产品采集于 2026-11-14，全部图页可沿「出处」回溯正文</div>
        <div class="cv-sec">全 册 论 证 链　·　十章递进，每章回答一个 BP 问题</div>
        <div class="cv-chain">{chain}</div>
        <div class="cv-sec">关 键 数 据　·　全册口径一致</div>
        <div class="cv-facts">{facts}</div>
        <div class="cv-sec">章 节 与 图 量　·　40 图 / 54 页</div>
        <div class="cv-list">{lines}</div>
        <div class="cv-sec">G F 色 彩 系 统　·　石墨 × 前进蓝 × 火花橙</div>
        <div class="cv-palette">{sw}</div>
        <div class="cv-sec">全 册 数 据 口 径 与 阅 读 指 引　·　可逐条核验</div>
        <div class="cv-more">
          <div class="m"><b>价格与采购口径</b>
            2026-11-14 官网实采：腾讯云轻量 2C4G5M ¥188/年（学生 ¥46.43/3 月，续费 ¥65/月）、
            阿里云轻量 ¥199/年、域名 ¥60–80/年、Token Plan Lite ¥39 / Essential ¥79 每月。
            <br/><span>对应图 7-2 / 7-3 · 技术方案 §5.8 运行成本细目</span></div>
          <div class="m"><b>市场数据口径</b>
            CNNIC 第 57 次报告（2026-02-05，截至 2025-12）在线教育用户 3.27 亿；
            2027 研考官方报名人数截至 2026-11-15 尚未公布，机构测算 315–335 万仅作敏感性区间，不进 TAM。
            <br/><span>对应图 2-3 · 技术方案 §1.5 附 6 条来源链接</span></div>
          <div class="m"><b>阅读与回溯方式</b>
            每张图页底部标注「出处」与「第 N 图 / 共 40 图」，可沿图号回溯产品报告与技术方案正文；
            章节扉页给出本章回答的 BP 问题、关键数据格与每张图的要点和证据出处。
            <br/><span>图号 0-1 / 1-1 / 2-x … 9-x 与文件名严格一致</span></div>
          <div class="m"><b>版式与视觉规范</b>
            40 张矢量图统一 680×960 画布、632 全宽内容区；册页 A4 210×297 mm，
            左右 12 / 上 10 / 下 8 mm 页边距；纯图与册页均输出 1588×2246 px。
            <br/><span>白纸底 + 石墨正文 + 前进蓝主色；火花橙仅作向前箭头点睛，风险保留砖红</span></div>
        </div>
        <div class="cv-foot">毕业设计材料　·　配套《产品报告 V2 完整版》《技术方案_GrowthForward.md》《BiliNote_深度拆解分析.md》<br/>
          2026 年 11 月 16 日　·　GrowthForward 成长向前</div>
      </div></div>'''


def toc_page(part, entries, total_parts):
    rows, last = [], None
    for idx, d in entries:
        if d['chap'] != last:
            rows.append(f'<tr class="grp"><td colspan="4">{html.escape(d["chap"])}</td></tr>')
            last = d['chap']
        rows.append(f'<tr><td class="no">{html.escape(d["no"])}</td><td>{html.escape(d["name"])}</td>'
                    f'<td class="ch">{html.escape(d["src"])}</td><td class="pg">{idx}</td></tr>')
    note = ("版式说明：全部图页统一 A4 竖版（210 × 297 mm），左右页边距 12 mm、上 10 mm、下 8 mm；"
            "40 张插图统一 680 × 960 标准画布，图区按近 1 : 1 铺满页面；每页含页眉（章节 / 图号 / 图名）、"
            "整幅图区、要点提示与页脚。全册按商业计划书逻辑分卷首品牌篇与九章，每章设扉页说明逻辑定位与核心结论。") if part == 1 else (
            "阅读提示：图号按本册 BP 章节重编；「出处」列保留《技术方案》《产品报告》原始章节号，便于回溯原文。"
            "K1 大文件直传 / K2 长任务入队 / K3 任务态反馈在多图间编号一致，可跨图引用；"
            "◆ 为 2026-11-14 架构评审新增项；所有价格为当日官网实采并标注来源。")
    return f'''<div class="page toc">{head(f"图 目 录 · 第 {part} / {total_parts} 部分")}<div class="tmark"><div class="ic">{B.mark()}</div><span>GROWTHFORWARD · FIGURE BOOKLET</span></div><h2>图 目 录（{part} / {total_parts}）</h2>
      <div class="lead">共 {len(F)} 张图 · 按商业计划书九章分组 · 图号与章节对应</div>
      <table><tr><th class="no">图号</th><th>图名</th><th class="ch">出处</th><th class="pg">序号</th></tr>
      {''.join(rows)}</table>
      <div class="note">{note}</div>
      <div class="pfoot"><span>目录 {part} / {total_parts}</span><span>共 {len(F)} 图</span></div></div>'''


def back_page():
    sw = ''.join(f'<div class="sw"><div class="chip" style="background:{c}"></div>'
                 f'<div class="nm">{html.escape(n)}</div><div class="hx">{c}</div></div>'
                 for n, c in PALETTE)
    return f'''<div class="page back">
      <div class="phead"><span>{B.head_mark()}GrowthForward · 商业计划书图表册</span><span class="r">编制说明</span></div>
      <div class="bk-gwatermark">{B.mark()}</div>
      <div class="bk-logo">{B.logo()}</div>
      <div class="bk-slogan">LEARN. GROW. KEEP MOVING FORWARD.</div>
      <div class="bk-rule"></div>
      <h2 class="bk-h">编 制 说 明</h2>
      <div class="bk-fast">
        <div class="f"><b>40</b><span>张学术插图</span></div>
        <div class="f"><b>54</b><span>页 A4 图册</span></div>
        <div class="f"><b>10</b><span>章 BP 逻辑</span></div>
        <div class="f"><b>38</b><span>项功能总账</span></div>
        <div class="f"><b>11</b><span>款上线竞品</span></div>
        <div class="f"><b>16</b><span>周交付排期</span></div>
      </div>
      <div class="bk-grid">
        <div class="bk-blk"><b>配套文档</b>
          《产品报告 V2 完整版》：市场、竞品实证、38 项功能、成本与盈利（第九章按实价校准）；
          《技术方案_GrowthForward.md》：架构、AI 管线、门禁、部署与运行成本，§1.5 附 6 条市场数据来源链接；
          《BiliNote_深度拆解分析.md》：开源参照系逐文件读码拆解。</div>
        <div class="bk-blk"><b>结构逻辑（商业计划书式）</b>
          卷首品牌 → ① 执行摘要 → ② 市场与机会 → ③ 产品与解决方案（功能先行）→
          ④ 系统架构 → ⑤ 模型选型与 AI 治理 → ⑥ 工程与测试 → ⑦ 财务可行性 →
          ⑧ 团队与资源 → ⑨ 进度与风险控制。模型与治理细节统一后置在功能之后。</div>
        <div class="bk-blk"><b>图号体系</b>
          图 0-1 品牌 · 1-1 摘要 · 2-x 市场 · 3-x 产品与功能域（含 3-10 遗忘曲线理论）·
          4-x 架构与流程 · 5-x 模型与 AI 治理 · 6-x 工程测试 · 7-x 财务采购 · 8-x 团队 · 9-x 进度风险。
          共 40 张，中英双语图题与文件名编号严格一致；F01–F38 / K1–K3 / G1–G7 / R1–R10 全册贯通。</div>
        <div class="bk-blk"><b>数据与视觉规范</b>
          全册采用白纸底 + 石墨 #1D1D1F 正文；前进蓝 #0071E3 为唯一主色，用于表头、图形标与关键数值；
          冰蓝 #EAF3FF / 云雾 #F5F5F7 作浅底，银线 #D2D2D7 作分隔，火花橙 #FF9F0A 仅用于向前箭头；
          风险项独立使用砖红 #B4472F。图形标为几何 G 环 + 冲出开口的箭头，吉祥物「小前」为极简悬浮机器人。
          采购与模型单价为 2026-11-14 官网实采；市场规模并列公开口径，收入与用户数显式标注为规划假设。</div>
        <div class="bk-blk wide"><b>源文件与重建</b>
          全部插图保留矢量 SVG 于「学术图表/src/」；_gf_brand.py 为统一品牌资产（图形标 / icon / 吉祥物 / 色板），
          _figlib / _figlib2 / _figlib_bp 为统一图形库，_build_figs_a / c / d / e / f 与 _build_bp_a / b / c / d 分组生成 40 张插图；
          _patch_apple_theme.py 负责主题色（幂等），_convert.py 导出 1588×2246 纯图，_booklet.py 合成 A4 册页。
          日常增量重建走「单独调生成器 → _convert.py → _booklet.py」，勿直接跑全量重建覆盖定点修订。</div>
      </div>
      <div class="bk-pal">{sw}</div>
      <div class="bk-more">
        <div class="m"><div class="k">F01–F38</div><div class="t">38 项功能总账<br/>图 3-2 全景 · 3-4–3-9 六大功能域</div></div>
        <div class="m"><div class="k">G1–G7</div><div class="t">上线质量门禁<br/>图 6-2 门禁 · 6-3 评测与验收</div></div>
        <div class="m"><div class="k">R1–R10</div><div class="t">十项风险登记册<br/>图 9-2 热力矩阵与分级对策</div></div>
        <div class="m"><div class="k">K1–K3</div><div class="t">三项关键假设<br/>图 2-3 市场口径 · 7-4 敏感性</div></div>
      </div>
      <div class="bk-honest"><b>诚实边界与版本说明</b>
        本项目为单人毕业设计，无一手用户调研、无模型微调、无高并发实测；
        遗忘曲线、成长轨迹与热力分级均为理论示意（非实测），市场规模并列公开口径，收入与用户数显式标注为规划假设。
        全部单价为 2026-11-14 官网实采；2027 研考官方报名人数截至编制日尚未公布，机构测算仅作敏感性区间。
        <span>版本 2026-11-16　·　配套 3 份文档　·　源矢量 40 份　·　中英双语图题</span></div>
      <div class="bk-mascot">{B.mascot("bkms")}</div>
      <div class="bk-foot"><span><b>GrowthForward</b> 成长向前 · AI 学习伴侣</span>
        <span>40 图 / 54 页 · A4 · 2026-11-16</span></div></div>'''


def main():
    idx = {d['no']: i for i, d in enumerate(F, 1)}
    entries = [(idx[d['no']], d) for d in F]
    mid = (len(F) + 1) // 2
    pages = [cover_page(),
             toc_page(1, entries[:mid], 2), toc_page(2, entries[mid:], 2)]
    # 章扉页穿插在对应章节第一张图之前
    for ci, c in enumerate(CHAPTERS):
        pages.append(chapter_page(c, ci))
        for d in F:
            if d['chap'] == c['key']:
                pages.append(figure_page(idx[d['no']], d))
    pages.append(back_page())

    doc = ('<!DOCTYPE html><html><head><meta charset="utf-8"><style>' + CSS +
           '</style></head><body>' + ''.join(pages) + '</body></html>')
    html_path = OUT / '_booklet.html'
    html_path.write_text(doc, encoding='utf-8')
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=2, viewport={'width': 794, 'height': 1123})
        page.goto(html_path.as_uri())
        page.wait_for_timeout(1200)
        n = page.locator('.page').count()
        print('pages in DOM:', n)
        pdf = OUT / 'GrowthForward_学术图表册.pdf'
        page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
        # 零删除策略：册页 PNG 按固定文件名覆盖写，不清理目录，
        # 这样即便中途中断也不会丢失上一版完整交付物。
        # 命名：00 封面 / 01-02 目录 / 章扉页与图页按出现顺序编号 / 末页封底
        names = ['00_封面', '01_目录1', '02_目录2']
        cur = 3
        for ci, c in enumerate(CHAPTERS):
            names.append(f'{cur:02d}_扉页{c["no"]}')
            cur += 1
            for d in F:
                if d['chap'] == c['key']:
                    names.append(f'{cur:02d}_{d["no"].replace(" ", "")}')
                    cur += 1
        names.append(f'{cur:02d}_封底')
        W, H = 1588, 2246
        from io import BytesIO
        from PIL import Image
        for i, nm in enumerate(names):
            raw = page.locator('.page').nth(i).screenshot()
            im = Image.open(BytesIO(raw)).convert('RGB')
            if im.size != (W, H):
                canvas = Image.new('RGB', (W, H), 'white')
                canvas.paste(im.crop((0, 0, min(im.width, W), min(im.height, H))))
                im = canvas
            im.save(OUT / f'{nm}.png')
        browser.close()
    print('PDF:', pdf)
    print('PNG pages:', len(names), '| fixed canvas:', f'{W}x{H}')


if __name__ == '__main__':
    main()
