# -*- coding: utf-8 -*-
"""UI 实拍：登录 → 逐页截图（桌面/移动/暗色），同时收集控制台错误与横向滚动。

用法：
    python scripts/ui_shots.py [BASE] [OUTDIR]
默认 http://127.0.0.1:8011 → gflc/docs/screenshots/react_baseline/
"""
import json
import sys
import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "../docs/screenshots/react_baseline")
OUT.mkdir(parents=True, exist_ok=True)

PAGES = [("dashboard", "/dash"), ("docs", "/docs"), ("qa", "/qa"), ("notes", "/notes"),
         ("decks", "/deck"), ("study", "/study"), ("review", "/review"),
         ("plans", "/plans"), ("tasks", "/tasks"), ("video", "/video")]

errors: list[str] = []


def main() -> int:
    email = f"ui_{uuid.uuid4().hex[:10]}@gflc.com"
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        # 注册（前端注册页）
        pg.goto(f"{BASE}/login", wait_until="networkidle")
        pg.screenshot(path=str(OUT / "login.png"))
        r = pg.request.post(f"{BASE}/api/auth/register",
                            data={"email": email, "password": "password123"})
        assert r.ok, r.text()
        pg.goto(f"{BASE}/", wait_until="networkidle")
        time.sleep(1.2)

        report = []
        for name, path in PAGES:
            pg.goto(f"{BASE}{path}", wait_until="networkidle")
            time.sleep(0.9)
            overflow = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
            pg.screenshot(path=str(OUT / f"{name}_1440.png"), full_page=False)
            report.append({"page": name, "path": path, "h_overflow_1440": overflow})

        # 430 移动端
        pg.set_viewport_size({"width": 430, "height": 900})
        for name, path in PAGES[:4]:
            pg.goto(f"{BASE}{path}", wait_until="networkidle")
            time.sleep(0.7)
            ov = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
            pg.screenshot(path=str(OUT / f"{name}_430.png"))
            report.append({"page": name, "path": path, "h_overflow_430": ov})

        # 暗色
        pg.set_viewport_size({"width": 1440, "height": 900})
        ctx2 = b.new_context(viewport={"width": 1440, "height": 900},
                             color_scheme="dark", locale="zh-CN")
        pg2 = ctx2.new_page()
        pg2.goto(f"{BASE}/login", wait_until="networkidle")
        pg2.screenshot(path=str(OUT / "login_dark.png"))
        b.close()

    print(json.dumps({"out": str(OUT), "errors": errors[:20], "pages": report},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
