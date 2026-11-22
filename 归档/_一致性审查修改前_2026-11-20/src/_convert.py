# -*- coding: utf-8 -*-
"""SVG -> PNG：全部图统一 680×960（A4 比例）画布，导出严格 1588×2246（A4 幅面），
与小册子内页尺寸完全一致，页边距由 _figlib / _normalize 统一模板控制。"""
import sys
from pathlib import Path
from io import BytesIO

from PIL import Image

SRC = Path(r"F:\GrowthForward_AI学习伴侣\毕设材料\学术图表\src")
DST = Path(r"F:\GrowthForward_AI学习伴侣\毕设材料\学术图表")
W, H, SCALE = 680, 960, 2
RW, RH = W * SCALE, H * SCALE          # 渲染中间画布 1360×1920
PW, PH = 1588, 2246                    # 统一交付尺寸（A4，与小册子内页一致）

HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  html,body{{margin:0;padding:0;background:#fff}}
  #canvas{{width:{w}px;height:{h}px;overflow:hidden}}
  #canvas svg{{display:block;width:{w}px;height:{h}px}}
</style></head><body><div id="canvas">{svg}</div></body></html>"""


def main():
    from playwright.sync_api import sync_playwright
    # 零删除策略：同名 PNG 直接覆盖写，不做任何 unlink / 批量清理，
    # 避免中断时把已有交付物清空；图号重编由 _renumber.py 以 rename 完成。
    svgs = sorted(SRC.glob("*.svg"))
    if not svgs:
        print("no svg found"); sys.exit(1)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(device_scale_factor=SCALE, viewport={"width": W + 20, "height": H + 20})
        ok, fail = [], []
        for f in svgs:
            out = DST / (f.stem + ".png")
            try:
                # 临时 HTML 改为内存注入，不在磁盘上产生中间文件，也就无需删除
                page.set_content(HTML.format(svg=f.read_text(encoding="utf-8"), w=W, h=H))
                page.wait_for_timeout(240)
                raw = page.locator("#canvas").screenshot()
                im = Image.open(BytesIO(raw)).convert("RGB")
                if im.size != (RW, RH):                       # 固定中间画布消除亚像素差
                    canvas = Image.new("RGB", (RW, RH), "white")
                    canvas.paste(im.crop((0, 0, min(im.width, RW), min(im.height, RH))))
                    im = canvas
                im = im.resize((PW, PH), Image.LANCZOS)       # 统一 A4 交付尺寸
                im.save(out)
                ok.append(out.name)
            except Exception as e:
                fail.append((f.name, str(e)[:200]))
        browser.close()
    print("OK:", len(ok), "| unified size", f"{PW}x{PH}")
    for n in ok: print("  ", n)
    if fail:
        print("FAIL:", len(fail))
        for n, e in fail: print("  ", n, "->", e)


if __name__ == "__main__":
    main()
