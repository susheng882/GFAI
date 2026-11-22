# -*- coding: utf-8 -*-
"""_booklet.py → Apple 极简版式（2026-11-16）。
只替换 CSS 覆盖层、色板、品牌片段与页面函数，前 300 行的图录数据保持不动。
"""
from pathlib import Path
import re

F = Path(__file__).parent / '_booklet.py'
s = F.read_text(encoding='utf-8')

# ---------------------------------------------------------------- 1. import
s = s.replace('from playwright.sync_api import sync_playwright',
              'from playwright.sync_api import sync_playwright\nimport _gf_brand as B')

# ---------------------------------------------------------------- 2. CSS 覆盖层
NEW_CSS = r'''
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
'''

i = s.index('/* ===== GF 蓝黄学术主题色')
j = s.index('\n"""', i)
s = s[:i] + NEW_CSS + s[j:]

s = re.sub(r'^PALETTE = .*$',
           'PALETTE = [(\'石墨 Graphite\', \'#1D1D1F\'), (\'前进蓝 Forward\', \'#0071E3\'), '
           '(\'冰蓝 Ice\', \'#EAF3FF\'), (\'云雾 Mist\', \'#F5F5F7\'), '
           '(\'银线 Silver\', \'#D2D2D7\'), (\'火花橙 Spark\', \'#FF9F0A\')]',
           s, flags=re.M)

# ---------------------------------------------------------------- 3. 品牌片段 / 页眉 / 图页
def cut(a, b, new):
    global s
    i = s.index(a)
    j = s.index(b, i)
    s = s[:i] + new + s[j:]


cut('def brand_svg(', 'def svg_inline(', '''def brand_svg(name, prefix="b", white=False, recolor=True):
    """兼容旧调用：统一返回新的 Apple 极简品牌资产。"""
    if name.startswith("mascot"):
        return B.mascot(prefix)
    if name.startswith("logo"):
        return B.mark(stroke='#FFFFFF' if white else B.BLUE,
                      arrow='#FFFFFF' if white else B.SPARK)
    return B.mark()


''')

cut('def head(right):', 'def figure_page(', '''def head(right):
    return (f'<div class="phead"><span>{B.head_mark()}GrowthForward · 商业计划书图表册</span>'
            f'<span class="r">{html.escape(right)}</span></div>')


''')

cut('def figure_page(', 'def chapter_page(', '''def figure_page(idx, d):
    pts = '　'.join(f'{i}. {html.escape(p)}' for i, p in enumerate(d['pts'], 1))
    foot = (f'<div class="pfoot"><span>{html.escape(d["no"])}　{html.escape(d["name"])}</span>'
            f'<span>出处：{html.escape(d["src"])}　·　第 {idx} 图 / 共 {len(F)} 图</span></div>')
    return (f'<div class="page">{head(d["chap"] + "　|　" + d["no"] + "　" + d["name"])}'
            f'<div class="figbox"><div class="figwm">{B.mark()}</div>'
            f'<div class="figtag">GFLC · 2026</div>{svg_inline(SRC / d["f"])}</div>'
            f'<div class="keypts"><b>要点</b>　{pts}</div>{foot}</div>')


''')

# 扉页水印
s = s.replace('return f\'\'\'<div class="page part">{head(',
              'return f\'\'\'<div class="page part"><div class="partwm">{B.mark()}</div>{head(')

# 目录页图形标
s = s.replace('{head(f"图 目 录 · 第 {part} / {total_parts} 部分")}<h2>',
              '{head(f"图 目 录 · 第 {part} / {total_parts} 部分")}'
              '<div class="tmark"><div class="ic">{B.mark()}</div>'
              '<span>GROWTHFORWARD · FIGURE BOOKLET</span></div><h2>')

# ---------------------------------------------------------------- 4. 封面
cut('def cover_page():', 'def toc_page(', '''def cover_page():
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
    return f\'\'\'<div class="page cover">
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
      </div></div>\'\'\'


''')

# ---------------------------------------------------------------- 5. 封底
cut('def back_page():', 'def main():', '''def back_page():
    sw = ''.join(f'<div class="sw"><div class="chip" style="background:{c}"></div>'
                 f'<div class="nm">{html.escape(n)}</div><div class="hx">{c}</div></div>'
                 for n, c in PALETTE)
    return f\'\'\'<div class="page back">
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
        <span>40 图 / 54 页 · A4 · 2026-11-16</span></div></div>\'\'\'


''')

F.write_text(s, encoding='utf-8')
print('patched', F.name, len(s), 'chars')
