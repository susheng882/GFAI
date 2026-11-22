# -*- coding: utf-8 -*-
"""第二轮修正：流程图连线避让、曲线标注、底部补框，以及统一化旧图的 Logo / 旧图例残留清理。"""
import re
from pathlib import Path
from lxml import etree

ROOT = Path(__file__).parent
Q = "{http://www.w3.org/2000/svg}"


def patch(path, rules):
    s = path.read_text(encoding="utf-8")
    for old, new in rules:
        n = s.count(old)
        print(("  ok  " if n else "  MISS"), path.name, "x", n, "|", old[:56].replace("\n", " "))
        if n:
            s = s.replace(old, new)
    path.write_text(s, encoding="utf-8")


RA = [
    ('    b.append(t(232, 314, "无复习：R(t)=e^(−t/S)", 7.6, fill=INK))\n', ''),
    ('"每次成功复习抬升起点并增大记忆强度 S；R(t)<θ 触发回炉，S 减半。"',
     '"无复习曲线 R(t)=e^(−t/S)；每次成功复习抬升起点并增大 S；R(t)<θ 触发回炉，S 减半。"'),
    ("    yy = y + 10 + hh2 + 6", "    yy = y + 10 + hh2 + 12"),
]

RB = [
    # 图 2-2 异常路径改为走节点下方，不穿「产物写 PG」
    ('    b.append(path("M 362,410 L 580,410 L 580,432", stroke=RED, dash="4 3", arrow=True))\n'
     '    b.append(t(386, 426, "重试耗尽 → 死信（不无限重试）", 7.2, fill=RED))',
     '    b.append(path("M 362,432 L 362,452 L 580,452 L 580,434", stroke=RED, dash="4 3", arrow=True))\n'
     '    b.append(t(386, 446, "重试耗尽 → 死信（不无限重试）", 7.2, fill=RED))'),
    # 图 3-3 拒答路径避开泳道上边框
    ('    b.append(path("M 277,204 L 277,170 L 159,170 L 159,338", stroke=RED, dash="4 3", arrow=True))\n'
     '    b.append(t(284, 166, "否 → 拒答", 7.0, fill=RED))',
     '    b.append(path("M 230,204 L 230,316 L 159,316 L 159,338", stroke=RED, dash="4 3", arrow=True))\n'
     '    b.append(t(238, 310, "否 → 拒答", 7.0, fill=RED))'),
    # 图 3-3 降级路径与标注错开
    ('    b.append(path("M 513,282 L 590,282 L 590,430 L 159,430 L 159,382", stroke=RED, dash="4 3", arrow=True))\n'
     '    b.append(t(330, 424, "空集 / 越权 / 契约自修复失败 → 降级提示（不返回编造数据）", 7.2, fill=RED))',
     '    b.append(path("M 513,282 L 590,282 L 590,436 L 159,436 L 159,382", stroke=RED, dash="4 3", arrow=True))\n'
     '    b.append(t(330, 428, "空集 / 越权 / 契约自修复失败 → 降级提示（不返回编造数据）", 7.2, fill=RED))'),
    # 图 3-3 底部补「理论映射」框
    ('    b.append(t(X0, y + 78, "注 2：本图与图 3-2 成本护栏共用轻档路由与降级设施；与图 5-2 仪表盘模块对应。", 7.8, fill="#444444"))\n'
     '    return frame("NL 问数仪表盘五步链路流程图拆解",',
     '    b.append(t(X0, y + 78, "注 2：本图与图 3-2 成本护栏共用轻档路由与降级设施；与图 5-2 仪表盘模块对应。", 7.8, fill="#444444"))\n'
     '    y4 = y + 88\n'
     '    b.append(r(X0, y4, CW, 46, "#FAFAFA", INK, 0.8))\n'
     '    b.append(icon("brain", X0 + 10, y4 + 8, 0.66))\n'
     '    b.append(t(X0 + 34, y4 + 21, "理论映射：白名单模板＝降低外在负荷；先判定后生成＝可解释 AI；拒答优于编造＝可验证性优先", 8.0))\n'
     '    b.append(t(X0 + 34, y4 + 37, "（对应技术方案 3.9 的认知负荷理论与元认知反馈，见图 4-3）", 7.6, fill=GREY))\n'
     '    return frame("NL 问数仪表盘五步链路流程图拆解",'),
]

LEGEND_KEYS = ("数据出处：", "◆ 架构评审新增", "★ 推荐方案", "● 完整支持",
               "价格为 2026-11-14 官网活动价快照", "◆ 评审新增", "实线＝同步")


def clean_normalized():
    files = [p for p in ROOT.glob("*.svg")
             if p.name.startswith(("图2-1_", "图3-1_", "图3-2_", "图4-1_", "图5-1_",
                                   "图5-2_", "图5-4_", "图6-1_", "图7-1_", "图9-1_"))]
    for p in files:
        s = p.read_text(encoding="utf-8")
        root = etree.fromstring(s.encode("utf-8"))
        target = None
        for g in root.iter(Q + "g"):
            tr = g.get("transform", "")
            if "scale(" in tr and "translate(" in tr:
                target = g
                break
        if target is None:
            print("  no embedded group", p.name)
            continue
        removed = 0
        for el in list(target):
            if not isinstance(el.tag, str):
                target.remove(el); removed += 1
                continue
            tag = etree.QName(el).localname
            txt = "".join(el.itertext()).strip()
            if tag == "text":
                try:
                    y = float(el.get("y", "999"))
                except ValueError:
                    y = 999
                if y < 70 or any(k in txt for k in LEGEND_KEYS):
                    target.remove(el); removed += 1
            elif tag == "g":
                ys = []
                for n in el.iter():
                    for a in ("y", "cy", "y1"):
                        v = n.get(a)
                        if v:
                            try: ys.append(float(v))
                            except ValueError: pass
                m = re.search(r"translate\([^,]+,\s*([-\d.]+)\)", el.get("transform", ""))
                if m:
                    try: ys.append(float(m.group(1)))
                    except ValueError: pass
                if ys and max(ys) < 70:
                    target.remove(el); removed += 1
            elif tag in ("circle", "rect", "line", "polyline", "path"):
                v = el.get("y") or el.get("cy") or el.get("y1")
                if v:
                    try:
                        if float(v) < 70:
                            target.remove(el); removed += 1
                    except ValueError:
                        pass
        p.write_text(etree.tostring(root, encoding="unicode"), encoding="utf-8")
        print("  cleaned", p.name, "removed", removed)


if __name__ == "__main__":
    patch(ROOT / "_build_figs_a.py", RA)
    patch(ROOT / "_build_figs_b.py", RB)
    clean_normalized()
