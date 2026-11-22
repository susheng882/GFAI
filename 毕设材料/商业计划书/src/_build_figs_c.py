# -*- coding: utf-8 -*-
"""重绘图 5-2 功能全景流程图、图 6-1 专业甘特图。
数据口径：产品报告第四章（八）38 项功能全景清单；技术方案 §6 16 周排期与 P0–P6 出口条件。
主体字号 9.6–10.2 px，最小 9.0 px，统一 680×960 A4 画布。
"""
from pathlib import Path
from _figlib import W, H, INK, GREY, LIGHT, RED, t, r, ln, path, circ, icon, frame, save

ROOT = Path(__file__).parent
X0, X1 = 24, 656
CW = X1 - X0

# ---------------- 38 项功能（真实清单，按主链路五阶段归组） ----------------
STAGES = [
    ("①", "素材接入层", "Collection", "6 项", "链接 / 文件 / 待整理清单", "video", [
        ("F01", "B站链接", "V0"), ("F02", "本地上传", "V0"),
        ("F03", "待整理清单", "V0"), ("F04", "YouTube 源", "V1"),
        ("F05", "插件收藏", "V2"), ("F06", "播放列表", "V2")]),
    ("②", "入口与调度层", "Orchestration", "6 项", "统一提交 / 鉴权 / 状态机", "flow", [
        ("F34", "注册与会话", "V0"), ("F35", "成本护栏", "V0"),
        ("F36", "注销/导出", "V0"), ("F37", "供应商管理", "V1"),
        ("F38", "图片本域代理", "V1"), ("F31", "任务回看", "V0")]),
    ("③", "内容解析与生成", "Content Parsing", "10 项", "三级取材 · 契约校验 · 溯源", "brain", [
        ("F07", "取材降本链", "V0"), ("F08", "语音转写", "V0"),
        ("F09", "PDF 解析", "V0"), ("F10", "扫描 OCR", "V1"),
        ("F11", "智能切片", "V0"), ("F12", "三档路由", "V0"),
        ("F13", "契约校验降级", "V0"), ("F14", "断点续传", "V0"),
        ("F15", "溯源硬字段", "V0"), ("F16", "关键帧截图", "V1")]),
    ("④", "知识产品层", "Knowledge", "9 项", "笔记 / 卡片 / 组卷 / 问答", "card", [
        ("F17", "结构化笔记", "V0"), ("F18", "背诵卡片", "V0"),
        ("F19", "智能组卷", "V0"), ("F20", "错题本", "V0"),
        ("F21", "多版本笔记", "V0"), ("F22", "MD/PDF 导出", "V1"),
        ("F23", "Anki 导出", "V1"), ("F30", "带来源问答", "V0"),
        ("F33", "成长记录", "V1")]),
    ("⑤", "学习闭环层", "Learning Loop", "7 项", "遗忘曲线 · 掌握度驱动", "target", [
        ("F24", "今日任务卡", "V0"), ("F25", "拖拽仪表盘", "V0"),
        ("F26", "计划与重排", "V0"), ("F27", "复习排程", "V0"),
        ("F28", "掌握度模型", "V0"), ("F29", "错题回炉", "V0"),
        ("F32", "NL 问数", "V2")]),
]

VSTYLE = {  # 版本：V0 主线 / V1 V1.5 / V2 规划池
    "V0": ("#FFFFFF", INK, 1.0, ""),
    "V1": ("#EEF7FB", "#6C7B85", 0.8, ""),
    "V2": ("#FFFFFF", "#83949E", 0.8, "4 3"),
}


def sec(y, tag, name):
    return [r(X0, y - 10, 3, 12, INK, None, 0), t(X0 + 9, y, f"{tag}　{name}", 10, weight="bold")]


def node(x, y, w, h, code, label, ver):
    fill, stroke, sw, dash = VSTYLE[ver]
    out = [r(x, y, w, h, fill, stroke, sw, dash)]
    out.append(t(x + 6, y + 17, code, 8.6, fill="#55626A"))
    out.append(t(x + 34, y + 17, label, 9.0, weight="bold" if ver == "V0" else ""))
    return "\n".join(out)


def fig_5_2():
    b = []
    b += sec(86, "A", "五阶段主链路（阶段编号 · 驱动机制 · 功能容量）")
    # 五阶段横向主流程卡
    cardw, gap = 118, 9.2
    for i, (num, cn, en, cnt, drv, ic, items) in enumerate(STAGES):
        x = X0 + i * (cardw + gap)
        b.append(r(x, 96, cardw, 78, "#FFFFFF", INK, 1.0))
        b.append(r(x, 96, cardw, 21, INK, INK, 0.8))
        b.append(t(x + 7, 111, f"{num} {cn}", 9.6, weight="bold", fill="#FFFFFF"))
        b.append(icon(ic, x + 8, 121, 0.62))
        b.append(t(x + 27, 134, en, 8.8, fill=GREY))
        b.append(t(x + 27, 148, f"{cnt} 功能", 9.2, weight="bold"))
        b.append(t(x + 7, 165, drv[:12], 8.6, fill="#3C464D"))
        if i < 4:
            b.append(ln(x + cardw + 1, 135, x + cardw + gap - 2, 135, INK, 0.9, arrow=True))

    # B 五阶段泳道流程（38 个功能节点全部落位）
    b += sec(192, "B", "五阶段泳道功能全景（F01–F38 · 节点内流程顺序 · 版本以框型区分）")
    lane_y, lane_h = 202, 69
    ncol, nrow = 5, 2
    nw, nh = 100, 26
    gx, gy = 5.5, 5
    for si, (num, cn, en, cnt, drv, ic, items) in enumerate(STAGES):
        y = lane_y + si * (lane_h + 3)
        b.append(r(X0, y, CW, lane_h, "#F3FAFD" if si % 2 == 0 else "#FFFFFF", "#C6DEE9", 0.6))
        b.append(r(X0, y, 104, lane_h, INK, INK, 0.8))
        b.append(t(X0 + 6, y + 22, f"{num} {cn}", 9.6, weight="bold", fill="#FFFFFF"))
        b.append(t(X0 + 6, y + 38, en, 8.6, fill="#DCEBF2"))
        b.append(t(X0 + 6, y + 57, f"{cnt} · {drv[:7]}", 8.4, fill="#DCEBF2"))
        bx = X0 + 110
        for k, (code, label, ver) in enumerate(items):
            cc, rr = k % ncol, k // ncol
            nx = bx + cc * (nw + gx)
            ny = y + 8 + rr * (nh + gy)
            b.append(node(nx, ny, nw, nh, code, label, ver))
            if cc < ncol - 1 and k + 1 < len(items):
                b.append(ln(nx + nw + 1, ny + nh / 2, nx + nw + gx - 1.5, ny + nh / 2,
                            "#83949E", 0.7, arrow=True))
        # 阶段间纵向箭头
        if si < 4:
            b.append(ln(X0 + 52, y + lane_h, X0 + 52, y + lane_h + 2.6, INK, 1.0, arrow=True))

    # C 关键链路与闭环回授
    b += sec(578, "C", "关键链路 K1–K3 与错题回炉闭环（编号与图 5-1 互相锚定）")
    kcards = [
        ("K1", "大文件直传", "presign → 直传 → confirm", "以 stat 为准，字节流不进 API"),
        ("K2", "长任务入队", "入队 → Worker 消费 → 产物写回", "API 与 CPU 密集管线分进程"),
        ("K3", "任务态反馈", "3→15 s 退避 · 心跳 · 60 min 超时", "不引入 WebSocket 长连接"),
    ]
    for i, (k, name, line1, line2) in enumerate(kcards):
        x = X0 + i * 213
        b.append(r(x, 588, 204, 56, "#FFFFFF", INK, 0.9))
        b.append(t(x + 7, 604, f"{k}　{name}", 9.6, weight="bold"))
        b.append(t(x + 7, 620, line1, 8.8, fill="#2B3237"))
        b.append(t(x + 7, 634, line2, 8.6, fill=GREY))
    # 闭环回授虚线：从学习闭环右侧回到内容解析链路
    b.append(path("M 650,536 L 660,536 L 660,352 L 650,352", stroke=RED, sw=1.2, dash="5 3", arrow=True))
    b.append(t(640, 566, "错题回炉：低掌握度知识点 → 回流内容解析链路生成变式练习", 9.0, "end", fill=RED))
    b.append(icon("loop", X0 + 6, 648, 0.62, RED))
    b.append(t(X0 + 25, 657, "闭环合龙：mastery < θ=0.85 触发回炉，复习行为回流掌握度模型（技术方案 3.9）", 9.0, fill=RED))

    # D 版本分布 + 六功能域统计 + 验收
    b += sec(686, "D", "功能版本分布、六功能域构成与关键功能验收口径")
    # 堆叠条
    b.append(t(X0 + 4, 706, "版本切分（38 项）", 9.4, weight="bold"))
    segs = [(27, INK, "主线 27"), (8, "#B4C3CB", "V1.5 8"), (3, "#FFFFFF", "规划 3")]
    sx = X0 + 4
    for v, col, lab in segs:
        w = 300 * v / 38
        b.append(r(sx, 712, w, 20, col, INK, 0.8, "" if v != 3 else "4 3"))
        if v >= 8:
            b.append(t(sx + w / 2, 726, lab, 9.0, "middle", "bold",
                       "#FFFFFF" if v == 27 else INK))
        sx += w
    b.append(t(X0 + 4, 746, "主线 27 项为答辩可演示范围；V1.5 8 项可独立降级，不阻塞主路径。", 8.8, fill="#2B3237"))
    b.append(t(X0 + 4, 760, "验收：四条主路径 100% / 解析成功率 ≥90% / 溯源字段不可缺省。", 8.8, fill="#2B3237"))
    # 六域统计表
    tx = X0 + 328
    dom = [("收集与入口", 6, "3/1/2"), ("内容解析", 10, "8/2/0"), ("知识产品", 7, "5/2/0"),
           ("学习闭环", 6, "6/0/0"), ("增强能力", 4, "2/1/1"), ("平台与账号", 5, "3/2/0")]
    b.append(r(tx, 700, 300, 20, INK, INK, 0.8))
    for x, s, anc in [(tx + 6, "功能域", "start"), (tx + 176, "项数", "middle"), (tx + 246, "主/V1.5/规划", "middle")]:
        b.append(t(x, 714, s, 9.0, anc, "bold", "#FFFFFF"))
    for i, (name, n, split) in enumerate(dom):
        yy = 720 + i * 16
        b.append(r(tx, yy, 300, 16, "#FFF4D6" if i % 2 else "#FFFFFF", "#DCEBF2", 0.4))
        b.append(t(tx + 6, yy + 11.5, name, 9.0))
        b.append(t(tx + 176, yy + 11.5, str(n), 9.0, "middle", "bold"))
        b.append(t(tx + 246, yy + 11.5, split, 9.0, "middle"))
    b.append(ln(tx + 168, 700, tx + 168, 816, "#C6DEE9", 0.4))
    b.append(ln(tx + 220, 700, tx + 220, 816, "#C6DEE9", 0.4))

    # E 注释
    b.append(r(X0, 824, CW, 30, "#FBFDFE", "#9AAAB3", 0.7, "5 3"))
    b.append(t(X0 + 7, 836, "注 1：节点编号 F01–F38 与产品报告第四章（八）功能全景清单一一对应；白底实框＝主线，灰底＝V1.5，虚线框＝规划池。", 8.8, fill="#2B3237"))
    b.append(t(X0 + 7, 849, "注 2：K1/K2/K3 与图 2-1、2-2、2-3、5-1 编号一致；数据出处：产品报告第四章（八）、技术方案 2.5 / 2.6 / 3.9。", 8.8, fill="#2B3237"))

    legend = "白底实框＝主线 27　·　灰底＝V1.5 8　·　虚线框＝规划池 3　·　实线箭头＝主流程　·　朱红虚线＝闭环回授　·　数据出处：产品报告第四章（八）"
    return frame("功能全景流程图：38 项功能 × 五阶段主链路", "第五章 · 五阶段泳道 · F01–F38 全景节点 · K1–K3 关键链路 · 错题回炉闭环 · 产品报告第四章（八）",
                 "\n".join(b), legend, "图 5-2　功能全景流程图（38 项功能 × 五阶段）",
                 "Fig. 5-2　End-to-end functional flow of 38 features across five stages", tag="GFLC · 2026")


# ---------------- 甘特图 WBS（技术方案 §6 真实阶段与出口） ----------------
TASKS = [
    ("P0", "1.1", "需求与契约 Schema", 1, 2, "M"),
    ("P0", "1.2", "Compose 与服务编排", 2, 3, "M"),
    ("P1", "2.1", "ASR / PDF / OCR 适配器", 3, 5, "M"),
    ("P1", "2.2", "三档路由与四级降级", 4, 6, "M"),
    ("P1", "2.3", "字幕优先取材链", 5, 6, "M"),
    ("P1", "2.4", "Worker + Redis 队列", 6, 7, "M"),
    ("P1", "2.5", "预签名上传 + Alembic", 7, 8, "M"),
    ("P2", "3.1", "计划与复习调度", 8, 10, "M"),
    ("P2", "3.2", "掌握度模型 + pgvector", 9, 11, "M"),
    ("P3", "4.1", "时间戳溯源（可牺牲）", 10, 12, "S"),
    ("P3.5", "5.1", "V1.5 增量（截图/导出）", 12, 14, "V"),
    ("P4", "6.1", "E2E + 性能压测", 13, 15, "M"),
    ("P5", "7.1", "CI 门禁 + 备份恢复演练", 14, 16, "M"),
    ("P6", "8.1", "灰度 5/25/100 + 回滚", 16, 16, "M"),
]
EXITS = [
    ("P0 需求与设计", "W1–W3", "Compose config 通过；契约 Schema 可单测", "G1 门"),
    ("P1 内容管线", "W3–W8", "40 份评测集字段完整率 ≥95%；Worker/直传/迁移就位", "G1 质量"),
    ("P2 学习闭环", "W8–W11", "四条主路径 API 测试 100%；掌握度可解释", "G1 功能"),
    ("P3 视频链路", "W10–W12", "第 11 周未达标即降 V1.5，不拖主线", "降级决策"),
    ("P3.5 V1.5 增量", "W12–W14", "截图与导出可独立降级，不阻塞主路径", "可选"),
    ("P4 内测打磨", "W13–W15", "P95 ≤3 s；解析成功率 ≥90%；错误案例库", "G2 性能"),
    ("P5 上线准备", "W14–W16", "CI 门禁 + 恢复演练 + 成本告警；G3 三项达标", "G3/G4/G5"),
    ("P6 灰度发布", "W16", "5/25/100 灰度；回滚 ≤10 min；Go/No-Go", "G7 发布"),
]


def fig_6_1():
    b = []
    b += sec(86, "A", "16 周甘特主体（WBS 14 项任务 · 周刻度 · 依赖 · 里程碑）")
    LX, RX = 224, 656          # 任务列右界 / 刻度区右界
    WK = (RX - LX) / 16        # 27 px
    HY, HH = 96, 24            # 表头
    TY = HY + HH               # 120 任务起点
    RH = 24
    ENDY = TY + len(TASKS) * RH   # 456
    # 周网格
    for i in range(16):
        xx = LX + i * WK
        gate = i in (3, 7, 11, 16)
        b.append(ln(xx, HY, xx, ENDY + 26, "#BED3DE" if gate else "#E1EFF6",
                    0.8 if gate else 0.5, "3 3" if gate else ""))
    b.append(r(X0, HY, CW, HH, INK, INK, 0.8))
    b.append(t(X0 + 6, HY + 16, "阶段 / WBS / 工程任务", 9.2, weight="bold", fill="#FFFFFF"))
    for i in range(16):
        b.append(t(LX + (i + 0.5) * WK, HY + 16, f"W{i+1}", 8.8, "middle", "bold", "#FFFFFF"))
    # 任务行
    bar_style = {"M": (INK, INK, 1.0, ""), "V": ("#BED3DE", "#55626A", 0.8, ""),
                 "S": ("#FFFFFF", RED, 0.9, "4 3")}
    prev_phase = None
    for i, (ph, wbs, name, s, e, kind) in enumerate(TASKS):
        yy = TY + i * RH
        b.append(r(X0, yy, CW, RH, "#F3FAFD" if i % 2 == 0 else "#FFFFFF", "#E7F2F8", 0.4))
        if ph != prev_phase:
            b.append(r(X0, yy, 4, RH, INK if ph not in ("P3", "P3.5") else RED, None, 0))
            prev_phase = ph
        b.append(t(X0 + 8, yy + 16, ph, 8.8, weight="bold", fill=RED if ph == "P3" else GREY))
        b.append(t(X0 + 48, yy + 16, wbs, 8.8, fill=GREY))
        b.append(t(X0 + 80, yy + 16, name, 9.2, weight="bold" if kind == "M" else ""))
        fill, stroke, sw, dash = bar_style[kind]
        bx = LX + (s - 1) * WK + 2
        bw = (e - s + 1) * WK - 4
        b.append(r(bx, yy + 5, bw, 14, fill, stroke, sw, dash))
        if bw > 34:
            b.append(t(bx + bw / 2, yy + 15.5, f"{s}–{e}" if s != e else str(s), 8.6, "middle", "bold",
                       "#FFFFFF" if kind == "M" else (RED if kind == "S" else INK)))
    # 里程碑行
    MY = ENDY + 2
    b.append(r(X0, MY, CW, 24, "#FFFFFF", INK, 0.8))
    b.append(t(X0 + 6, MY + 16, "里程碑 / 门禁", 9.2, weight="bold"))
    miles = [(3, "M1 G1"), (7, "M2 评测"), (11, "M3 路径"), (12.8, "M4 降级"),
             (14.5, "M5 Go"), (16, "M6 回滚")]
    for wk, lab in miles:
        cx = LX + (wk - 0.5) * WK
        b.append(f'<path d="M {cx:.1f},{MY+4} L {cx+7:.1f},{MY+12} L {cx:.1f},{MY+20} L {cx-7:.1f},{MY+12} Z" '
                 f'fill="{INK}" stroke="{INK}" stroke-width="0.7"/>')
        b.append(t(cx, MY + 35, lab, 8.4, "middle", fill=GREY))

    # B 单人周工时投入曲线
    b += sec(508, "B", "单人周工时投入曲线（计划值 · 峰值与缓冲对照）")
    GX0, GX1, GY0, GY1 = LX, RX, 520, 590
    b.append(r(GX0, GY0, GX1 - GX0, GY1 - GY0, "#FFFFFF", "#DCEBF2", 0.6))
    for v in (0, 20, 40):
        yy = GY1 - v / 45 * (GY1 - GY0)
        b.append(ln(GX0, yy, GX1, yy, "#E7F2F8", 0.5))
        b.append(t(GX0 - 6, yy + 3, str(v), 8.6, "end", fill=GREY))
    b.append(t(X0 + 6, GY0 + 14, "工时", 9.0, weight="bold"))
    b.append(t(X0 + 6, GY0 + 30, "h / 周", 8.6, fill=GREY))
    hours = [22, 28, 30, 34, 36, 38, 35, 32, 36, 40, 38, 30, 34, 32, 28, 20]
    pts = []
    for i, v in enumerate(hours):
        xx = GX0 + (i + 0.5) * WK
        yy = GY1 - v / 45 * (GY1 - GY0)
        pts.append(f"{xx:.1f},{yy:.1f}")
    b.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{INK}" stroke-width="1.5"/>')
    for i, v in enumerate(hours):
        xx = GX0 + (i + 0.5) * WK
        yy = GY1 - v / 45 * (GY1 - GY0)
        b.append(circ(xx, yy, 1.8, RED if v == 40 else INK, INK, 0.5))
    b.append(ln(GX0, GY1 - 40 / 45 * (GY1 - GY0), GX1, GY1 - 40 / 45 * (GY1 - GY0), RED, 0.7, "4 3"))
    b.append(t(GX1 - 4, GY1 - 40 / 45 * (GY1 - GY0) - 4, "缓冲上限 40 h", 8.6, "end", fill=RED))
    b.append(t(X0 + 6, GY1 + 12, "峰值 W10（40 h）；均值约 32 h/周；单人实际排期按 20–24 周折算。", 8.8, fill="#2B3237"))

    # C 出口门禁表
    b += sec(618, "C", "阶段出口条件与上线门禁映射（技术方案 §6 · G1–G7）")
    cw = [116, 62, 348, 106]
    cx = [X0]
    for w in cw:
        cx.append(cx[-1] + w)
    b.append(r(X0, 628, CW, 20, INK, INK, 0.8))
    for j, h in enumerate(["阶段", "周次", "出口条件（可核验）", "门禁"]):
        b.append(t(cx[j] + 5, 642, h, 9.0, weight="bold", fill="#FFFFFF"))
    for i, row in enumerate(EXITS):
        yy = 648 + i * 15
        b.append(r(X0, yy, CW, 15, "#FFF4D6" if i % 2 else "#FFFFFF", "#DCEBF2", 0.4))
        for j, cell in enumerate(row):
            b.append(t(cx[j] + 5, yy + 11, cell, 8.8, weight="bold" if j == 0 else ""))
    for j in range(1, 4):
        b.append(ln(cx[j], 628, cx[j], 768, "#C6DEE9", 0.4))

    # D 风险缓冲与降级决策
    b += sec(784, "D", "进度风险缓冲与范围控制")
    cards = [
        ("缓冲周", "W12 / W15 各留 0.5 周浮量", "吸收 ASR 与第三方接口波动"),
        ("可牺牲项", "P3 时间戳溯源第 11 周判定", "未达标即降 V1.5，主线不受影响"),
        ("关键路径", "P0 → P1 → P2 → P4 → P5 → P6", "任一延期直接顺延答辩演示"),
    ]
    for i, (h, l1, l2) in enumerate(cards):
        x = X0 + i * 213
        b.append(r(x, 792, 204, 50, "#FFFFFF", INK, 0.9))
        b.append(icon(["clock", "warn", "flow"][i], x + 7, 797, 0.6))
        b.append(t(x + 26, 808, h, 9.4, weight="bold"))
        b.append(t(x + 7, 823, l1, 8.8))
        b.append(t(x + 7, 836, l2, 8.6, fill=GREY))

    legend = "深灰实条＝主线任务　·　浅灰＝V1.5 增量　·　朱红虚线框＝可牺牲项　·　竖虚线＝阶段门禁周　·　◆＝里程碑/门禁　·　数据出处：技术方案 §6"
    return frame("16 周工程里程碑与排期映射甘特图", "第六章 · WBS 14 项任务 · 16 周刻度 · 关键路径与依赖 · 单人投入曲线 · P0–P6 出口门禁 · 技术方案 §6",
                 "\n".join(b), legend, "图 6-1　16 周工程里程碑与排期映射甘特图",
                 "Fig. 6-1　Sixteen-week milestone and schedule Gantt chart", tag="GFLC · 2026")


if __name__ == "__main__":
    save("图5-2_功能全景流程图", fig_5_2(), ROOT)
    save("图6-1_16周工程里程碑与排期映射甘特图", fig_6_1(), ROOT)
