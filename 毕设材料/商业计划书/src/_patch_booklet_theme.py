# -*- coding: utf-8 -*-

# [2026-11-16 已停用] 当前为 Apple 极简体系；本脚本会把主题/封面改回旧版，请勿运行，仅作历史留档。
raise SystemExit("[已停用] 历史改版脚本：当前主题由 _gf_brand.py / _patch_apple_theme.py / _booklet.py 维护")

"""把 GF 暖橙主题色延伸到册页 CSS，并用品牌 V2 资产重做封面 / 封底（2026-11-15）。"""
import re
from pathlib import Path

P = Path(__file__).parent / "_booklet.py"
S = P.read_text(encoding="utf-8")

OVERRIDE = """
/* ===== GF 暖橙学术主题色 · 覆盖层（2026-11-15） ===== */
html, body { background:#FFFDFB; color:#1D2330; }
.page { background:#FFFDFB; }
.phead { border-bottom:.7pt solid #C9531B; }
.phead > span:first-child { color:#C9531B; font-weight:bold; }
.phead .r { color:#1D2330; }
.figbox { border:.3pt solid #E4D7C8; background:#FFFDFB; }
.keypts { border:.4pt solid #E4D7C8; background:#FFF9F2; color:#4A423C; }
.pfoot { border-top:.7pt solid #C9531B; color:#4A423C; }
.toc th { border-top-color:#C9531B; border-bottom-color:#C9531B; }
.toc td { border-bottom-color:#E4D7C8; }
.toc .grp td { background:#FFF2E4; color:#C9531B; }
.toc .ch, .toc .note, .toc .lead { color:#6B625B; }
.part .phero { border-bottom:1.2pt solid #C9531B; }
.part .phero .num { color:#F0C39E; }
.part .phero .q b { color:#9C8D7E; }
.part .plabel { border-left-color:#C9531B; color:#C9531B; }
.part .plogic, .part .fcard ul { color:#4A423C; }
.part .kpis .k { border-color:#E4D7C8; background:#FFF9F2; }
.part .kpis .k .v { color:#C9531B; }
.part .kpis .k .n { border-top-color:#E4D7C8; color:#9C8D7E; }
.part .fcard { border-color:#E4D7C8; border-left-color:#C9531B; background:#FFFDFB; }
.part .fcard.x { border-left-color:#D9971A; background:#FFF6EC; }
.part .fcard .fh { border-bottom-color:#E4D7C8; }
.part .fcard .no, .part .fcard .anch b { color:#C9531B; }
.part .fcard .anch { background:#FFF2E4; border-left-color:#D9971A; color:#4A423C; }
.part .fcard .src { border-top-color:#D8C7B5; color:#9C8D7E; }
.part .plink { border-top-color:#D8C7B5; color:#6B625B; }

/* ===== 封面：暖橙渐变 + 品牌标 + 吉祥物 + 信息矩阵 ===== */
.cover { position:relative; justify-content:flex-start; align-items:stretch; text-align:left; padding:0; }
.cv-band { height:7mm; flex:0 0 auto;
  background:linear-gradient(100deg,#C9531B 0%,#FF6A2A 52%,#FFB020 100%); }
.cv-body { flex:1 1 auto; min-height:0; padding:6mm 12mm 4mm; display:flex; flex-direction:column; }
.cv-logo { width:98mm; margin-bottom:1mm; }
.cv-logo svg { width:100%; height:auto; display:block; }
.cv-mascot { position:absolute; right:11mm; top:13mm; width:31mm; }
.cv-mascot svg { width:100%; height:auto; display:block; }
.cv-kicker { margin-top:3mm; font-size:8.4pt; letter-spacing:2.2pt; color:#C9531B; font-weight:bold; }
.cv-title { margin-top:3mm; font-size:31pt; font-weight:bold; line-height:1.22; color:#1D2330;
  letter-spacing:-.4pt; }
.cv-title em { font-style:normal; color:#C9531B; }
.cv-sub { margin-top:2mm; font-size:15pt; letter-spacing:3.4pt; color:#1D2330; }
.cv-tagline { margin-top:2.5mm; font-size:9.2pt; color:#6B625B; letter-spacing:.4pt; }
.cv-rule { width:62mm; height:1.1mm; margin:4mm 0 0;
  background:linear-gradient(90deg,#C9531B,#FFB020); }
.cv-meta { margin-top:3mm; font-size:8.8pt; color:#4A423C; line-height:1.75; }
.cv-sec { margin-top:4.2mm; font-size:8pt; font-weight:bold; letter-spacing:1.6pt;
  color:#C9531B; border-left:2pt solid #C9531B; padding-left:2mm; }
.cv-chain { display:flex; gap:1.1mm; margin-top:1.8mm; }
.cv-chain .nd { flex:1; border:.4pt solid #E4D7C8; background:#FFF9F2; padding:1.6mm .5mm;
  text-align:center; font-size:7.4pt; line-height:1.35; color:#4A423C; }
.cv-chain .nd b { display:block; font-size:9pt; color:#C9531B; }
.cv-chain .nd:first-child { background:#C9531B; border-color:#C9531B; color:#FFFFFF; }
.cv-chain .nd:first-child b { color:#FFFFFF; }
.cv-facts { display:grid; grid-template-columns:repeat(4,1fr); gap:2mm; margin-top:1.8mm; }
.cv-facts .f { border:.4pt solid #E4D7C8; border-top:1.4pt solid #C9531B;
  background:#FFFDFB; padding:2.2mm 2.4mm; }
.cv-facts .f .v { font-size:16pt; font-weight:bold; color:#C9531B; line-height:1.1; }
.cv-facts .f .l { font-size:7.8pt; color:#6B625B; margin-top:1mm; }
.cv-list { display:grid; grid-template-columns:repeat(5,1fr); gap:1.4mm; margin-top:1.8mm;
  border:.4pt solid #E4D7C8; background:#FFF9F2; padding:2.4mm 3mm; }
.cv-list div { font-size:7.9pt; line-height:1.6; color:#4A423C; }
.cv-list b { color:#C9531B; font-size:8.2pt; }
.cv-palette { display:flex; gap:1.6mm; margin-top:1.8mm; }
.cv-palette .sw { flex:1; border:.4pt solid #E4D7C8; padding:1.5mm 1.4mm; background:#FFFDFB; }
.cv-palette .chip { height:5mm; border-radius:.6mm; margin-bottom:1.2mm; }
.cv-palette .nm { font-size:7.4pt; font-weight:bold; color:#1D2330; }
.cv-palette .hx { font-size:6.9pt; color:#9C8D7E; margin-top:.4mm; }
.cv-foot { margin-top:auto; padding-top:3mm; border-top:.5pt solid #D8C7B5;
  font-size:8.2pt; color:#6B625B; line-height:1.7; }

/* ===== 封底：深墨反白 + 主题色系统色卡 ===== */
.back { background:#1D2330; color:#EFE7DD; padding:10mm 12mm 8mm; }
.back .phead { border-bottom-color:#C9531B; color:#C9BCAE; }
.back .phead .r { color:#EFE7DD; }
.bk-logo { width:86mm; margin-top:9mm; }
.bk-logo svg { width:100%; height:auto; display:block; }
.bk-slogan { margin-top:2mm; font-size:9pt; letter-spacing:2.2pt; color:#FFB020; }
.bk-rule { width:100%; height:1mm; margin:5mm 0 0;
  background:linear-gradient(90deg,#C9531B,#FFB020 60%,#1D2330); }
.bk-h { text-align:center; font-size:17pt; letter-spacing:5pt; margin:6mm 0 4mm; color:#FFFFFF; }
.bk-grid { display:grid; grid-template-columns:1fr 1fr; gap:2.4mm 4mm; }
.bk-blk { border-top:.5pt solid #4A423C; padding-top:2mm; font-size:8.3pt; line-height:1.7;
  color:#D6CCC0; }
.bk-blk b { display:block; color:#FFB020; font-size:9pt; margin-bottom:1mm; letter-spacing:.6pt; }
.bk-blk.wide { grid-column:1 / -1; }
.bk-mascot { position:absolute; right:13mm; bottom:34mm; width:26mm; opacity:.95; }
.bk-mascot svg { width:100%; height:auto; display:block; }
.bk-pal { display:flex; gap:1.6mm; margin-top:5mm; }
.bk-pal .sw { flex:1; border:.4pt solid #4A423C; padding:1.6mm 1.4mm; background:#252C3A; }
.bk-pal .chip { height:6mm; border-radius:.6mm; margin-bottom:1.2mm; }
.bk-pal .nm { font-size:7.6pt; font-weight:bold; color:#FFFFFF; }
.bk-pal .hx { font-size:7pt; color:#A99C8E; margin-top:.4mm; }
.bk-foot { margin-top:auto; padding-top:3mm; border-top:.5pt solid #4A423C;
  display:flex; justify-content:space-between; font-size:8.2pt; color:#A99C8E; }
.bk-foot b { color:#FFB020; }
"""

BRAND_FN = '''
BRAND = Path(r"F:\\GrowthForward_AI学习伴侣\\brand_assets")


def brand_svg(name, prefix="b", white=False):
    """内联品牌矢量资产：去固定宽高、隔离渐变 id；white=True 生成深墨底反白版。"""
    s = (BRAND / name).read_text(encoding="utf-8")
    def fix(m):
        a = re.sub(r'\\s(?:width|height|preserveAspectRatio)\\s*=\\s*"[^"]*"', '', m.group(1))
        return '<svg' + a + ' preserveAspectRatio="xMidYMid meet">'
    s = re.sub(r'<svg([^>]*)>', fix, s, count=1)
    for i in re.findall(r'id="([^"]+)"', s):
        s = s.replace('id="%s"' % i, 'id="%s_%s"' % (prefix, i))
        s = s.replace('url(#%s)' % i, 'url(#%s_%s)' % (prefix, i))
    if white:
        s = s.replace('#1D2330', '#FFFFFF').replace('#8A909C', '#C9BCAB')
    return s


'''

PALETTE = [("深墨 Ink", "#1D2330"), ("主橙 Primary", "#C9531B"), ("亮橙 Accent", "#FF6A2A"),
           ("金黄 Gold", "#D9971A"), ("暖浅 Tint", "#FFF2E4"), ("暖白 Base", "#FFFDFB")]

COVER_FN = """def cover_page():
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
        <div class="cv-logo">{brand_svg("logo_primary.svg", "cv")}</div>
        <div class="cv-mascot">{brand_svg("mascot_wave.svg", "cvm")}</div>
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
        <div class="cv-sec">G F 主 题 色 系 统　·　暖橙学术版</div>
        <div class="cv-palette">{sw}</div>
        <div class="cv-foot">毕业设计材料　·　配套《产品报告 V2 完整版》《技术方案_GrowthForward.md》《BiliNote_深度拆解分析.md》<br/>
          2026 年 11 月 15 日　·　GrowthForward 成长向前</div>
      </div></div>\'\'\'


"""

BACK_FN = """def back_page():
    sw = ''.join(f'<div class="sw"><div class="chip" style="background:{c}"></div>'
                 f'<div class="nm">{html.escape(n)}</div><div class="hx">{c}</div></div>'
                 for n, c in PALETTE)
    return f\'\'\'<div class="page back">
      <div class="phead"><span>GrowthForward · 商业计划书图表册</span><span class="r">编制说明</span></div>
      <div class="bk-logo">{brand_svg("logo_primary.svg", "bk", white=True)}</div>
      <div class="bk-slogan">LEARN. GROW. KEEP MOVING FORWARD.</div>
      <div class="bk-rule"></div>
      <h2 class="bk-h">编 制 说 明</h2>
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
          GF 暖橙学术主题色：深墨 #1D2330 作正文、主橙 #C9531B 作表头与标题、金黄 #D9971A 作次级高亮，
          暖白 #FFFDFB / 暖浅 #FFF2E4 作底，风险项保留朱红 #B4472F 作独立语义色。
          采购与模型单价为 2026-11-14 官网实采；市场规模并列公开口径，收入与用户数显式标注为规划假设。</div>
        <div class="bk-blk wide"><b>源文件与重建</b>
          全部插图保留矢量 SVG 于「学术图表/src/」；_figlib / _figlib2 / _figlib_bp 为统一图形库，
          _build_figs_a / c / d / e / f 与 _build_bp_a / b / c / d 分组生成 40 张插图；
          _theme.py 负责主题色（幂等），_convert.py 导出 1588×2246 纯图，_booklet.py 合成 A4 册页。
          日常增量重建走「单独调生成器 → _convert.py → _booklet.py」，勿直接跑全量重建覆盖定点修订。</div>
      </div>
      <div class="bk-pal">{sw}</div>
      <div class="bk-mascot">{brand_svg("mascot_wave.svg", "bkm")}</div>
      <div class="bk-foot"><span><b>GrowthForward</b> 成长向前 · AI 学习伴侣</span>
        <span>40 图 / 54 页 · A4 · 2026-11-15</span></div></div>\'\'\'


"""

# ---- 1) 追加 CSS 覆盖层
anchor = '.back .blk b { display:block; margin-bottom:1.5mm; }\n"""'
assert S.count(anchor) == 1, "CSS 结尾锚点未唯一命中"
S = S.replace(anchor, '.back .blk b { display:block; margin-bottom:1.5mm; }\n' + OVERRIDE + '"""', 1)

# ---- 2) 插入品牌资产函数与色板常量
anchor2 = 'def svg_inline(path: Path) -> str:'
assert S.count(anchor2) == 1
S = S.replace(anchor2,
              'PALETTE = ' + repr(PALETTE) + '\n' + BRAND_FN + anchor2, 1)

# ---- 3) 替换封面 / 封底
S, n1 = re.subn(r'def cover_page\(\):.*?(?=def toc_page\()', COVER_FN, S, flags=re.S)
S, n2 = re.subn(r'def back_page\(\):.*?(?=def main\(\):)', BACK_FN, S, flags=re.S)
assert n1 == 1 and n2 == 1, "封面/封底函数替换失败：%s %s" % (n1, n2)

P.write_text(S, encoding="utf-8")
print("已写入：CSS 主题色覆盖层、brand_svg()、PALETTE、新封面、新封底")
print("文件行数：", S.count("\n") + 1)
