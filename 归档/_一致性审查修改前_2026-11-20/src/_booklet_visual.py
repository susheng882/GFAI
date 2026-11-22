# -*- coding: utf-8 -*-
"""图文并茂版图表册：在已校验的原 54 页骨架上，插入实拍照片图文插页。

- 复用 _booklet.py 的全部数据（F / CHAPTERS / CH_META / KPI_NOTE）与原页面函数。
- 原 54 页逐页原样保留，不外泄、不改动任何 SVG 信息图。
- 新增 12 张图文插页：主视觉 1 + 章节 10 + 收尾 1，照片铺满上半页、下半页白卡承载文案。
- 照片为 Unsplash 免费授权实拍，base64 内联，输出到「统一版式_图文版/」独立目录。
"""
import base64
import html
from pathlib import Path
from playwright.sync_api import sync_playwright
import _booklet as base
import _gf_brand as B

OUT = Path(r"F:\GrowthForward_AI学习伴侣\毕设材料\学术图表\统一版式_图文版")
OUT.mkdir(parents=True, exist_ok=True)
PHOTOS = Path(r"F:\GrowthForward_AI学习伴侣\brand_assets\photos")
W, H = 1588, 2246

# 照片 → 页面主题映射（章节号 -> 文件名）；00 为卷首品牌篇
PHOTO_MAP = {
    "hero": "cover",      # 主视觉：书桌 + 咖啡 + 花
    "00": "brand",        # 品牌篇：书本 + 苹果
    "01": "summary",      # 执行摘要：干净工位 + 代码
    "02": "market",       # 市场：平板数据看板
    "03": "product",      # 产品：多人协作
    "04": "arch",         # 架构：手指操作笔记本
    "05": "ai",           # AI 治理：深色数据大屏
    "06": "eng",          # 工程：代码屏 + 绿植
    "07": "fin",          # 财务：团队协作讨论
    "08": "team",         # 团队：机房学习
    "09": "plan",         # 进度：手写笔记
    "end": "back",        # 收尾：极简玻璃静物
}

_b64_cache = {}
def photo_uri(key):
    name = PHOTO_MAP[key]
    if name not in _b64_cache:
        data = (PHOTOS / f"{name}.jpg").read_bytes()
        _b64_cache[name] = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
    return _b64_cache[name]

# 图文插页文案：每章一句「照片旁白」，与章节论点呼应，措辞克制、苹果式短句
QUOTE = {
    "hero": "把「看过」变成「学会」。",
    "00": "安静、可信赖，不催不吵的学习伙伴。",
    "01": "一页看清：为什么做、做什么、花多少、多久交付。",
    "02": "上半场已被验证，下半场仍然空白。",
    "03": "38 项功能，不为堆砌，只为一次完整的学习闭环。",
    "04": "把最容易出事故的链路，拆到可实现的每一步。",
    "05": "选得对、用得省、管得住，¥82 才成立。",
    "06": "能长期跑起来的系统，才算真正做完。",
    "07": "支出用实价说话，收入用假设标注。",
    "08": "不虚构团队，把每个能力主张绑定到交付物。",
    "09": "何时交付、出问题怎么办，都要有明确答案。",
    "end": "Learn. Grow. Keep Moving Forward.",
}

EXTRA_CSS = r"""
/* ===== 图文插页：照片主导 + 白卡文案，苹果极简 ===== */
.vpage { position:relative; padding:0; background:#FFFFFF; color:#1D1D1F; }
.vphoto { position:absolute; left:0; right:0; top:0; height:170mm; overflow:hidden;
  background-position:center center; background-size:cover; }
.vfade { position:absolute; left:0; right:0; top:118mm; height:52mm;
  background:linear-gradient(to bottom, rgba(255,255,255,0) 0%, rgba(255,255,255,.55) 42%, #FFFFFF 100%); }
.vtop { position:absolute; left:12mm; right:12mm; top:8mm; display:flex;
  align-items:center; justify-content:space-between; z-index:2; }
.vtop .l, .vtop .r { display:inline-flex; align-items:center; gap:2mm;
  background:rgba(255,255,255,.86); border:.5pt solid rgba(255,255,255,.9);
  border-radius:999px; padding:1.6mm 3.4mm; font-size:7.8pt; letter-spacing:1.3pt;
  color:#1D1D1F; -webkit-backdrop-filter:blur(6px); backdrop-filter:blur(6px); }
.vtop .l svg { width:4.4mm; height:4.4mm; display:block; }
.vtop .r { color:#6E6E73; }
.vcap { position:absolute; left:12mm; top:118mm; z-index:2; }
.vcap .vno { font-size:46pt; font-weight:600; line-height:1; letter-spacing:-3pt;
  color:#FFFFFF; text-shadow:0 2px 18px rgba(0,0,0,.28); }
.vcap .vlabel { margin-top:1.5mm; display:inline-block; background:#0071E3; color:#FFFFFF;
  font-size:8pt; letter-spacing:1.6pt; font-weight:600; border-radius:999px; padding:1.3mm 3.2mm; }
.vbody { position:absolute; left:12mm; right:12mm; top:162mm; bottom:16mm;
  display:flex; flex-direction:column; }
.vbody h1 { margin:0; font-size:27pt; font-weight:600; letter-spacing:-.6pt; line-height:1.2; color:#1D1D1F; }
.vbody .ven { margin-top:1.8mm; font-size:8.4pt; letter-spacing:2.2pt; color:#86868B; font-weight:600; }
.vbody .vquote { margin-top:5mm; font-size:13.4pt; line-height:1.6; color:#1D1D1F; font-weight:400;
  padding-left:4mm; border-left:1.4mm solid #0071E3; }
.vbody .vkicker { margin-top:5mm; font-size:8pt; letter-spacing:1.8pt; color:#86868B; font-weight:600; }
.vkpis { display:grid; grid-template-columns:repeat(4,1fr); gap:2.4mm; margin-top:2.4mm; }
.vkpis .k { background:#F5F7FA; border:.5pt solid #E5E5EA; border-radius:3mm;
  padding:3mm 3.2mm; }
.vkpis .k .v { font-size:15pt; font-weight:600; color:#0071E3; line-height:1.15; letter-spacing:-.4pt; }
.vkpis .k .l { font-size:7.8pt; color:#6E6E73; margin-top:1.4mm; }
.vbody .vpts { margin-top:auto; padding-top:4mm; border-top:.6pt solid #E5E5EA; }
.vbody .vpts div { font-size:9.4pt; line-height:1.7; color:#3A3A3C; margin-bottom:1.6mm; }
.vbody .vpts div b { color:#0071E3; font-weight:600; margin-right:1.6mm; }
.vfoot { position:absolute; left:12mm; right:12mm; bottom:6mm; display:flex;
  align-items:center; justify-content:space-between; font-size:7.4pt; color:#86868B; }
.vfoot .slogan { letter-spacing:1.4pt; }
.vfoot .slogan b { color:#0071E3; }
.vfoot .src { color:#A1A1A6; }
.vpage .vwm { position:absolute; right:-14mm; bottom:24mm; width:74mm; height:74mm;
  opacity:.04; pointer-events:none; }
.vpage .vwm svg { width:100%; height:100%; display:block; }
"""

def visual_page(key, cn, en, label, kpis, pts, quote=None):
    """生成一张图文插页。key 对应照片；kpis 为 (值, 标签) 四元组；pts 为 2-3 条要点。"""
    kp = "".join(f'<div class="k"><div class="v">{html.escape(v)}</div>'
                 f'<div class="l">{html.escape(l)}</div></div>' for v, l in kpis[:4])
    pl = "".join(f'<div><b>{i:02d}</b>{html.escape(p)}</div>' for i, p in enumerate(pts, 1))
    q = quote if quote is not None else QUOTE.get(key, "")
    return f'''<div class="page vpage">
      <div class="vphoto" style="background-image:url('{photo_uri(key)}')"></div>
      <div class="vtop"><span class="l">{B.head_mark()}GROWTHFORWARD · 图文插页</span>
        <span class="r">GFLC · 2026</span></div>
      <div class="vcap"><div class="vno">{html.escape(label)}</div>
        <div class="vlabel">{html.escape(cn)}</div></div>
      <div class="vfade"></div>
      <div class="vbody">
        <h1>{html.escape(cn)}</h1>
        <div class="ven">{html.escape(en)}</div>
        <div class="vquote">{html.escape(q)}</div>
        <div class="vkicker">本 章 关 键 数 据</div>
        <div class="vkpis">{kp}</div>
        <div class="vpts">{pl}</div>
      </div>
      <div class="vwm">{B.mark()}</div>
      <div class="vfoot"><span class="slogan"><b>Learn. Grow.</b> Keep Moving Forward.</span>
        <span class="src">摄影：Unsplash · 免费授权 · 图文插页不参与图号编号</span></div>
    </div>'''

def main():
    F = base.F
    idx = {d['no']: i for i, d in enumerate(F, 1)}
    entries = [(idx[d['no']], d) for d in F]
    mid = (len(F) + 1) // 2

    pages, names, need_shot = [], [], []

    def add(page, name, shot=True):
        pages.append(page); names.append(name); need_shot.append(shot)

    # 封面 + 主视觉图文页 + 双目录（封面与目录复用原版 PNG）
    add(base.cover_page(), "00_封面", shot=False)
    add(visual_page("hero", "GrowthForward · 主视觉", "LEARN · GROW · KEEP MOVING FORWARD", "GF",
                    [("40 图", "学术插图"), ("54 页", "原册页"), ("12 张", "图文插页"), ("10 章", "BP 逻辑")],
                    ["前半程把「看过」变成「学会」，后半程按节奏持续向前。",
                     "原 54 页学术图表册完整保留，本版额外插入实拍图文页。"],
                    quote="把「看过」变成「学会」。"), "01_图文_主视觉")
    add(base.toc_page(1, entries[:mid], 2), "02_目录1", shot=False)
    add(base.toc_page(2, entries[mid:], 2), "03_目录2", shot=False)

    # 每章：原扉页(复用) -> 图文插页(新渲染) -> 该章图页(复用)
    seq = 4
    for ci, c in enumerate(base.CHAPTERS):
        add(base.chapter_page(c, ci), f"{seq:02d}_扉页{c['no']}", shot=False); seq += 1
        meta = base.CH_META[c["no"]]
        add(visual_page(c["no"], c["cn"], c["en"], c["no"],
                        meta["kpi"], c["pts"][:3]), f"{seq:02d}_图文_{c['no']}"); seq += 1
        for d in F:
            if d['chap'] == c['key']:
                add(base.figure_page(idx[d['no']], d), f"{seq:02d}_{d['no'].replace(' ', '')}",
                    shot=False); seq += 1

    # 收尾图文页(新渲染) + 封底(复用)
    add(visual_page("end", "成长向前", "THE JOURNEY CONTINUES", "END",
                    [("38 项", "功能总账"), ("16 周", "交付排期"), ("¥82", "月支出"), ("R1–R10", "风险登记")],
                    ["从品牌到市场、从功能到治理、从财务到排期，十章构成一条可回溯的证据链。",
                     "每一页都可沿「出处」回到产品报告与技术方案正文。"],
                    quote="Learn. Grow. Keep Moving Forward."), f"{seq:02d}_图文_收尾"); seq += 1
    add(base.back_page(), f"{seq:02d}_封底", shot=False)

    css = base.CSS + EXTRA_CSS
    doc = ('<!DOCTYPE html><html><head><meta charset="utf-8"><style>' + css +
           '</style></head><body>' + ''.join(pages) + '</body></html>')
    hp = OUT / "_booklet_visual.html"
    hp.write_text(doc, encoding="utf-8")

    from io import BytesIO
    from PIL import Image
    import shutil
    ORIG = base.OUT  # 原版 54 页目录，复用其已校验 PNG

    # 复用页映射：图文版名 -> 原版名（按出现顺序一一对应）
    orig_names = ['00_封面', '01_目录1', '02_目录2']
    for c in base.CHAPTERS:
        orig_names.append(None)  # 占位：章扉页（稍后按图页名反推）
        for d in F:
            if d['chap'] == c['key']:
                orig_names.append(None)
    orig_names.append(None)
    # 用原目录实际文件列表重建映射：原版顺序 = 封面,目录1,目录2,(扉页,图页)*10,封底
    orig_files = sorted(p.name for p in ORIG.glob('*.png'))
    assert len(orig_files) == 54, f'原版 PNG 应为 54 张，实际 {len(orig_files)}'
    oi = 0
    reuse_map = {}
    for i, shot in enumerate(need_shot):
        if not shot:
            reuse_map[names[i]] = orig_files[oi]
            oi += 1
    print('reuse pages:', len(reuse_map), '| new shots:', sum(need_shot))

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=2, viewport={'width': 794, 'height': 1123})
        page.goto(hp.as_uri())
        page.wait_for_timeout(1500)
        n = page.locator('.page').count()
        print('pages in DOM:', n, '| names:', len(names))
        pdf = OUT / 'GrowthForward_学术图表册_图文版.pdf'
        page.pdf(path=str(pdf), prefer_css_page_size=True, print_background=True)
        # 只截图 12 张新增图文页，避免 66 页逐页截图耗时
        for i, nm in enumerate(names):
            if not need_shot[i]:
                shutil.copy2(ORIG / reuse_map[nm], OUT / f'{nm}.png')
                continue
            raw = page.locator('.page').nth(i).screenshot()
            im = Image.open(BytesIO(raw)).convert('RGB')
            if im.size != (W, H):
                canvas = Image.new('RGB', (W, H), 'white')
                canvas.paste(im.crop((0, 0, min(im.width, W), min(im.height, H))))
                im = canvas
            im.save(OUT / f'{nm}.png')
            print('  shot', i + 1, nm)
        browser.close()
    print('PDF:', pdf)
    print('PNG pages:', len(names), '| fixed canvas:', f'{W}x{H}')

if __name__ == '__main__':
    main()
