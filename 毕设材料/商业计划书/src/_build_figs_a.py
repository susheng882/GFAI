# -*- coding: utf-8 -*-
"""生成重点学术图 A 组：图 1-1 / 1-2 / 4-2 / 4-3 / 5-3（统一 680×960 画布）。"""
from pathlib import Path
from _figlib import *

ROOT = Path(__file__).parent
X0, CW = 24, 632


def fig_1_1():
    b = []
    b.append(t(X0, 78, "A　已上线产品能力矩阵（● 完整支持　○ 部分支持　— 不提供；能力口径以主力使用场景为准）", 9, weight="bold"))
    headers = ["产品（已上线）|厂商 / 状态", "多模态|资料解析", "结构化|知识产物", "时间戳|溯源定位", "间隔复习|计划调度", "掌握度|错题回炉", "公开定价|2026-11-14"]
    widths = [166, 62, 62, 62, 62, 62, 156]
    rows = [
        ["Gemini Notebook|Google · 2023 上线 / 2026 更名", "○", "●", "●", "—", "—", "Free｜AI Plus $4.99 / Pro $19.99 月"],
        ["通义听悟|阿里云 · 商用在线", "●", "○", "○", "—", "—", "每日 2 h 免费｜¥399/年"],
        ["飞书妙记|字节 · 商用在线", "●", "○", "○", "—", "—", "免费 300 min/月｜¥69/月"],
        ["Recall|海外 · 2026 在线", "●", "●", "●", "○", "—", "Free 10 次/月｜Plus $10/月"],
        ["NoteGPT|海外 · 商用在线", "●", "●", "—", "—", "—", "Free 15 额度/月｜Pro $9.99/月"],
        ["Eightify|海外 · 商用在线", "○", "○", "●", "—", "—", "免费 3 视频/周｜$4.95/月"],
        ["BibiGPT|国内 · 商用在线", "●", "○", "○", "—", "—", "订阅制（含转录 + 总结）"],
        ["Anki (FSRS-6)|开源 · 2025-07 起默认", "—", "—", "—", "●", "○", "桌面/Android 免费｜iOS $24.99"],
        ["RemNote|海外 · 商用在线", "—", "○", "—", "●", "○", "Free 含完整 SRS｜Pro $8/月"],
        ["Quizlet|海外 · 商用在线", "—", "○", "—", "○", "—", "Free｜Plus $7.99/月"],
        ["BiliNote v2.4.4|开源 · MIT（参照系）", "●", "●", "●", "—", "—", "免费自部署"],
        ["GFLC（本项目）★|毕业设计 · V1.0 主线", "●", "●", "●", "●", "●", "月付 ¥12｜年付 ¥99"],
    ]
    fills = [None] * 11 + ["#E7F2F8"]
    tb, hh = table(X0, 86, widths, headers, rows, header_h=34, row_h=37,
                   font=7.7, header_font=7.4, fills=fills)
    b.append(tb)
    y = 86 + hh + 12
    b.append(t(X0, y, "B　由实证矩阵导出的三条结论", 9, weight="bold"))
    y += 8
    cards = [
        ("上半场已被验证", ["7 款以上在线收费产品把音视频 / PDF", "转为摘要、章节、闪卡；价格带", "$0–20/月 或 ¥399/年 —— 真实付费需求"], "video"),
        ("下半场只做了一半", ["Anki / RemNote / Recall 有间隔重复，", "但都不接收「自有资料解析出的", "知识单元」；NotebookLM 出卡不排程"], "clock"),
        ("差异化是数据链", ["解析 → 产物 → 溯源 → 调度 →", "掌握度 → 回炉 串成同一条闭环；", "逐跳带时间戳，可现场演示验证"], "loop"),
    ]
    for i, (title, lines, ic) in enumerate(cards):
        b.append(box(X0 + i * 212, y, 204, 84, title, lines, fill="#F3FAFD", icon_name=ic, tsize=8.8, lsize=7.4))
    y += 96
    b.append(r(X0, y, CW, 82, "#FBFDFE", "#9AAAB3", 0.8, "5 3"))
    notes = [
        "注 1：采集口径为 2026-11-14 厂商官网 / 公开定价页；Gemini Notebook 无独立订阅，价格随 Google AI 套餐；美元档未折算。",
        "注 2：「○」表示需插件、人工或仅覆盖部分链路，例如 Recall 的间隔重复为通用卡片、飞书妙记为音字同步跳转而非知识点溯源。",
        "注 3：Anki 自 2025-07 起默认 FSRS-6，基于约 7 亿次复习训练，同等保持率下比 SM-2 减少 20%–30% 复习量。",
        "注 4：GFLC 的「●」以产品报告第四章 38 项功能全景清单与技术方案 3.7 集成核对表为据，溯源跳转为 P0 硬字段。",
    ]
    for i, s in enumerate(notes):
        b.append(t(X0 + 12, y + 18 + i * 17, s, 8.0, fill="#2B3237"))
    b.append(t(X0, y + 94, "数据源：产品报告第二章（二）（四）· 技术方案 1.4 节 · 图 1-2 定价对照", 8.2, fill=GREY))
    y4 = y + 104
    b.append(r(X0, y4, CW, 62, "#F3FAFD", INK, 0.8))
    b.append(icon("eye", X0 + 10, y4 + 8, 0.7))
    b.append(t(X0 + 34, y4 + 20, "实证复核方法与数据来源", 8.8, weight="bold"))
    b.append(t(X0 + 12, y4 + 38, "采集路径：厂商官网定价页 / 官方帮助中心 / 2026 年第三方定价复核页；能力判定以产品主力使用场景为准，", 7.8))
    b.append(t(X0 + 12, y4 + 53, "跨类能力以「是否需插件或人工」为 ○／● 分界；所有条目均标注上线状态，未上线或仅内测的产品不纳入本矩阵。", 7.8))
    return frame("已上线产品实证对比与 GFLC 差异化定位矩阵",
                 "第一章 · 11 款真实上线产品 × 5 项核心能力 · 2026-11-14 官网实采",
                 "\n".join(b),
                 "● 完整支持　○ 部分支持　— 不提供　★ 本项目　◆ 2026-11 复核新增　·　逐项报价见技术方案 1.4",
                 "图 1-1　已上线产品实证对比与差异化定位矩阵",
                 "Fig. 1-1　Empirical comparison of launched products and GFLC positioning matrix",
                 tag="GFLC · 2026")


def fig_1_2():
    b = []
    b.append(t(X0, 78, "A　公开定价对照（折算为元/月，仅作量级比较）", 9, weight="bold"))
    items = [
        ("Eightify", 36, "$4.95/月"), ("通义听悟", 33, "¥399/年"), ("Quizlet Plus", 58, "$7.99/月"),
        ("RemNote Pro", 58, "$8/月"), ("NoteGPT Pro", 72, "$9.99/月"), ("Recall Plus", 72, "$10/月"),
        ("飞书妙记 AI", 69, "¥69/月"), ("Gemini Pro", 144, "$19.99/月"), ("GFLC 年付", 8.25, "¥99/年"),
        ("GFLC 月付", 12, "¥12/月"),
    ]
    bx, by, bw = 92, 100, 190
    b.append(r(X0, 88, 316, 300, "#FFFFFF", INK, 1))
    for i, (name, val, raw) in enumerate(items):
        yy = 100 + i * 27
        b.append(t(X0 + 6, yy + 9, name, 7.6))
        w = val / 150 * bw
        fill = RED if name.startswith("GFLC") else "#83949E"
        b.append(r(bx, yy, w, 11, fill, None, 0))
        b.append(t(bx + w + 4, yy + 9, raw, 7.0, fill="#3C464D"))
    b.append(ln(bx, 372, bx, 96, "#BED3DE", 0.6))
    b.append(t(X0 + 6, 382, "美元按 1 USD ≈ ¥7.2 折算，仅供量级对照；★ 红色为本项目", 7.2, fill=GREY))

    b.append(t(356, 78, "B　能力覆盖热图（六款代表产品）", 9, weight="bold"))
    cols = ["解析", "产物", "溯源", "复习", "掌握度"]
    prods = ["Gemini NB", "通义听悟", "Recall", "NoteGPT", "Anki", "GFLC ★"]
    vals = [
        [1, 2, 2, 0, 0], [2, 1, 1, 0, 0], [2, 2, 2, 1, 0],
        [2, 2, 0, 0, 0], [0, 0, 0, 2, 1], [2, 2, 2, 2, 2],
    ]
    gx, gy, cw2, rh = 356, 104, 47, 38
    b.append(r(gx, 88, 300, 300, "#FFFFFF", INK, 1))
    for j, c in enumerate(cols):
        b.append(t(gx + 58 + j * cw2 + cw2 / 2, 100, c, 7.4, "middle", "bold"))
    for i, p in enumerate(prods):
        yy = gy + i * rh
        b.append(t(gx + 6, yy + 20, p, 7.6, weight="bold" if i == 5 else ""))
        for j, v in enumerate(vals[i]):
            xx = gx + 58 + j * cw2
            fill = INK if v == 2 else ("#BED3DE" if v == 1 else "#FFFFFF")
            b.append(r(xx, yy + 4, cw2 - 4, 28, fill, "#9AAAB3", 0.5))
            mark = "●" if v == 2 else ("○" if v == 1 else "—")
            b.append(t(xx + (cw2 - 4) / 2, yy + 23, mark, 10, "middle", "bold", "#FFFFFF" if v == 2 else INK))
    b.append(t(gx + 6, 378, "深＝完整　灰＝部分　白＝不提供　·　GFLC 是唯一满行", 7.2, fill=GREY))

    b.append(t(X0, 404, "C　价格带与空白定位（由 A、B 两区交叉读出）", 9, weight="bold"))
    b.append(box(X0, 414, 204, 96, "工具层 $0–20/月", ["总结类产品定价高度收敛；", "同质化在「生成即结束」——", "无状态、无复习、无迁移成本"], fill="#F3FAFD", icon_name="coin", tsize=8.8))
    b.append(box(X0 + 212, 414, 204, 96, "算法层 免费 / $8–10/月", ["Anki / RemNote 算法成熟，", "但卡片需自制，不承担从", "原始素材到知识单元的加工"], fill="#F3FAFD", icon_name="clock", tsize=8.8))
    b.append(box(X0 + 424, 414, 208, 96, "GFLC 的交叉空白", ["¥8.25–12/月落在最低价格带，", "却覆盖 5 项能力；壁垒来自", "闭环数据资产而非模型能力"], fill="#F0F8FC", icon_name="target", tsize=8.8))

    b.append(t(X0, 528, "D　实证复核要点（答辩可逐条追溯）", 9, weight="bold"))
    rows = [
        ["① 需求验证", "7 款以上在线收费产品集中在「音视频 / 文档 → 结构化产物」，说明付费需求已被市场验证，无需教育用户。"],
        ["② 空白验证", "间隔重复只有 Anki / RemNote / Recall 触及，且均不接收自有视频与 PDF 解析产物，亦无时间戳溯源回炉。"],
        ["③ 定价验证", "GFLC 年付 ¥99（≈¥8.25/月）低于全部订阅型竞品，成本依据见技术方案 5.8 与图 5-3、图 5-4。"],
        ["④ 风险复核", "大厂可能内置学习模式（产品报告 SWOT 的 T 项）；对策是数据资产 + 流程细节 + 产物可导出。"],
    ]
    tb, hh = table(X0, 538, [104, 528], ["要点", "实证结论与文档落点"], rows,
                   header_h=28, row_h=44, font=8.0, zebra=True)
    b.append(tb)
    y = 538 + hh + 12
    b.append(r(X0, y, CW, 80, "#FBFDFE", "#9AAAB3", 0.8, "5 3"))
    for i, s in enumerate([
        "注 1：价格采集于 2026-11-14；活动价 / 新客 / 学生优惠与续费价差异显著，采购前须以厂商当期页面复核。",
        "注 2：Gemini Notebook 为 Google AI 套餐附赠能力，无独立订阅；免费档 100 笔记本 × 50 源已覆盖学期用量。",
        "注 3：本图与图 1-1 为同一组实证数据的两种视图（能力矩阵 / 定价与覆盖），配套技术方案 1.4 节。",
    ]):
        b.append(t(X0 + 12, y + 20 + i * 19, s, 8.2, fill="#2B3237"))
    return frame("已上线竞品定价对照与能力覆盖分析",
                 "第一章 · 价格带 × 能力热图 × 交叉空白 · 2026-11-14 实采",
                 "\n".join(b),
                 "■ 折算月价（深色＝本项目）　● 完整　○ 部分　— 不提供　·　数据出处：技术方案 1.4 / 5.8",
                 "图 1-2　已上线竞品定价对照与能力覆盖分析",
                 "Fig. 1-2　Pricing benchmark and capability coverage of launched competitors",
                 tag="GFLC · 2026")


def fig_4_2():
    b = []
    b.append(t(X0, 78, "A　遗忘曲线与复习抬升（理论模型 → 本项目参数）", 9, weight="bold"))
    # 坐标图
    b.append(r(X0, 88, 392, 268, "#FFFFFF", INK, 1))
    ax, ay, aw, ah = 60, 108, 330, 210
    b.append(ln(ax, ay + ah, ax + aw, ay + ah, INK, 1))
    b.append(ln(ax, ay, ax, ay + ah, INK, 1))
    b.append(t(ax + 4, ay - 4, "保持率 R(t)", 7.4, fill=GREY))
    # 横轴单位右对齐收在 R4 刻度右侧，避免与「R4/14 d」标签重叠或越出框右界
    b.append(t(ax + aw + 22, ay + ah + 14, "t / d", 7.4, "end", fill=GREY))
    for i, lab in enumerate(["1.0", "0.8", "0.6", "0.4", "0.2", "0"]):
        yy = ay + i * (ah / 5)
        b.append(ln(ax - 3, yy, ax, yy, INK, 0.6))
        b.append(t(ax - 6, yy + 3, lab, 7, "end", fill=GREY))
    # 无复习衰减曲线
    # 无复习衰减曲线：终点严格收在横轴（y=ay+ah=318）上方，不再穿轴出绘图区
    b.append(path("M 60,108 C 95,220 140,278 210,299 C 280,311 350,315 390,316", INK, 1.6))
    # 复习抬升曲线簇
    b.append(path("M 60,108 C 78,160 90,200 100,214 L 100,120 C 118,180 140,214 166,228 L 166,126 C 190,186 215,222 246,236 L 246,130 C 275,188 305,226 330,240 L 330,132 C 352,184 370,220 390,232",
                  INK, 1.2, dash="4 3"))
    for xx, lab, dy in [(100, "R1 · 1 d", 22), (166, "R2 · 3 d", 22), (246, "R3 · 7 d", 22), (330, "R4 · 14 d", 22)]:
        b.append(ln(xx, ay, xx, ay + ah, "#BED3DE", 0.6, "3 3"))
        b.append(path(f"M {xx},120 L {xx},318", "#DCEBF2", 0.6))
        b.append(t(xx, ay + ah + 14, lab.replace(" · ", "/"), 7, "middle", fill=GREY))
        b.append(circ(xx, 120, 2.4, INK))
    b.append(ln(ax, ay + ah * 0.10, ax + aw, ay + ah * 0.10, "#83949E", 0.8, "4 3"))
    # 阈值标注加浅底，避免压在 R4 回升虚线上导致文字不可读
    b.append('<rect x="288" y="113" width="104" height="14" fill="#FFFFFF" opacity="0.92"/>')
    b.append(t(ax + aw - 2, ay + ah * 0.10 - 4, "目标保持率 R*=0.90", 7.2, "end", fill="#4E5A62"))
    b.append(ln(ax, ay + ah * 0.15, ax + aw, ay + ah * 0.15, RED, 0.9, "4 3"))
    b.append('<rect x="304" y="140" width="88" height="14" fill="#FFFFFF" opacity="0.92"/>')
    b.append(t(ax + aw - 2, ay + ah * 0.15 + 11, "回炉阈值 θ=0.85", 7.2, "end", fill=RED))
    b.append(t(X0 + 8, 348, "无复习曲线 R(t)=e^(−t/S)；每次成功复习抬升起点并增大 S；R(t)<θ 触发回炉，S 减半。", 7.6, fill="#3C464D"))

    # 公式框
    b.append(t(428, 78, "B　三代调度模型与公式", 9, weight="bold"))
    fboxes = [
        ("① 指数遗忘　Ebbinghaus 1885", ["R(t) = e^(−t/S)", "24 h 后 R≈0.3（约损失 70%）", "S = 记忆强度 / 稳定性"], "brain"),
        ("② SM-2　Wozniak 1987", ["I(1)=1, I(2)=6, I(n)=I(n−1)·EF", "EF′=EF+0.1−(5−q)(0.08+0.02(5−q))", "EF 下限 1.3；答错间隔归 1"], "clock"),
        ("③ FSRS　Anki 2025-07 默认", ["R(t,S)=(1+F·t/S)^(−C)", "t*=(S/F)(R*^(−1/C)−1)", "D/S/R 三参数由历史拟合"], "gear"),
    ]
    for i, (title, lines, ic) in enumerate(fboxes):
        yy = 88 + i * 90
        b.append(box(428, yy, 228, 82, title, lines, fill="#F3FAFD", icon_name=ic, tsize=8.2, lsize=7.2))
    b.append(t(428, 366, "◆ 本项目主线用可解释的 ①+②，V1.5 评估 ③", 7.8, fill=RED))

    # 参数表
    b.append(t(X0, 372, "C　参数化取舍（全部写成可配置常量，落库可回溯）", 9, weight="bold"))
    rows = [
        ["R1 / R2 / R3 / R4", "1 / 3 / 7 / 14 天", "Cepeda et al. (2006) 间隔效应 + 备考周期间隔递增的初始序列"],
        ["目标保持率 R*", "0.90", "FSRS 默认目标；低于此值即安排下一次复习"],
        ["回炉阈值 θ", "0.85", "mastery(t) < θ 触发错题回炉，并令 S ← S/2"],
        ["难度因子 EF", "初值 2.5，下限 1.3", "SM-2 原值；q∈[0,5] 为作答质量，半对按 q=3 计入"],
        ["掌握度 mastery(t)", "正确率 × 间隔 × 难度三因子", "BKT 先验；低分必须输出「哪个知识点 / 哪次答错」依据"],
        ["拟合与 A/B 验收", "≥50 用户 · ≥200 次/人 · ≥4 周", "目标保持率相对固定间隔提升 10–15 pp，不显著则回退 FSRS 基线"],
    ]
    tb, hh = table(X0, 382, [128, 150, 354], ["参数", "取值", "依据与落地口径"], rows,
                   header_h=26, row_h=34, font=7.8, aligns=["start", "middle", "start"])
    b.append(tb)

    # 文献表
    y = 382 + hh + 12
    b.append(t(X0, y, "D　设计理论的文献依据（答辩可逐条追溯）", 9, weight="bold"))
    rows2 = [
        ["遗忘曲线 / 间隔效应", "Ebbinghaus (1885)；Cepeda et al. (2006), Psychological Bulletin 132(3): 354–380（254 项元分析）", "R1–R4 序列"],
        ["测试效应 / 检索练习", "Roediger & Karpicke (2006), Psychological Science 17(3): 249–255（1 周后 80% vs 34%）", "回炉重讲解"],
        ["认知负荷 / 双重编码", "Sweller (1988), Cognitive Science 12(2): 257–285；Paivio (1986)；Mayer (2009)", "三类笔记 / 图文"],
        ["工作记忆容量", "Cowan (2001), BBS 24(1): 87–114（约 4 组块）；Miller (1956) 7±2", "单卡一知识点"],
        ["合意困难 / 高效用策略", "Bjork & Bjork (2011)；Dunlosky et al. (2013), PSPI 14(1): 4–58", "将忘未忘触发"],
        ["知识追踪 / 元认知", "Corbett & Anderson (1994), UMUAI 4(4): 253–278；Brown et al. (2014) Make It Stick", "掌握度可解释"],
    ]
    tb2, hh2 = table(X0, y + 10, [120, 400, 112], ["理论", "经典文献与关键数据", "落地为"], rows2,
                     header_h=24, row_h=28, font=7.4, aligns=["start", "start", "middle"])
    b.append(tb2)
    yy = y + 10 + hh2 + 12
    b.append(t(X0, yy, "注：固定倍率调度零样本可跑，单人项目冷启动阶段无足够日志拟合 FSRS；先落库 review_logs，样本达标后再 A/B 切换（技术方案 3.9）。", 7.8, fill="#3C464D"))
    return frame("遗忘曲线设计理论与间隔复习调度参数推导",
                 "第四章 · 指数遗忘 / SM-2 / FSRS 三代模型 · 公式—文献—参数全链可追溯",
                 "\n".join(b),
                 "实线 无复习衰减　虚线 复习抬升　朱红 θ 阈值　·　数据出处：技术方案 3.9 · 产品报告第七章（三）",
                 "图 4-2　遗忘曲线设计理论与间隔复习调度参数推导",
                 "Fig. 4-2　Forgetting-curve theory and derivation of spaced-review scheduling parameters",
                 tag="GFLC · 2026")


def fig_4_3():
    b = []
    b.append(t(X0, 78, "A　38 项功能的设计理论依据矩阵（每行给出「为什么这样做」）", 9, weight="bold"))
    headers = ["功能模块|（含图标）", "设计理论", "经典文献与关键数据", "落地参数 / 验收口径"]
    widths = [140, 112, 226, 154]
    rows = [
        ["复习点 R1–R4|间隔复习调度", "遗忘曲线·间隔效应", "Ebbinghaus 1885；Cepeda et al. 2006（254 项元分析）", "1/3/7/14 天；R*=0.90"],
        ["背诵卡片 / 先问后答|PDF 解析产物", "测试效应·检索练习", "Roediger & Karpicke 2006：1 周 80% vs 重读 34%", "默认隐藏答案；回炉重讲解"],
        ["掌握度 m 与低分依据|学习伴侣", "贝叶斯知识追踪 BKT", "Corbett & Anderson 1994, UMUAI 4(4)", "三因子更新；低分可解释"],
        ["三类笔记|文稿 / 大纲 / 图文", "认知负荷理论", "Sweller 1988：内在 / 外在 / 相关负荷", "速览降外在负荷；单屏控密度"],
        ["图文笔记 + 时间戳跳转|多模态视频解析", "双重编码·多媒体学习", "Paivio 1986；Mayer 2009 Multimedia Learning", "文字 + 视觉双通道；P0 硬字段"],
        ["知识单元切块 / 单卡一考点|内容解析链路", "工作记忆容量约束", "Cowan 2001 约 4 组块；Miller 1956 7±2", "按 H2/H3 切块；卡片原子化"],
        ["复习触发时机|计划重排", "合意困难", "Bjork & Bjork 2011", "将忘未忘触发；θ=0.85"],
        ["低掌握度优先排程|可拖拽仪表盘", "高效用学习策略排序", "Dunlosky et al. 2013：练习测试 / 分散练习最高", "mastery 升序 + 截止日双权重"],
        ["三曲线反馈|掌握度 / 完成率 / 成本", "元认知与反馈闭环", "Brown, Roediger & McDaniel 2014：流畅性错觉", "用行为数据替代主观熟练感"],
        ["FSRS 个体化间隔（V1.5）|迭代规划", "SM-2 → FSRS 演进", "Wozniak 1987；Anki 2025-07 默认 FSRS-6", "少 20–30% 复习量；A/B 验收"],
    ]
    tb, hh = table(X0, 88, widths, headers, rows, header_h=30, row_h=56,
                   font=7.5, header_font=7.6, aligns=["start", "start", "start", "start"])
    b.append(tb)
    # 图标叠加在第一列每行左侧（表格第一列文字 x+6 起，改为图标 + 文字右移）
    # 重新画一列遮罩再写文字，避免重叠
    for i in range(len(rows)):
        yy = 88 + 30 + i * 56
        b.append(r(X0 + 1, yy + 1, 138, 54, "#FFFFFF" if i % 2 == 0 else "#FFF4D6", None, 0))
        b.append(icon(["clock", "card", "brain", "book", "video", "layers", "target", "chart", "eye", "gear"][i],
                      X0 + 7, yy + 17, 0.72))
        name, sub = rows[i][0].split("|")
        b.append(t(X0 + 27, yy + 23, name, 7.8, weight="bold"))
        b.append(t(X0 + 27, yy + 37, sub, 7.0, fill=GREY))
    y = 88 + hh + 12
    b.append(t(X0, y, "B　三条贯穿性设计原则", 9, weight="bold"))
    cards = [
        ("先检索，后呈现", ["卡片默认隐藏答案；错题回炉", "不重看答案，而是回原文重新", "检索并生成新讲解（测试效应）"], "quiz"),
        ("降低外在负荷", ["速览用大纲、精读用文稿、", "图文用双通道；每个知识单元", "只承载一个考点（认知负荷）"], "layers"),
        ("可解释、可回退", ["掌握度给低分依据；自适应", "调度设计为可开关增强项，", "A/B 不显著即回退 FSRS 基线"], "shield"),
    ]
    for i, (title, lines, ic) in enumerate(cards):
        b.append(box(X0 + i * 212, y + 8, 204, 84, title, lines, fill="#F3FAFD", icon_name=ic, tsize=8.8, lsize=7.4))
    y2 = y + 100
    b.append(r(X0, y2, CW, 62, "#FBFDFE", "#9AAAB3", 0.8, "5 3"))
    for i, s in enumerate([
        "注 1：本图把产品报告第四章 38 项功能全景清单按「设计理论」重新归类，功能编号与技术方案 3.7 集成核对表一致。",
        "注 2：所有参数写成可配置常量并落库（review_logs / mastery），便于答辩现场演示 A/B 与回退，而非口头描述。",
    ]):
        b.append(t(X0 + 12, y2 + 22 + i * 20, s, 8.2, fill="#2B3237"))
    return frame("功能模块的设计理论依据矩阵",
                 "第四章 · 功能 → 理论 → 文献 → 参数 四列映射 · 图标标注功能域",
                 "\n".join(b),
                 "图标：时钟 复习 · 卡片 产物 · 脑 掌握度 · 书 笔记 · 视频 解析 · 层 切块 · 靶 触发 · 图表 排程 · 眼 反馈 · 齿轮 演进",
                 "图 4-3　功能模块的设计理论依据矩阵",
                 "Fig. 4-3　Design-theory rationale matrix for functional modules",
                 tag="GFLC · 2026")


def fig_5_3():
    b = []
    b.append(t(X0, 78, "A　服务器选购对比（2026-11-14 官网活动价）", 9, weight="bold"))
    rows = [
        ["腾讯云轻量 2C4G5M ★", "¥188/年 ≈ ¥15.7/月", "¥65/月", "2C / 4G / 5M / SSD", "选", "新客限购 1 台，到期续费 ×4.2"],
        ["阿里云轻量 2C4G", "¥199/年（秒杀）", "¥379/年", "2C / 4G / 峰值带宽", "备选", "常规价 ¥379/年，秒杀需蹲点"],
        ["阿里云 ECS e 2C2G", "¥99/年（续费同价）", "¥99/年", "2C / 2G", "不选", "2G 内存跑不动 API + Worker 双进程"],
        ["P2 升配 4C8G", "¥880/年", "—", "4C / 8G", "预留", "20 并发观测出瓶颈后再升配"],
    ]
    tb, hh = table(X0, 88, [136, 128, 84, 116, 48, 120],
                   ["机型", "活动价", "续费价", "规格", "结论", "备注"], rows,
                   header_h=26, row_h=34, font=7.6, aligns=["start", "middle", "middle", "middle", "middle", "start"])
    b.append(tb)

    y = 88 + hh + 12
    b.append(t(X0, y, "B　月度成本构成图表（20 用户内测，堆叠柱 + 占比条）", 9, weight="bold"))
    b.append(r(X0, y + 10, 392, 232, "#FFFFFF", INK, 1))
    # 堆叠柱
    groups = [("按量内测", 15.7, 60, 6, 0), ("订阅 Lite", 15.7, 39, 6, 0), ("第 2 年续费", 65, 60, 6, 0)]
    gx, gy, gh = 52, y + 40, 150
    for i, (name, srv, llm, dom, _) in enumerate(groups):
        xx = gx + 20 + i * 116
        total = srv + llm + dom
        scale = gh / 150
        b.append(t(xx + 30, y + 30, name, 7.8, "middle", "bold"))
        cur = gy + gh
        for val, fill, lab in [(srv, "#212121", "服务器"), (llm, "#83949E", "LLM"), (dom, "#DCEBF2", "域名")]:
            h = val * scale
            b.append(r(xx, cur - h, 60, h, fill, "#FFFFFF" if fill != "#DCEBF2" else "#9AAAB3", 0.5))
            if h > 14:
                b.append(t(xx + 30, cur - h / 2 + 3, f"{val:g}", 7.2, "middle", "bold", "#FFFFFF" if fill == "#212121" else INK))
            cur -= h
        b.append(t(xx + 30, cur - 6, f"¥{total:g}", 8.2, "middle", "bold", RED if i == 2 else INK))
        b.append(ln(xx - 4, gy + gh, xx + 64, gy + gh, INK, 0.7))
    b.append(ln(gx, gy, gx, gy + gh, INK, 0.8))
    # 预算线
    byline = gy + gh - 250 * (gh / 150) if False else gy + gh - 250 / 150 * gh
    # 250 超出坐标范围，改用标注
    b.append(ln(gx + 4, gy + gh - 100 * (gh / 150), gx + 366, gy + gh - 100 * (gh / 150), RED, 0.8, "4 3"))
    b.append(t(gx + 366, gy + gh - 100 * (gh / 150) - 4, "¥100", 7, "end", fill=RED))
    b.append(t(X0 + 8, y + 224, "■ 服务器　■ LLM API　□ 域名　·　横虚线 ¥100 参照；¥250 为硬上限（图外）", 7.2, fill=GREY))
    # 占比条
    b.append(t(428, y, "C　按量内测成本占比", 9, weight="bold"))
    b.append(r(428, y + 10, 228, 96, "#F3FAFD", INK, 1))
    total = 81.7
    segs = [("服务器 ¥15.7", 15.7 / total, INK), ("LLM ¥60", 60 / total, "#83949E"), ("域名 ¥6", 6 / total, "#DCEBF2")]
    xx = 440
    for lab, frac, fill in segs:
        w = 204 * frac
        b.append(r(xx, y + 34, w, 20, fill, "#FFFFFF" if fill == INK else "#9AAAB3", 0.5))
        xx += w
    for i, (lab, frac, fill) in enumerate(segs):
        b.append(r(440, y + 66 + i * 13, 9, 9, fill, "#9AAAB3", 0.4))
        b.append(t(455, y + 74 + i * 13, f"{lab}　{frac*100:.0f}%", 7.6))
    # 敏感度
    b.append(t(428, y + 118, "D　用户规模敏感度", 9, weight="bold"))
    b.append(r(428, y + 128, 228, 114, "#FFFFFF", INK, 1))
    pts = [(10, 41), (20, 82), (50, 172), (100, 322)]
    b.append(ln(446, y + 224, 644, y + 224, INK, 0.8))
    b.append(ln(446, y + 146, 446, y + 224, INK, 0.8))
    poly = " ".join(f"{446 + (u-5)/100*186:.1f},{y + 224 - min(c,350)/350*70:.1f}" for u, c in pts)
    b.append(f'<polyline points="{poly}" fill="none" stroke="{INK}" stroke-width="1.4"/>')
    for u, c in pts:
        px, py = 446 + (u - 5) / 100 * 186, y + 224 - min(c, 350) / 350 * 70
        b.append(circ(px, py, 2.2, INK))
        b.append(t(px, py - 6, f"¥{c}", 7, "middle", "bold"))
        b.append(t(px, y + 236, f"{u}人", 7, "middle", fill=GREY))
    b.append(t(436, y + 148, "¥", 7, fill=GREY))

    y2 = y + 252
    b.append(t(X0, y2, "E　结论、风险与报价口径", 9, weight="bold"))
    b.append(box(X0, y2 + 8, 204, 74, "内测约 ¥82/月", ["按量付费：15.7 + 60 + 6", "区间 ¥52–192；", "对照 ¥250 上限有余量"], fill="#F0F8FC", icon_name="coin", tsize=8.8, lsize=7.2))
    b.append(box(X0 + 212, y2 + 8, 204, 74, "订阅制 ¥39–79/月", ["Token Plan 一次付费", "含 150+ 模型，无月账单", "浮动；见图 5-4"], fill="#F3FAFD", icon_name="cloud", tsize=8.8, lsize=7.2))
    b.append(box(X0 + 424, y2 + 8, 208, 74, "⚠ 续费陷阱", ["第 2 年服务器 ¥65/月", "（×4.2）；答辩周期内", "活动价可覆盖"], fill="#F3FAFD", icon_name="warn", tsize=8.8, lsize=7.2))
    y3 = y2 + 90
    b.append(r(X0, y3, CW, 60, "#FBFDFE", "#9AAAB3", 0.8, "5 3"))
    for i, s in enumerate([
        "注 1：价格采集自腾讯云 2026 采购季 / 云+校园、阿里云双 11 会场官网活动页（2026-11-14），采购前以当期报价校准。",
        "注 2：LLM 单价 qwen-flash ¥0.15/¥1.5、qwen-plus ¥0.8/¥2、qwen-max ¥2.4/¥9.6（元/百万 tokens）；ASR / OCR / Embedding 本地跑零 API 费。",
    ]):
        b.append(t(X0 + 12, y3 + 22 + i * 20, s, 8.0, fill="#2B3237"))
    b.append(t(X0, 674, "F　LLM API 单价 × 三档路由映射（元/百万 tokens，按量付费口径）", 9, weight="bold"))
    rows3 = [
        ["轻档 qwen-flash", "¥0.15", "¥1.50", "意图解析 / 格式整理 / 摘要", "单次成本 <0.001 元量级"],
        ["中档 qwen-plus", "¥0.80", "¥2.00", "常规笔记 / 卡片 / 题目解析", "主线默认档位"],
        ["强档 qwen-max", "¥2.40", "¥9.60", "复杂推理 / 组卷 / 低置信重跑", "仅护栏判定后启用"],
        ["DeepSeek-V4.1 Flash", "$0.15", "$0.60", "供应商可替换的备选端点", "美元计价，peak 时段翻倍"],
    ]
    tb3, _ = table(X0, 684, [122, 70, 70, 218, 152],
                   ["模型档位", "输入单价", "输出单价", "用途", "备注"], rows3,
                   header_h=24, row_h=30, font=7.6,
                   aligns=["start", "middle", "middle", "start", "start"])
    b.append(tb3)
    return frame("运行成本解析与服务器云服务选型（图表版）",
                 "第五章 · 服务器实价对比 · 月度成本堆叠柱 · 占比条 · 规模敏感度曲线",
                 "\n".join(b),
                 "■ 服务器　■ LLM　□ 域名　朱红＝预算参照 / 风险项　·　数据出处：技术方案 5.8 · 图 5-4",
                 "图 5-3　运行成本解析与服务器云服务选型（图表版）",
                 "Fig. 5-3　Operating cost breakdown and server / cloud service selection",
                 tag="GFLC · 2026")


if __name__ == "__main__":
    save("图1-1_竞品格局与差异化定位矩阵", fig_1_1(), ROOT)
    save("图1-2_已上线竞品定价对照与能力覆盖分析", fig_1_2(), ROOT)
    save("图4-2_学习闭环与间隔复习调度机制", fig_4_2(), ROOT)
    save("图4-3_功能模块设计理论依据矩阵", fig_4_3(), ROOT)
    save("图5-3_运行成本解析与服务器云服务选型", fig_5_3(), ROOT)
