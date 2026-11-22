# -*- coding: utf-8 -*-
"""【已停用 · 历史保留】GrowthForward 学术主题色系统 · 蓝黄版（2026-11-15）。

2026-11-16 全册已改为 Apple 极简体系（白 / 石墨 / 前进蓝 / 火花橙），
主题色改由 _patch_apple_theme.py + _gf_brand.py 维护；本脚本会把颜色改回旧蓝黄，
请勿再运行，仅作为换色逻辑的历史参考保留。

参考图五色：深墨 #212121 / 浅蓝 #CDE9F6 / 亮蓝 #8ED7FE / 亮黄 #F4FF8D / 奶油黄 #F8EDB8，
视觉语言是「深底 + 大圆角亮色块 + 深墨字」。A4 学术图册内页不能整页深底（印刷与可读性），
因此做语义化翻译：

  深墨      → 正文文字 / 外框 / 封面封底底色
  深蓝(派生) → 表头、区块标签、主标题（由 #8ED7FE 降明度得到，白字对比 ≈ 5:1）
  亮蓝/浅蓝 → 强调条、斑马行、卡片浅底
  亮黄/奶油黄 → 关键数据、锚点、次级浅底
  朱红      → 风险语义色，唯一保留的例外

用法：D:/anaconda3/python.exe _theme.py
  · 若当前 SVG 还是上一版暖橙，会先从 归档/_主题色改版前备份_2026-11-15/_src_*.svg 恢复黑白原版
  · 对 40 张 SVG 语义化换色（幂等），并把常量写回图形库，保证以后重建不丢
"""
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
ARCH = ROOT.parent.parent.parent / "归档" / "_主题色改版前备份_2026-11-15"
ARCH.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- 色板
P = dict(
    ink="#212121",        # 深墨：正文、外框、封面封底底
    primary="#1B6E9C",    # 派生主蓝：表头 / 区块标签 / 主标题（由亮蓝降明度，保证白字可读）
    accent="#8ED7FE",     # 亮蓝：强调、箭头、色块
    gold="#C9A227",       # 派生深黄：亮黄上的文字（亮黄底不可写白字）
    yellow="#F4FF8D",     # 亮黄：关键数据 / 高亮
    cream="#F8EDB8",      # 奶油黄：次级浅底
    risk="#B4472F",       # 朱红：风险 / 异常（语义色，保留）
    slate="#55626A",      # 冷灰：辅助文字
    line="#C6DEE9",       # 浅蓝边框
    line_soft="#E7F2F8",  # 更浅边框
    tint="#E4F3FB",       # 蓝浅底：斑马行 / 表头下衬
    tint_soft="#F3FAFD",  # 更浅蓝底：卡片
    tint_warm="#FFF4D6",  # 黄浅底：交替斑马行 / 锚点
    paper="#FFFFFF",      # 白纸底
)

# 旧黑白灰阶 → 冷蓝灰阶（兜底映射）；两个浅灰分别落到蓝/黄，形成拼色斑马
GRAYS = {
    "#1F2328": P["ink"], "#333333": "#2B3237", "#3D3D3D": "#353F46",
    "#444444": "#3C464D", "#555555": "#4E5A62", "#666666": P["slate"],
    "#6B6B6B": "#5B6871", "#777777": "#6C7B85", "#888888": "#83949E",
    "#8A8A8A": "#8FA1AB", "#999999": "#9AAAB3", "#9A9A9A": "#9AAAB3",
    "#AAAAAA": "#B4C3CB", "#BBBBBB": "#BED3DE", "#BDBDBD": "#BED3DE",
    "#C8C8C8": "#C6DEE9", "#CCCCCC": P["line"], "#D9D9D9": "#D8E9F1",
    "#DDDDDD": "#DCEBF2", "#E4E4E4": "#E1EFF6", "#E8E8E8": "#E7F2F8",
    "#EDEDED": "#ECF5FA", "#EFEFEF": "#EEF7FB", "#F0F0F0": "#F0F8FC",
    "#F4F4F4": P["tint"], "#F7F7F7": P["tint_warm"], "#FAFAFA": P["tint_soft"],
    "#FCFCFC": "#FBFDFE",
}

# 上一版暖橙留在图形库里的硬编码，统一冷化
WARM2COOL = {
    "#1D2330": P["ink"], "#C9531B": P["primary"], "#FF6A2A": P["accent"],
    "#D9971A": P["gold"], "#FFB020": P["yellow"], "#6B625B": P["slate"],
    "#D8C7B5": P["line"], "#EBDFD1": P["line_soft"], "#FFF2E4": P["tint"],
    "#FFF9F2": P["tint_soft"], "#FFFDFB": P["paper"], "#FFF6EC": P["tint_warm"],
    "#2E2B28": "#2B3237", "#39342F": "#353F46", "#4A423C": "#3C464D",
    "#5C534C": "#4E5A62", "#6F655C": "#5B6871", "#7A6F66": "#6C7B85",
    "#9C8D7E": "#83949E", "#A09485": "#8FA1AB", "#B09E8C": "#9AAAB3",
    "#C2B2A0": "#B4C3CB", "#CDBCA9": "#BED3DE", "#E0D2C2": "#D8E9F1",
    "#E4D7C8": "#E1EFF6", "#EADDD0": "#E7F2F8", "#EFE5D9": "#ECF5FA",
    "#F2E9DF": "#EEF7FB", "#F4EBE1": "#F0F8FC", "#F5EDE3": "#FBFDFE",
    "#FFFBF5": "#FBFDFE", "#F0C39E": P["accent"], "#9C8D7E": "#83949E",
}

TOKEN = {v: "__GF_%s__" % k.upper() for k, v in P.items()}
TOKEN_REV = {v: k for k, v in TOKEN.items()}


def _bold(attrs):
    return 'font-weight="bold"' in attrs


def _size(attrs):
    m = re.search(r'font-size="([\d.]+)"', attrs)
    return float(m.group(1)) if m else 0.0


def _color(attrs, attr, tag):
    """把单个颜色属性按元素语义解析成占位符。"""
    pat = r'(%s=")(#[0-9A-Fa-f]{6})(")' % attr
    m = re.search(pat, attrs)
    if not m:
        return attrs
    c = m.group(2).upper()
    if c == "#B4472F":          # 风险朱红是独立语义色，不动
        return attrs
    if c == "#1F2328":
        if tag == "rect" and attr == "fill":
            new = TOKEN[P["primary"]]        # 深色矩形＝表头 / 深色带 → 主蓝
        elif tag in ("line", "path", "polyline", "polygon", "circle") and attr == "stroke":
            sw = re.search(r'stroke-width="([\d.]+)"', attrs)
            new = TOKEN[P["primary"]] if sw and float(sw.group(1)) >= 1.2 else TOKEN[P["ink"]]
        elif tag in ("path", "circle") and attr == "fill":
            new = TOKEN[P["primary"]]        # 实心箭头 / 圆点
        elif attr == "stroke":
            new = TOKEN[P["ink"]]
        else:
            new = TOKEN[P["ink"]]
    elif c == "#FFFFFF":
        new = TOKEN[P["paper"]] if tag == "rect" and attr == "fill" else "__GF_KEEPWHITE__"
    else:
        new = GRAYS.get(c, c)
        if new == c:
            return attrs
        new = "__GF_G_%s__" % new[1:].upper()
    return attrs[:m.start()] + m.group(1) + new + m.group(3) + attrs[m.end():]


def _text_tag(m):
    attrs, inner = m.group(1), m.group(2)
    was_white = re.search(r'fill="#FFFFFF"', attrs) is not None  # 表头 / 阶段带反白字不参与强调改色
    is_bold = _bold(attrs)
    size = _size(attrs)
    plain = re.sub(r"<[^>]+>", "", inner)
    # 主标题 / 图题 / A–E 区块标签 / 带圈编号 → 主蓝
    emphasis = is_bold and (
        size >= 11 or re.match(r"^[A-E][\u3000 ]", plain) or
        re.match(r"^[①-⑩◆]", plain) or plain.startswith("图 ")
    )
    attrs = _color(attrs, "fill", "text")
    if emphasis and 'fill="' in attrs and not was_white:
        attrs = re.sub(r'fill="(?:__GF_[^"]*__|#[0-9A-Fa-f]{6})"',
                       'fill="' + TOKEN[P["primary"]] + '"', attrs, count=1)
    inner = _generic(inner)
    return attrs + inner + m.group(3)


def _other_tag(m):
    tag, attrs = m.group(1).lower(), m.group(2)
    if tag in ("text", "tspan"):
        return m.group(0)
    for attr in ("fill", "stroke"):
        attrs = _color(attrs, attr, tag)
    return "<%s%s%s>" % (m.group(1), attrs, m.group(3))


def _generic(s):
    """兜底：把残留旧色值换成冷色阶（跳过占位符）。"""
    def rep(mm):
        c = mm.group(0).upper()
        if c in GRAYS:
            return "__GF_G_%s__" % GRAYS[c][1:].upper()
        if c in WARM2COOL:
            return "__GF_G_%s__" % WARM2COOL[c][1:].upper()
        return c
    return re.sub(r"#[0-9A-Fa-f]{6}", rep, s)


def theme_svg(s):
    s = re.sub(r'(<text\b[^>]*>)(.*?)(</text>)', _text_tag, s, flags=re.S)
    s = re.sub(r'<([a-zA-Z][\w:-]*)([^>]*?)(/?)>', _other_tag, s)
    s = _generic(s)
    for tok, val in TOKEN_REV.items():
        s = s.replace(tok, val)
    s = s.replace("__GF_KEEPWHITE__", "#FFFFFF")
    s = re.sub(r"__GF_G_([0-9A-F]{6})__", lambda m: "#" + m.group(1), s)
    # 亮色块注入：把次级浅灰蓝/浅黄在非文本元素上升格为参考图的亮蓝 / 浅蓝 / 奶油黄。
    # 只动 rect/path/line 等图形元素的 fill|stroke，绝不动文字，避免浅色字看不清。
    inject = {"#BED3DE": P["accent"], "#DCEBF2": "#CDE9F6",
              "#FFF4D6": P["cream"], "#F3FAFD": P["tint"]}
    for old, new in inject.items():
        s = re.sub(r'(<(?:rect|path|line|polyline|polygon|circle)\b[^>]*?'
                   r'(?:fill|stroke)=")' + old + r'(")',
                   lambda m, v=new: m.group(1) + v + m.group(2), s)
    return s


LIB_PATCH = [
    ("_figlib.py",
     'INK = "#1D2330"       # 深墨 · 正文与外框\n'
     'PRIMARY = "#C9531B"   # 主橙 · 表头 / 区块标签 / 主标题\n'
     'GOLD = "#D9971A"      # 金黄 · 次级高亮\n'
     'PAPER = "#FFFDFB"     # 暖白 · 页面底\n'
     'GREY = "#6B625B"\nLIGHT = "#FFF2E4"\nRED = "#B4472F"',
     'INK = "#212121"       # 深墨 · 正文与外框（参考图底色）\n'
     'PRIMARY = "#1B6E9C"   # 主蓝 · 表头 / 区块标签 / 主标题（亮蓝降明度派生）\n'
     'ACCENT = "#8ED7FE"    # 亮蓝 · 强调 / 箭头 / 色块\n'
     'YELLOW = "#F4FF8D"    # 亮黄 · 关键数据高亮\n'
     'CREAM = "#F8EDB8"     # 奶油黄 · 次级浅底\n'
     'GOLD = "#C9A227"      # 深黄 · 亮黄底上的文字\n'
     'PAPER = "#FFFFFF"     # 白纸底\n'
     'GREY = "#55626A"\nLIGHT = "#E4F3FB"\nRED = "#B4472F"'),
]


def main():
    svgs = sorted(ROOT.glob("*.svg"))
    # 幂等：若当前还是上一版暖橙，从黑白原版备份恢复后再映射
    warm = any("#C9531B" in p.read_text(encoding="utf-8") for p in svgs)
    backups = sorted(ARCH.glob("_src_*.svg"))
    if warm and backups:
        for b in backups:
            shutil.copy2(b, ROOT / b.name[5:])
        print("已从黑白原版备份恢复 SVG：", len(backups))
    svgs = sorted(ROOT.glob("*.svg"))
    print("待处理 SVG：", len(svgs))
    for p in svgs:
        s = p.read_text(encoding="utf-8")
        out = theme_svg(s)
        p.write_text(out, encoding="utf-8")
        print("  ", p.name[:26], "| 主蓝", out.count(P["primary"]),
              "| 蓝浅底", out.count(P["tint"]), "| 黄浅底", out.count(P["tint_warm"]))
    for fname, old, new in LIB_PATCH:
        p = ROOT / fname
        s = p.read_text(encoding="utf-8")
        if old not in s:
            if new in s:
                print("  图形库已应用：", fname)
                continue
            raise SystemExit("图形库未命中：%s / %s" % (fname, old[:50]))
        p.write_text(s.replace(old, new, 1), encoding="utf-8")
        print("  图形库已同步：", fname)
    # 图形库里所有硬编码暖色 / 旧灰阶统一冷化，保证以后重建直接产出蓝黄版
    for fname in ("_figlib.py", "_figlib2.py", "_figlib_bp.py", "_domain_layouts.py",
                  "_build_bp_a.py", "_build_bp_b.py", "_build_bp_c.py", "_build_figs_a.py",
                  "_build_figs_c.py", "_booklet.py"):
        p = ROOT / fname
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8")
        out = re.sub(r"#[0-9A-Fa-f]{6}",
                     lambda m: WARM2COOL.get(m.group(0).upper(),
                                             GRAYS.get(m.group(0).upper(), m.group(0))), s)
        if out != s:
            p.write_text(out, encoding="utf-8")
            print("  硬编码色已冷化：", fname)
    bad = []
    for p in ROOT.glob("*.svg"):
        s = p.read_text(encoding="utf-8")
        for c in ("#1F2328", "#C9531B", "#FFF2E4", "#D8C7B5"):
            if c in s:
                bad.append((p.name, c))
    print("残留旧暖色 / 旧灰阶：", bad[:12] or "无")


if __name__ == "__main__":
    raise SystemExit("[已停用] 当前主题为 Apple 极简体系；请勿运行本脚本。"
                     "如需重刷配色请使用 _patch_apple_theme.py。")
    main()
