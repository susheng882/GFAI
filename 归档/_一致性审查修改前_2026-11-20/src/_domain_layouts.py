# -*- coding: utf-8 -*-
"""六大功能域图的差异化版式（2026-11-15 第二次改版）。

用户反馈：不再统一成「AI 横向管线」，要求每张图排版各自不同且内容依然丰富。
本模块为图 3-4～3-9 各设计一种独立的信息组织方式：

  3-4 多源汇聚分流树   左入口 → 中央统一网关 → 右三路解析器 + 3×2 功能宫格
  3-5 阶段×关卡棋盘    五阶段 × 四列质量成本矩阵 + 十行五列功能清单 + 理论卡
  3-6 中心放射派生图   单知识单元为 hub，六类产物环绕 + 2×4 功能宫格
  3-7 环形闭环+时间轴  五节点回路 + R1–R4 遗忘曲线轴 + 六行功能时间线
  3-8 仪表盘+漏斗      KPI 宫格 + 轨迹示意 + 五级收窄漏斗 + 2×2 功能大卡
  3-9 治理金字塔+矩阵  四层金字塔 + 治理对照矩阵 + 三原则论证条

所有区块仍以 X0=24、CW=632 全宽严格对齐，经 compose 自动铺满 680×960 画布。
数据一律取自 _build_bp_b.DOMAINS 与已落地的产品/技术文档口径，不新增未经核实的数字。
"""
from _figlib import INK, GREY, RED, t, r, ln, path, circ, icon
from _figlib2 import X0, CW
from _figlib_bp import compose

A = ["start"] * 4
A3 = ["start"] * 3


# ---------------------------------------------------------------- 通用小工具
def _head(o, cy, d):
    """各图共用的 44pt 域信息带：定位 / 痛点 / 规模 / 设计约束，行距留足不贴框线。"""
    o.append(r(X0, cy, CW, 44, "#E4F3FB", INK, 0.5))
    o.append(t(X0 + 8, cy + 13, "域定位：" + d["pos"][0], 8.8, weight="bold"))
    o.append(t(X0 + 8, cy + 27, d["pains"] + "　｜　" + d["pos"][1], 8.2, fill="#3C464D"))
    o.append(t(X0 + 8, cy + 40, d["sub"], 8.0, fill=GREY))


def _subtitle(o, cy, s):
    o.append(t(X0, cy + 56, s, 8.6, weight="bold", fill="#2B3237"))


def _wrap(s, n=17, k=2):
    """中文按字宽粗切，最多 k 行；用于窄卡片内长说明。"""
    out, buf = [], ""
    for ch in s:
        buf += ch
        if len(buf) >= n:
            out.append(buf)
            buf = ""
            if len(out) == k:
                break
    if buf and len(out) < k:
        out.append(buf)
    return out


def _chip(o, x, y, w, s, fill="#EEF7FB"):
    o.append(r(x, y, w, 15, fill, "#B4C3CB", 0.5))
    o.append(t(x + w / 2, y + 11, s, 7.8, "middle", weight="bold", fill="#2B3237"))


def _cell(o, x, y, w, h, lines, fs=8.2, bold_first=False, fill="#FFFFFF"):
    o.append(r(x, y, w, h, fill, "#C6DEE9", 0.5))
    for k, s in enumerate(lines):
        o.append(t(x + 6, y + 12 + k * 12, s, fs if k else fs + 0.2,
                   weight="bold" if (k == 0 and bold_first) else "",
                   fill=INK if k == 0 else "#3C464D"))


def _trap(cx, y, wt, wb, h, fill="#FFFFFF"):
    return path(f"M {cx-wt/2:.1f},{y:.1f} L {cx+wt/2:.1f},{y:.1f} "
                f"L {cx+wb/2:.1f},{y+h:.1f} L {cx-wb/2:.1f},{y+h:.1f} Z",
                INK, 0.9, fill=fill)


def _note(d):
    return ("", "note", {"title": "依赖关系与版本说明", "icon": "flow", "lines": d["note"]})


def _theory_grid(d, widths=None, headers=None, tag="C"):
    return (tag + "　设计理论 · 优化手段 · 验收口径", "grid", {
        "widths": widths or [176, 234, 222],
        "headers": headers or ["设计理论 / 依据", "落地参数与优化手段", "可核验验收口径"],
        "aligns": A3, "rows": d["theory"], "rh": 34, "font": 8.8})


def _emit(d, subtitle, specs):
    return compose(d["name"] + " · 功能域展开",
                   d["en"] + " / " + subtitle + " / " + d["sub"],
                   d["legend"], d["cap"], d["capen"], specs)


# ================================================================ 图 3-4 汇聚分流树
def _a34(d):
    def draw(cy):
        o = []
        _head(o, cy, d)
        _subtitle(o, cy, "多源汇聚 → 统一 task 网关 → 三路解析器：一条状态机覆盖全部入口")
        b = cy + 64
        srcs = [
            ("B 站视频链接", "F01 · 平台字幕优先", "video"),
            ("本地视频 / PDF / 讲义", "F02 · 预签名直传", "doc"),
            ("YouTube 链接", "F04 · V1.5 扩展渠道", "cloud"),
            ("插件收藏 / 播放列表", "F05 / F06 · 规划池", "layers"),
        ]
        for k, (nm, sub, ic) in enumerate(srcs):
            y = b + k * 33
            o.append(r(X0, y, 160, 29, "#FFFFFF", INK, 0.8))
            o.append(icon(ic, X0 + 5, y + 6, 0.5))
            o.append(t(X0 + 24, y + 13, nm, 8.6, weight="bold"))
            o.append(t(X0 + 24, y + 24, sub, 7.8, fill=GREY))
            o.append(ln(184, y + 14.5, 196, b + 80, "#83949E", 0.8))
        # 中央网关
        gx, gy, gw, gh = 196, b + 34, 176, 92
        o.append(r(gx, gy, gw, gh, "#FBFDFE", INK, 1.2))
        o.append(t(gx + gw / 2, gy + 20, "统一 task 网关", 10.2, "middle", "bold"))
        for k, s in enumerate(["同一 task 记录 / 同一配额校验",
                              "状态机唯一，避免多套解析逻辑",
                              "预签名 URL → object_key + 校验",
                              "Redis List 下发 job_id（K2）"]):
            o.append(t(gx + 9, gy + 38 + k * 13, s, 8.0, fill="#3C464D"))
        # 右侧三路解析器
        outs = [
            ("视频链", "字幕 → 音轨 → 转写，命中即短路", "带时间戳文本"),
            ("文档链", "PyMuPDF 抽取文本与版式", "页码定位单元"),
            ("图像链", "PaddleOCR 扫描讲义（V1.5）", "OCR 文本 + 页码"),
        ]
        for k, (nm, desc, prod) in enumerate(outs):
            y = b + k * 45
            o.append(r(392, y, 264, 41, "#FFFFFF", INK, 0.8))
            o.append(t(400, y + 15, f"{k+1}　{nm}", 9.2, weight="bold"))
            o.append(t(400, y + 28, desc, 8.0, fill="#3C464D"))
            o.append(t(648, y + 28, prod, 7.8, "end", fill=GREY))
            o.append(ln(372, b + 80, 392, y + 20, "#83949E", 0.8, arrow=True))
        o.append(t(X0, b + 140, "验收：三条链路各 10 个真实样本跑通（G1）；1 GB 文件不占 API 进程内存（图 4-4）。",
                   8.0, fill="#3C464D"))
        return "\n".join(o)
    return draw


def _b34(d):
    anchor = ["依据：认知负荷理论 Sweller 1988", "依据：经济性原则 · 直传不进 API",
              "依据：工作记忆 4±1（每屏 ≤4 项）", "依据：第 11 周出口条件降 V1.5",
              "依据：降低收集摩擦（规划池）", "依据：按科目组织对齐复习计划"]

    def draw(cy):
        o = []
        w, h, gx, gy = 205.3, 85, 8, 8
        for k, row in enumerate(d["funcs"]):
            c, rr = k % 3, k // 3
            x, y = X0 + c * (w + gx), cy + rr * (h + gy)
            o.append(r(x, y, w, h, "#FFFFFF", INK, 0.8))
            o.append(r(x, y, w, 18, "#EEF7FB", INK, 0.6))
            o.append(t(x + 7, y + 13, row[0] + "　·　" + row[3], 8.4, weight="bold"))
            o.append(t(x + 7, y + 34, row[1], 9.2, weight="bold"))
            o.append(t(x + 7, y + 51, row[2], 8.0, fill="#3C464D"))
            o.append(t(x + 7, y + 67, anchor[k], 7.9, fill=GREY))
            o.append(t(x + 7, y + 79, "出处：产品报告 第四章（八）", 7.6, fill="#83949E"))
        return "\n".join(o)
    return draw


def fig_3_4(d):
    return _emit(d, "Multi-source Ingestion Tree", [
        ("A　入口汇聚与三路分流（多源 → 统一网关 → 解析器）", "raw", {"h": 208, "svg": _a34(d)}),
        ("B　六项功能 3×2 宫格（编号 / 说明 / 理论锚点 / 出处）", "raw", {"h": 178, "svg": _b34(d)}),
        _theory_grid(d),
        ("D　域级关键数据与验收锚点", "cards", {"h": 76, "items": [
            ("入口规模", ["4 类提交入口 / 3 条解析链路", "V1.0 必达 F01–F03", "扩展渠道 F04–F06"], "layers"),
            ("成本护栏", ["预签名直传 1 GB 文件", "不进 API 进程内存", "字幕优先取材降本"], "coin"),
            ("验收锚点", ["每链路 10 个真实样本", "G1 全链路跑通", "task 状态机唯一"], "check"),
        ], "tsize": 9.4, "lsize": 8.4}),
        _note(d),
    ])


# ================================================================ 图 3-5 阶段×关卡棋盘
def _a35(d):
    rows = [
        ["① 字幕优先取材", "链接 / 音视频 / PDF", "三级链命中即短路", "跳过下载与转写，成本降量级"],
        ["② 分块与预算", "带时间戳文本", "按知识点单元切片", "体积预算二分，多轮归并"],
        ["③ 三档路由调用", "文本块 + Prompt", "难度分配 轻 / 主 / 推理", "超额自动降档 + 限流"],
        ["④ 契约校验", "模型原始输出", "JSON Schema 强校验", "失败自修复 ≤2 次 + 死信"],
        ["⑤ 落库与索引", "结构化知识单元", "时间戳 P0 硬字段", "Chroma 双索引限 50 段"],
    ]

    def draw(cy):
        o = []
        _head(o, cy, d)
        _subtitle(o, cy, "五阶段 × 四关卡：每阶段同时给出输入、质量控制与成本 / 容错护栏")
        b = cy + 64
        cols = [104, 152, 188, 188]
        xs = [X0]
        for w in cols:
            xs.append(xs[-1] + w)
        o.append(r(X0, b, CW, 18, INK, INK, 0.6))
        for j, h in enumerate(["处理阶段", "输入 / 数据", "质量控制", "成本与容错护栏"]):
            o.append(t(xs[j] + 6, b + 13, h, 8.6, weight="bold", fill="#FFFFFF"))
        for k, row in enumerate(rows):
            y = b + 18 + k * 22
            o.append(r(X0, y, CW, 22, "#FFFFFF" if k % 2 == 0 else "#F3FAFD", "#C6DEE9", 0.5))
            for j, c in enumerate(row):
                o.append(t(xs[j] + 6, y + 15, c, 8.2,
                           weight="bold" if j == 0 else "", fill="#2B3237"))
            for j in range(1, 4):
                o.append(ln(xs[j], y, xs[j], y + 22, "#E1EFF6", 0.5))
        o.append(t(X0, b + 140, "读法：横向为阶段推进，纵向为同阶段的三类约束；成本与质量在同一行内对齐，便于评审逐格核对。",
                   8.0, fill="#3C464D"))
        return "\n".join(o)
    return draw


def fig_3_5(d):
    stage = ["①", "①", "①", "①", "②", "③", "④", "④", "⑤", "②"]
    funcs = [row[:3] + [row[3], stage[k]] for k, row in enumerate(d["funcs"])]
    return _emit(d, "Stage × Gate Quality-Cost Matrix", [
        ("A　五阶段 × 四关卡质量成本棋盘", "raw", {"h": 208, "svg": _a35(d)}),
        ("B　十项功能清单（新增「关联阶段」列，与 A 区棋盘逐行对应）", "grid", {
            "widths": [46, 112, 288, 92, 94],
            "headers": ["编号", "功能", "说明", "落点", "关联阶段"],
            "aligns": ["start"] * 5, "rows": funcs, "rh": 26, "font": 8.8, "hf": 9.0}),
        ("C　三条设计理论（完整出处 + 手段 + 验收）", "cards", {"h": 76, "items": [
            ("测试效应", ["Roediger & Karpicke 2006", "切片按知识点单元便于主动检索",
                        "40 份评测集字段完整率 ≥95%"], "quiz"),
            ("输出契约", ["可验证性 / JSON Schema", "强制字段，失败即降级重跑",
                        "幻觉率与字段缺失纳入门禁"], "check"),
            ("容错成本工程", ["checkpoint + 指数退避", "断点续传不重复付费",
                          "硬超时 60 min，重试入死信"], "gear"),
        ], "tsize": 9.4, "lsize": 8.4}),
        ("", "band", {"h": 26, "items": ["① 字幕优先取材", "② 分块与预算", "③ 三档路由",
                                        "④ 契约校验", "⑤ 落库与索引"], "fs": 8.6}),
        _note(d),
    ])


# ================================================================ 图 3-6 中心放射派生
def _a36(d):
    top = [("结构化笔记 F17", "备考四档风格预设", "doc"),
           ("背诵卡片 F18", "问答 / 填空两类", "card"),
           ("智能组卷 F19", "按科目与掌握度", "quiz")]
    bot = [("错题本 F20", "附来源与错误归因", "warn"),
           ("多版本记录 F21", "版本快照 G4 可回滚", "clock"),
           ("导出包 F22 / F23", "Markdown / PDF / Anki", "layers")]

    def draw(cy):
        o = []
        _head(o, cy, d)
        _subtitle(o, cy, "单一知识单元（共享主键）→ 六类派生产物：同源不重复调用模型")
        b = cy + 64
        cw, gap = 192, 28
        hx, hy, hw, hh = 210, b + 50, 260, 60
        for k, (nm, sub, ic) in enumerate(top):
            x = X0 + k * (cw + gap)
            o.append(r(x, b, cw, 38, "#FFFFFF", INK, 0.8))
            o.append(icon(ic, x + 6, b + 8, 0.52))
            o.append(t(x + 25, b + 16, nm, 9.0, weight="bold"))
            o.append(t(x + 25, b + 30, sub, 8.0, fill=GREY))
            o.append(ln(x + cw / 2, b + 38, 340, hy, "#83949E", 0.8))
        o.append(r(hx, hy, hw, hh, "#FBFDFE", INK, 1.2))
        o.append(t(340, hy + 20, "knowledge_units", 10.0, "middle", "bold"))
        for k, s in enumerate(["共享主键 · 带 source_id", "同源派生不重复调模型", "时间戳 / 页码硬字段"]):
            o.append(t(hx + 9, hy + 35 + k * 11, s, 7.9, fill="#3C464D"))
        for k, (nm, sub, ic) in enumerate(bot):
            x = X0 + k * (cw + gap)
            y = b + 118
            o.append(r(x, y, cw, 38, "#FFFFFF", INK, 0.8))
            o.append(icon(ic, x + 6, y + 8, 0.52))
            o.append(t(x + 25, y + 16, nm, 9.0, weight="bold"))
            o.append(t(x + 25, y + 30, sub, 8.0, fill=GREY))
            o.append(ln(340, hy + hh, x + cw / 2, y, "#83949E", 0.8, arrow=True))
        # 中央左右两块实质说明
        for x, title, lines in [
            (X0, "同源派生原则", ["笔记 / 卡片 / 错题 / 组卷", "共用 knowledge_units 主键",
                              "避免重复生成与重复计费"]),
            (480, "来源绑定机制", ["每个产物带时间戳或页码", "错题附原文出处与归因",
                              "可回指、可打印、可迁移"]),
        ]:
            o.append(t(x, hy + 8, title, 8.8, weight="bold", fill=RED))
            for k, s in enumerate(lines):
                o.append(t(x, hy + 22 + k * 12, s, 7.9, fill="#3C464D"))
        return "\n".join(o)
    return draw


def _b36(d):
    anchor = ["测试效应", "主动检索", "合意困难", "来源可验证", "G4 可回滚", "G3 可携带",
              "兼容既有习惯", "设计约束"]
    def draw(cy):
        o = []
        w, h, gx, gy = 152, 94, 8, 8
        for k in range(8):
            c, rr = k % 4, k // 4
            x, y = X0 + c * (w + gx), cy + rr * (h + gy)
            o.append(r(x, y, w, h, "#FFFFFF", INK, 0.8))
            if k < 7:
                row = d["funcs"][k]
                o.append(r(x, y, w, 16, "#EEF7FB", INK, 0.6))
                o.append(t(x + 5, y + 12, row[0] + "　·　" + row[3], 7.9, weight="bold"))
                o.append(t(x + 5, y + 32, row[1], 8.4, weight="bold"))
                for j, s in enumerate(_wrap(row[2], 17, 2)):
                    o.append(t(x + 5, y + 47 + j * 12, s, 7.8, fill="#3C464D"))
                o.append(t(x + 5, y + 85, "理论：" + anchor[k], 7.6, fill=GREY))
            else:
                o.append(r(x, y, w, 16, INK, INK, 0.6))
                o.append(t(x + 5, y + 12, "落点分布统计", 7.9, weight="bold", fill="#FFFFFF"))
                for j, s in enumerate(["主线 5 项 / V1.5 2 项",
                                      "共享主键同源派生",
                                      "F22 / F23 第 11 周",
                                      "未达标可降级",
                                      "依据：成本工程原则"]):
                    o.append(t(x + 5, y + 32 + j * 12, s, 7.8,
                               fill="#2B3237" if j == 0 else "#3C464D",
                               weight="bold" if j == 0 else ""))
        return "\n".join(o)
    return draw


def fig_3_6(d):
    return _emit(d, "Hub-and-Spoke Artifact Derivation", [
        ("A　单一知识单元 → 六类产物放射派生（含同源与来源绑定机制）", "raw", {"h": 222, "svg": _a36(d)}),
        ("B　七项功能 2×4 宫格 + 落点分布统计", "raw", {"h": 196, "svg": _b36(d)}),
        _theory_grid(d),
        ("", "band", {"h": 26, "items": ["Markdown 导出", "PDF 打印", "Anki 卡组迁移",
                                        "G3 全量数据可带走"], "fs": 8.6}),
        _note(d),
    ])


# ================================================================ 图 3-7 环形闭环 + 时间轴
def _a37(d):
    import math
    nodes = ["生成计划", "间隔排程", "今日三卡", "测验自评", "掌握度更新"]

    def draw(cy):
        o = []
        _head(o, cy, d)
        _subtitle(o, cy, "左：五节点学习闭环（朱红＝错题回炉回授）　｜　右：R1–R4 间隔复习时间轴")
        b = cy + 64
        cx, cyc, rad = 177, b + 70, 62
        o.append(circ(cx, cyc, rad, "#F3FAFD", "#BED3DE", 0.9))
        for k, nm in enumerate(nodes):
            ang = math.radians(-90 + k * 72)
            nx, ny = cx + rad * math.cos(ang), cyc + rad * math.sin(ang)
            o.append(r(nx - 31, ny - 10, 62, 20, "#FFFFFF", INK, 0.9))
            o.append(t(nx, ny + 3.5, nm, 7.8, "middle", "bold"))
        o.append(t(cx, cyc - 4, "p(L) 掌握度", 8.6, "middle", "bold"))
        o.append(t(cx, cyc + 10, "θ = 0.85", 8.8, "middle", fill=RED))
        o.append(t(cx, cyc + 24, "低于阈值回炉", 7.8, "middle", fill=GREY))
        # 回授关系用圆外朱红箭头表示（含义见小标题，D 区卡片给出完整文字链）
        o.append(ln(X0 + 4, b + 138, X0 + 148, b + 138, RED, 1.2, arrow=True))
        # 右侧遗忘曲线轴
        x0, x1, ay = 340, 656, b + 96
        o.append(r(x0, b, 316, 132, "#FBFDFE", "#C6DEE9", 0.6))
        o.append(t(x0 + 8, b + 14, "间隔复习排程（R1–R4）与保持率示意", 8.8, weight="bold"))
        o.append(ln(x0 + 14, ay, x1 - 8, ay, INK, 0.9, arrow=True))
        o.append(ln(x0 + 14, b + 34, x0 + 14, ay, INK, 0.9))
        o.append(t(x0 + 18, b + 32, "R(t)", 7.8, fill=GREY))
        for yy, lab in [(b + 48, "R*=0.90"), (b + 76, "θ=0.85")]:
            o.append(ln(x0 + 14, yy, x1 - 12, yy, "#BED3DE", 0.6, "3 3"))
            # 标注垫浅底，避免折线穿字
            o.append('<rect x="%d" y="%d" width="56" height="13" fill="#FFFFFF" opacity="0.92"/>'
                     % (x1 - 72, yy - 15))
            o.append(t(x1 - 14, yy - 3, lab, 7.6, "end", fill=GREY))
        curve = [(350, 46), (378, 68), (410, 80), (450, 50), (480, 68),
                 (530, 54), (562, 76), (610, 58), (646, 82)]
        o.append(path("M " + " L ".join(f"{x},{b+y}" for x, y in curve), INK, 1.1))
        for x, lab in [(450, "R1 1d"), (490, "R2 3d"), (545, "R3 7d"), (610, "R4 14d")]:
            o.append(ln(x, ay, x, ay - 4, INK, 0.8))
            o.append(t(x, ay + 12, lab, 7.6, "middle", fill="#2B3237"))
        o.append(t(x0 + 8, b + 124, "示意曲线（非实测）｜R(t)=e^(−t/S)｜Cepeda 2006 · 254 项元分析",
                   7.7, fill="#3C464D"))
        return "\n".join(o)
    return draw


def _b37(d):
    def draw(cy):
        o = []
        o.append(ln(X0 + 16, cy + 6, X0 + 16, cy + 154, "#BED3DE", 1.0))
        for k, row in enumerate(d["funcs"]):
            y = cy + k * 26
            o.append(circ(X0 + 16, y + 12, 9, "#FFFFFF", INK, 0.9))
            o.append(t(X0 + 16, y + 15, str(k + 1), 8.2, "middle", "bold"))
            o.append(r(X0 + 32, y, 600, 24, "#FFFFFF" if k % 2 == 0 else "#F3FAFD",
                       "#E1EFF6", 0.5))
            o.append(t(X0 + 40, y + 16, row[0] + "　" + row[1], 8.8, weight="bold"))
            o.append(t(X0 + 190, y + 16, row[2], 8.2, fill="#3C464D"))
            _chip(o, X0 + 552, y + 4, 72, row[3])
        return "\n".join(o)
    return draw


def fig_3_7(d):
    theory = [
        ["Ebbinghaus 1885 / SM-2 / FSRS-6", "R1–R4 = 1/3/7/14 天", "R(t)=e^(−t/S) 驱动排程", "R*=0.90，θ=0.85"],
        ["间隔效应 Cepeda 2006", "间隔步长可配置常量", "254 项元分析：拉长间隔优于集中复习", "参数写入常量并落库"],
        ["BKT 掌握度 Corbett 1994", "p(L) 更新 / θ 阈值", "答题序列更新，低于阈值触发回炉", "四条主路径 100%（G2/G5）"],
    ]
    return _emit(d, "Closed Loop & Spacing Timeline", [
        ("A　学习闭环环形回路 + R1–R4 间隔复习时间轴", "raw", {"h": 208, "svg": _a37(d)}),
        ("B　六项功能纵向时间线（编号 / 说明 / 落点）", "raw", {"h": 160, "svg": _b37(d)}),
        ("C　理论模型 · 可配置参数 · 落地机制 · 验收", "grid", {
            "widths": [168, 150, 160, 154],
            "headers": ["理论模型 / 依据", "可配置参数", "落地机制", "可核验验收"],
            "aligns": A, "rows": theory, "rh": 30, "font": 8.4, "hf": 8.8}),
        ("", "band", {"h": 26, "items": ["R(t)=e^(−t/S)", "R*=0.90", "θ=0.85",
                                        "R1–R4 = 1 / 3 / 7 / 14 天"], "fs": 8.8}),
        ("D　闭环合龙的两个判定条件", "cards", {"h": 68, "items": [
            ("保持率目标", ["R*=0.90 为排程目标", "低于 θ=0.85 触发回炉", "公式推导见图 3-10"], "target"),
            ("回授与重排", ["错题回炉重新索引 / 再生成", "执行结果回流重排计划", "图 3-2 朱红回授线"], "loop"),
        ], "gap": 10, "tsize": 9.4, "lsize": 8.4}),
        _note(d),
    ])


# ================================================================ 图 3-8 仪表盘 + 收窄漏斗
def _a38(d):
    kpis = [("来源覆盖率", "100%", "回答必带来源定位"),
            ("上下文上限", "50 段", "Chroma 双索引"),
            ("交互时延", "P95 ≤3 s", "G2 验收口径"),
            ("评测样本", "40 份", "字段完整率 ≥95%")]

    def draw(cy):
        o = []
        _head(o, cy, d)
        _subtitle(o, cy, "学习状态仪表盘：关键指标宫格 + 成长轨迹示意 + 阶段复盘口径")
        b = cy + 64
        w, gap = 152, 8
        for k, (nm, val, sub) in enumerate(kpis):
            x = X0 + k * (w + gap)
            o.append(r(x, b, w, 46, "#E4F3FB", INK, 0.8))
            o.append(t(x + 8, b + 13, nm, 8.2, weight="bold", fill="#3C464D"))
            o.append(t(x + 8, b + 32, val, 13.0, weight="bold", fill=RED))
            o.append(t(x + w - 8, b + 40, sub, 7.5, "end", fill=GREY))
        y = b + 52
        o.append(r(X0, y, CW, 70, "#FBFDFE", "#C6DEE9", 0.6))
        o.append(t(X0 + 8, y + 13, "成长记录 / 学习轨迹（柱高为示意，非实测数据）", 8.6, weight="bold"))
        heights = [18, 26, 22, 34, 30, 38, 33, 44, 39, 47, 42, 50]
        for k, hh in enumerate(heights):
            x = X0 + 14 + k * 22
            o.append(r(x, y + 60 - hh, 12, hh, "#D8E9F1" if k % 2 == 0 else "#BED3DE",
                       "#9AAAB3", 0.5))
        o.append(ln(X0 + 8, y + 60, X0 + 286, y + 60, INK, 0.7))
        o.append(t(X0 + 8, y + 68, "周 1", 7.4, fill=GREY))
        o.append(t(X0 + 268, y + 68, "周 12", 7.4, "end", fill=GREY))
        o.append(ln(X0 + 296, y + 6, X0 + 296, y + 64, "#E1EFF6", 0.6))
        for k, s in enumerate(["F33 成长记录把轨迹反馈给学习者，",
                               "支持阶段复盘与自我调节；F31 历史任务",
                               "面板提供回看与断点续跑入口，两者",
                               "共同构成「可读、可问、可核」的证据面。"]):
            o.append(t(X0 + 306, y + 18 + k * 13, s, 8.0, fill="#3C464D"))
        return "\n".join(o)
    return draw


def _b38(d):
    stages = [("① 自然语言提问", "用户问题"), ("② 意图解析（轻档）", "意图 + 参数"),
              ("③ 白名单查询", "结果集 / 上下文"), ("④ 契约校验", "合规结果"),
              ("⑤ 图表与答案渲染", "图表 + 来源定位")]

    def draw(cy):
        o = []
        widths = [632, 548, 464, 380, 296]
        for k, ((nm, prod), w) in enumerate(zip(stages, widths)):
            x = X0 + (CW - w) / 2
            y = cy + k * 20
            o.append(r(x, y, w, 17, "#FFFFFF" if k % 2 == 0 else "#E4F3FB", INK, 0.8))
            o.append(t(x + 8, y + 12, nm, 8.4, weight="bold"))
            o.append(t(x + w - 8, y + 12, "→ " + prod, 7.9, "end", fill=GREY))
            if k < 4:
                o.append(ln(340, y + 17, 340, y + 20, "#83949E", 0.8, arrow=True))
        return "\n".join(o)
    return draw


def _c38(d):
    def draw(cy):
        o = []
        w, h, gap = 312, 70, 8
        for k, row in enumerate(d["funcs"]):
            c, rr = k % 2, k // 2
            x, y = X0 + c * (w + gap), cy + rr * (h + gap)
            o.append(r(x, y, w, h, "#FFFFFF", INK, 0.8))
            o.append(r(x, y, 34, h, "#EEF7FB", INK, 0.6))
            o.append(t(x + 17, y + 22, row[0], 8.6, "middle", "bold"))
            o.append(t(x + 44, y + 18, row[1], 9.4, weight="bold"))
            for j, s in enumerate(_wrap(row[2], 30, 2)):
                o.append(t(x + 44, y + 34 + j * 12, s, 8.2, fill="#3C464D"))
            _chip(o, x + w - 62, y + 6, 54, row[3])
            o.append(t(x + 44, y + 63, "出处：产品报告 第四章（八）", 7.5, fill="#83949E"))
        return "\n".join(o)
    return draw


def fig_3_8(d):
    return _emit(d, "Dashboard Grid & Query Funnel", [
        ("A　学习状态仪表盘（KPI 宫格 + 成长轨迹示意）", "raw", {"h": 188, "svg": _a38(d)}),
        ("B　问数 / 问答五级收窄漏斗（每级标注产物）", "raw", {"h": 106, "svg": _b38(d)}),
        ("C　四项功能 2×2 大卡（编号 / 说明 / 落点 / 出处）", "raw", {"h": 148, "svg": _c38(d)}),
        _theory_grid(d, tag="D"),
        _note(d),
    ])


# ================================================================ 图 3-9 治理金字塔 + 矩阵
def _a39(d):
    layers = [("① 身份与会话", 84, 122), ("② 配额与成本", 122, 172),
              ("③ 任务与审计", 172, 226), ("④ 数据可携带", 226, 276)]
    ctrl = [["身份", "Cookie + Argon2id", "G7 安全域"],
            ["成本", "日阈值自动降档", "F35 / 图 5-2"],
            ["数据", "全量导出 / 版本快照", "G3 / G4"],
            ["外链", "截图走本域代理", "F38 / 防盗链"],
            ["门禁", "G1–G7 逐项核验", "图 6-2"]]

    def draw(cy):
        o = []
        _head(o, cy, d)
        _subtitle(o, cy, "左：四层治理金字塔　｜　右：治理对象 × 控制手段 × 验收出处对照矩阵")
        b = cy + 64
        for k, (nm, wt, wb) in enumerate(layers):
            y = b + k * 36
            o.append(_trap(162, y, wt, wb, 33, "#FFFFFF" if k % 2 == 0 else "#E4F3FB"))
            o.append(t(162, y + 21, nm, 8.8, "middle", "bold"))
        x = 312
        o.append(t(x, b + 6, "治理对象 × 控制手段 × 验收出处", 8.6, weight="bold"))
        cols = [56, 178, 110]
        xs = [x]
        for w in cols:
            xs.append(xs[-1] + w)
        o.append(r(x, b + 12, 344, 18, INK, INK, 0.6))
        for j, hh in enumerate(["层", "控制手段", "验收 / 出处"]):
            o.append(t(xs[j] + 5, b + 25, hh, 8.2, weight="bold", fill="#FFFFFF"))
        for k, row in enumerate(ctrl):
            y = b + 30 + k * 22
            o.append(r(x, y, 344, 22, "#FFFFFF" if k % 2 == 0 else "#F3FAFD", "#C6DEE9", 0.5))
            for j, c in enumerate(row):
                o.append(t(xs[j] + 5, y + 15, c, 8.0,
                           weight="bold" if j == 0 else "", fill="#2B3237"))
            for j in range(1, 3):
                o.append(ln(xs[j], y, xs[j], y + 22, "#E1EFF6", 0.5))
        return "\n".join(o)
    return draw


def _c39(d):
    def draw(cy):
        o = []
        for k, row in enumerate(d["theory"]):
            y = cy + k * 45
            o.append(r(X0, y, CW, 40, "#FBFDFE", "#C6DEE9", 0.6))
            o.append(r(X0, y, 34, 40, INK, INK, 0.6))
            o.append(t(X0 + 17, y + 25, "①②③"[k], 11, "middle", "bold", fill="#FFFFFF"))
            o.append(t(X0 + 44, y + 16, row[0], 9.2, weight="bold"))
            o.append(t(X0 + 44, y + 31, "落地：" + row[1], 8.2, fill="#3C464D"))
            o.append(t(X0 + 400, y + 16, "验收：" + row[2], 8.2, fill="#2B3237"))
            o.append(t(X0 + 400, y + 31, "口径与图 6-2 / 第 5 章一致", 7.7, fill=GREY))
        return "\n".join(o)
    return draw


def fig_3_9(d):
    return _emit(d, "Governance Pyramid & Control Matrix", [
        ("A　四层治理金字塔 + 治理对照矩阵", "raw", {"h": 216, "svg": _a39(d)}),
        ("B　五项功能与落点（编号 / 说明 / 落点）", "grid", {
            "widths": [52, 132, 300, 148], "headers": ["编号", "功能", "说明", "落点"],
            "aligns": A, "rows": d["funcs"], "rh": 32, "font": 8.8}),
        ("C　三条治理原则论证（理论 → 落地 → 验收）", "raw", {"h": 136, "svg": _c39(d)}),
        ("", "band", {"h": 26, "items": ["最小权限", "可解释 · 可回退", "预算约束下的可用性",
                                        "G1–G7 上线门禁"], "fs": 8.6}),
        _note(d),
    ])


LAYOUTS = {"3-4": fig_3_4, "3-5": fig_3_5, "3-6": fig_3_6,
           "3-7": fig_3_7, "3-8": fig_3_8, "3-9": fig_3_9}


def domain_fig(d):
    return LAYOUTS[d["no"]](d)
