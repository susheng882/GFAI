# -*- coding: utf-8 -*-
"""一次性补丁：技术方案 md 新增 §1.4 竞品实证对比、§3.9 学习科学依据；产品报告 docx 追加两段实证/理论文字。"""
import shutil
import zipfile
from copy import deepcopy
from pathlib import Path

from lxml import etree

BASE = Path(r"F:\GrowthForward_AI学习伴侣")
MD = BASE / "技术方案_GrowthForward.md"
DOCX = BASE / "产品报告_GrowthForward_AI学习伴侣_V2完整版.docx"
BAK = BASE / "归档" / "_backup_report_before_competitor.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"


SEC14 = """### 1.4 已上线竞品实证对比（2026-11-14 官网实采，增补）

报告第二章按「类别」给过能力对比，价格只到量级。本节按**真实已上线产品**逐项复核，用于回答两个问题：这条需求是否已被验证、GFLC 的空白是否真实存在。所有价格采集于 2026-11-14 厂商官网或公开定价页，美元档未折算，采购前须以当期页面复核。

| # | 产品（厂商 / 上线状态） | 已上线的核心能力 | 公开定价（2026-11-14） | 相对 GFLC 的缺口 |
|---|---|---|---|---|
| 1 | Gemini Notebook（原 NotebookLM，Google，2026-07-16 更名） | 只依据用户上传资料作答并逐句给出引用；YouTube 字幕、PDF、网页、音频导入；闪卡、测验、思维导图、学习指南、Audio / Video Overviews、Deep Research；2026 起闪卡记录错题进度 | Free 100 笔记本 × 50 源；Google AI Plus $4.99/月、Pro $19.99/月、Ultra $99.99/月起 | 无间隔复习排程、无掌握度追踪；仅公开且有字幕的视频；无学习计划与错题回炉到原文 |
| 2 | 通义听悟（阿里云） | 音视频转写、说话人分离、章节速览 / 全文摘要 / 待办、PPT 页提取与时间轴对齐、思维导图、翻译、AI 问答 | 每日 2 小时免费；高级会员 ¥399/年；高校师生认证送 500 小时；API 转写 ¥0.6/小时 + AI 能力每项 ¥0.064/小时 | 产物止于纪要与摘要，不产出背诵卡片、组卷与复习计划；无学习状态记忆 |
| 3 | 飞书妙记（字节） | 会议转写、音字同步跳转、要点与待办、评论 @ 协作、同步飞书任务 | 免费 300 分钟/人/月；AI 高级会员 ¥69/月；企业版 ¥50–120/人/月 | 绑定飞书会议生态，不面向个人备考资料；无自有 PDF / 网课闭环 |
| 4 | Recall（海外，2026 在线） | YouTube 最长 10 小时、60+ 语言、无字幕自转录（5 小时）、摘要自动汇入知识图谱并关联概念；Plus 档含测验与间隔重复 | Free 10 次总结/月；Plus $10/月（年付）；Max $38/月 | 间隔重复是通用卡片，不接自有 PDF / 讲义产物；无时间戳溯源与掌握度驱动的重排 |
| 5 | NoteGPT | YouTube / PDF / 本地文件 → 摘要、转录、思维导图、闪卡、测验 | Free 约 15 credits/月；Pro $9.99/月；Unlimited 约 $19.92/月（年付） | 产物生成即结束；无计划、无掌握度、无错题回炉 |
| 6 | Eightify | YouTube 页内一键时间戳摘要，40+ 语言 | 免费 3 视频/周（≤30 min）；$4.95/月（年付约 $3.95/月） | 一次性摘要，无知识库、无复习、无学习数据沉淀 |
| 7 | BibiGPT | 30+ 平台（B 站 / YouTube / 抖音 / 播客 / 本地文件）视频总结 | 订阅制（含转录 + 总结） | 止于总结，无学习闭环 |
| 8 | Anki（FSRS-6） | 间隔重复算法标杆；2025-07 起默认 FSRS-6（基于约 7 亿次复习训练，同等保持率下比 SM-2 少 20%–30% 复习量） | 桌面 / Android 免费；iOS $24.99 一次性 | 卡片需自制或导入，不承担素材解析；不接视频 / PDF 原文 |
| 9 | RemNote | 笔记自动转 SRS 卡片、考试排程、PDF 标注 | 免费档含完整 SRS；Pro $8/月（年付 $96）或 $10/月 | 不解析网课视频与讲义原文；无时间戳溯源、无掌握度可解释输出 |
| 10 | Quizlet | 社区卡库、Learn 模式、AI 测验 | Free；Plus $7.99/月或 $35.99/年 | 算法偏短周期记忆，长期保持弱；不接自有资料 |
| 11 | BiliNote（开源，v2.4.4，MIT） | 视频 → 结构化笔记、时间戳跳转、Chroma 双索引 RAG 问答（详见 3.6） | 免费自部署 | 无复习卡片、学习计划、掌握度与错题闭环 |

**实证结论三条**：
1. **上半场已被充分验证**——「音视频 / 文档 → 结构化产物」至少有 7 款在线收费产品，价格带集中在 $0–20/月或 ¥399/年，说明这是真实付费需求，GFLC 不需要教育市场。
2. **下半场只有半个**——间隔重复由 Anki / RemNote / Recall 触及，但都不接收「用户自有视频与 PDF 解析出的结构化知识单元」；NotebookLM 与 NoteGPT 生成闪卡却不排程、不追踪掌握度。
3. **GFLC 的差异化不是功能数量，而是数据链**——把「自有资料 → 结构化产物 → 时间戳溯源 → 复习调度 → 掌握度 → 错题回炉」串成同一条可验证闭环；报告第二章的「空白」判断在 2026-11 的实证下依然成立，且更具体。

口径说明：Gemini Notebook 无独立订阅，价格随 Google AI 套餐；飞书妙记企业版为区间报价；美元档按厂商当地页面，未做汇率折算；新客 / 学生优惠与续费价差异见 5.8。图表化对照见 **图 1-1（能力矩阵）** 与 **图 1-2（实证产品与定价）**。

"""


SEC39 = """### 3.9 功能设计的学习科学依据（2026-11-14 增补，增补）

功能清单（报告第四章 38 项）此前只写「做什么」，缺「为什么这样做」。本节把每个关键设计决策锚定到可检索的学习科学文献与可落地的参数，答辩时可逐条追溯；图表化映射见 **图 4-2（遗忘曲线理论）** 与 **图 4-3（功能—理论矩阵）**。

| 功能 / 参数 | 设计理论 | 经典文献与关键数据 | 在本项目中的落地 |
|---|---|---|---|
| 复习点 R1–R4 = 1/3/7/14 天 | 遗忘曲线 + 间隔效应 | Ebbinghaus (1885)：无复习时 24 h 内约损失 70% 新信息；Cepeda et al. (2006), *Psychological Bulletin* 132(3): 354–380，254 项研究元分析确认分散练习优于集中练习 | 初始复习序列；每次成功复习抬升记忆强度 S，间隔按 S 反推递增 |
| 背诵卡片「先问后答」、错题回炉重讲解 | 测试效应 / 检索练习 | Roediger & Karpicke (2006), *Psychological Science* 17(3): 249–255：1 周后主动回忆保持率约 80%，重复阅读约 34%；Adesope et al. (2017) 元分析复核 | 卡片默认隐藏答案；回炉不是重看答案，而是经 pgvector 回原文重新检索并生成新讲解 |
| 掌握度 m ∈ [0,1] 与可解释低分依据 | 贝叶斯知识追踪（BKT） | Corbett & Anderson (1994), *UMUAI* 4(4): 253–278 | 由作答结果、间隔、题目难度三因子更新；低分必须给出「哪个知识点 / 哪次答错」 |
| 三类笔记（文稿 / 大纲 / 图文） | 认知负荷理论 | Sweller (1988), *Cognitive Science* 12(2): 257–285：内在 / 外在 / 相关负荷三分 | 速览用大纲降外在负荷，精读用文稿，图文笔记控制单屏信息密度 |
| 图文笔记 + 原片时间戳跳转 | 双重编码 / 多媒体学习 | Paivio (1986)；Mayer (2009), *Multimedia Learning* 2nd ed. | 文字 + 视觉双通道编码同一概念，并附可点击的原片定位 |
| 单卡一知识点、按 H2/H3 切块 | 工作记忆容量约束 | Miller (1956) 7±2；Cowan (2001), *BBS* 24(1): 87–114，约 4 个组块 | 知识单元切块上限与卡片原子化，避免一卡多考点 |
| 复习点在「将忘未忘」时触发 | 合意困难 | Bjork & Bjork (2011) | 目标保持率 0.90；θ=0.85 以下触发回炉，不提前也不拖后 |
| 计划重排：低掌握度优先 | 高效用学习策略排序 | Dunlosky et al. (2013), *PSPI* 14(1): 4–58：练习测试与分散练习为最高效用 | 每日待学清单按 mastery 升序 + 截止日双权重排序 |
| 固定倍率 → 个体化间隔（V1.5 评估） | SM-2 / FSRS | Wozniak (1987) SM-2；Anki 自 2025-07 起默认 FSRS-6，同等保持率少 20%–30% 复习量 | 主线先用可解释的 1/3/7/14 天 + 阈值策略；样本足够后评估切换 |
| 仪表盘三曲线（掌握度 / 完成率 / 成本） | 元认知与反馈 | Brown, Roediger & McDaniel (2014), *Make It Stick*：加工流畅性会造成「已学会」错觉 | 用可核验的行为数据替代主观熟练感，避免错误知识被反复强化 |

**遗忘曲线的具体设计理论（图 4-2 的推导链）**：

1. **指数遗忘模型**：`R(t) = e^(−t/S)`，`R` 为保持率、`t` 为距上次复习的天数、`S` 为记忆强度（稳定性）。Ebbinghaus 原始曲线在 20 min–31 d 的实测呈快速衰减后趋平；无复习时约 24 h 后 `R ≈ 0.3`。
2. **SM-2 递推**（Wozniak, 1987）：`I(1)=1, I(2)=6, I(n)=I(n−1)×EF`；每次作答质量 `q∈[0,5]` 更新难度因子 `EF′ = EF + 0.1 − (5−q)·(0.08 + 0.02·(5−q))`，并设下限 1.3；答错则间隔归 1 重新开始。优点是零样本可跑，缺点是对所有人都用同一套倍率。
3. **FSRS 可检索性模型**（Anki 2025 起默认）：以难度 D、稳定性 S、可检索性 R 三变量建模，`R(t,S) = (1 + F·t/S)^(−C)`；给定目标保持率 `R* = 0.90` 可反解下次最优间隔 `t* = (S/F)·(R*^(−1/C) − 1)`，参数由用户自身复习历史拟合。
4. **本项目的参数化取舍**：主线采用「固定初始序列 + 可解释掌握度」而非直接上 FSRS——单人项目在冷启动阶段没有足够复习日志做参数拟合，先把 `R1–R4 = 1/3/7/14 d`、`θ=0.85`、`R*=0.90` 写成可配置常量，并把每次 `review_logs` 落库；V1.5 在日志量达到可拟合规模后，用同一批数据 A/B 验证 FSRS（报告第七章（三）的验收口径：≥50 用户、每人 ≥200 次复习、≥4 周，目标保持率相对固定间隔提升 10–15 pp，不显著则回退）。
5. **回炉的语义**：`R(t) < θ` 时不是把同一张卡再推一遍，而是关联 `knowledge_units` → pgvector 检索原始时间戳 → 重新生成讲解与新卡片，同时 `S` 减半。依据是检索练习效应，且时间戳为 P0 硬字段，保证回炉链路可验证。

"""


def patch_md():
    s = MD.read_text(encoding="utf-8")
    assert "### 1.4 已上线竞品实证对比" not in s, "md already patched"
    s = s.replace("1.1 已锁定约定 · 1.2 硬约束 · 1.3 与报告差异",
                  "1.1 已锁定约定 · 1.2 硬约束 · 1.3 与报告差异 · 1.4 已上线竞品实证对比")
    s = s.replace("· [3.8 NL 问数仪表盘](#38-nl-问数仪表盘p2-增强2026-11-14-增补)",
                  "· [3.8 NL 问数仪表盘](#38-nl-问数仪表盘p2-增强2026-11-14-增补) · 3.9 功能设计的学习科学依据")
    assert "\n## 2. 技术框架选型\n" in s and "\n## 4. 测试体系\n" in s
    s = s.replace("\n## 2. 技术框架选型\n", "\n" + SEC14 + "---\n\n## 2. 技术框架选型\n", 1)
    s = s.replace("\n## 4. 测试体系\n", "\n" + SEC39 + "---\n\n## 4. 测试体系\n", 1)
    MD.write_text(s, encoding="utf-8")
    print("md patched:", len(SEC14), len(SEC39), "chars")


PARA_COMPETITOR = (
    "2026 年 11 月 14 日按厂商官网与公开定价页对已上线产品逐项复核，结论是「上半场拥挤、下半场空白」。"
    "视频与文档总结一侧已有 Google Gemini Notebook（原 NotebookLM，2026 年 7 月更名，免费 100 笔记本 × 50 源，"
    "AI Plus 4.99 美元/月、Pro 19.99 美元/月）、阿里云通义听悟（每日 2 小时免费，高级会员 399 元/年，"
    "API 转写 0.6 元/小时）、字节飞书妙记（免费 300 分钟/月，AI 高级会员 69 元/月）、Recall（免费 10 次总结/月，"
    "Plus 10 美元/月）、NoteGPT（Pro 9.99 美元/月）、Eightify（4.95 美元/月）与 BibiGPT 等，"
    "均能把音视频或 PDF 转成摘要、章节、闪卡或思维导图。复习调度一侧有 Anki（桌面与 Android 免费，"
    "2025 年 7 月起默认 FSRS-6）、RemNote（Pro 8 美元/月）与 Quizlet（Plus 7.99 美元/月），算法成熟但卡片需自制或导入。"
    "两侧之间仍缺一段：Recall 的间隔重复是通用卡片，不接自有 PDF 讲义与时间溯源；Gemini Notebook 的闪卡不排程、"
    "不追踪掌握度；通义听悟与飞书妙记的产物止于纪要。GFLC 的差异化不是功能数量，"
    "而是把「自有资料 → 结构化产物 → 溯源定位 → 复习调度 → 掌握度 → 错题回炉」用同一条数据链串成可验证闭环。"
    "逐项报价与能力矩阵见图 1-1、图 1-2 与技术方案 1.4 节。"
)

PARA_THEORY = (
    "上述调度策略的学习科学依据需明确到文献与参数，避免把经验规则当作结论。遗忘曲线取自 Ebbinghaus（1885）"
    "的指数遗忘模型 R(t)=e^(−t/S)，无复习时 24 小时内约损失七成新信息；间隔效应由 Cepeda 等（2006，"
    "Psychological Bulletin 132(3)，254 项研究元分析）确认分散练习显著优于集中练习，"
    "本项目据此设初始复习点 R1 至 R4 为 1/3/7/14 天。卡片「先问后答」依据测试效应："
    "Roediger 与 Karpicke（2006，Psychological Science 17(3): 249–255）测得一周后主动回忆保持率约八成、"
    "重复阅读约三成四，故回炉动作设计为重新检索原文并生成新讲解而非重看答案。三类笔记分别对应 Sweller（1988）"
    "认知负荷理论的内在、外在、相关负荷管理，图文笔记与时间戳跳转对应 Paivio（1986）双重编码与 Mayer（2009）"
    "多媒体学习；单卡一知识点、按 H2/H3 切块对应 Cowan（2001）工作记忆约四个组块的容量约束；"
    "复习点在「将忘未忘」时触发对应 Bjork 与 Bjork（2011）合意困难；掌握度以贝叶斯知识追踪"
    "（Corbett 与 Anderson，1994）为先验，由正确率、间隔、难度三因子更新，并要求输出可解释的低分依据。"
    "固定倍率调度参考 SM-2（Wozniak，1987），V1.5 再评估按个体保持率反解间隔的 FSRS 路线"
    "（Anki 自 2025 年 7 月起默认 FSRS-6，同等保持率下复习量减少两至三成）。"
    "完整「理论—功能—参数」映射见技术方案 3.9 节与图 4-2、图 4-3。"
)


def insert_after(anchor, text):
    np = etree.Element(W + "p")
    ppr = anchor.find(W + "pPr")
    if ppr is not None:
        np.append(deepcopy(ppr))
    r = etree.SubElement(np, W + "r")
    t = etree.SubElement(r, W + "t")
    t.set(XML_SPACE, "preserve")
    t.text = text
    anchor.addnext(np)
    return np


def patch_docx():
    BAK.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DOCX, BAK)
    z = zipfile.ZipFile(DOCX)
    items = [(i, z.read(i.filename)) for i in z.infolist()]
    z.close()
    raw = [b for n, b in items if n.filename == "word/document.xml"][0]
    root = etree.fromstring(raw)
    paras = list(root.iter(W + "p"))

    def find(prefix):
        for p in paras:
            t = "".join(n.text or "" for n in p.iter(W + "t")).strip()
            if t.startswith(prefix):
                return p
        raise RuntimeError("anchor not found: " + prefix)

    a1 = find("对照可见，GFLC 在复习算法上弱于 Anki")
    a2 = find("这是一个可验证的差异点")
    insert_after(a1, PARA_COMPETITOR)
    insert_after(a2, PARA_THEORY)

    new_doc = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as out:
        for info, data in items:
            out.writestr(info, new_doc if info.filename == "word/document.xml" else data)

    z2 = zipfile.ZipFile(DOCX)
    r2 = etree.fromstring(z2.read("word/document.xml"))
    print("docx patched | bookmarks",
          len(list(r2.iter(W + "bookmarkStart"))), len(list(r2.iter(W + "bookmarkEnd"))),
          "| tables", len(list(r2.iter(W + "tbl"))),
          "| fldChar", len(list(r2.iter(W + "fldChar"))),
          "| w14 in nsmap", "w14" in r2.nsmap,
          "| Ignorable", r2.get("{http://schemas.openxmlformats.org/markup-compatibility/2006}Ignorable"))
    txt = "".join(n.text or "" for n in r2.iter(W + "t"))
    for k in ["Gemini Notebook", "Ebbinghaus", "图 1-2", "图 4-3", "Corbett"]:
        print("  contains", k, "->", k in txt)


if __name__ == "__main__":
    patch_md()
    patch_docx()
