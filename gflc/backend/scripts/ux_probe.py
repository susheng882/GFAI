# -*- coding: utf-8 -*-
"""UX 交互验收：覆盖本轮新增的背诵/笔记交互（命令面板、评分间隔、vault 四态等）。

只做「能打开 / 能点 / 不报错 / 无横向滚动 / 控制台无错」的体验级断言，
不替代 verify_all.py 的接口契约与 e2e_paths.py 的主路径。

用法：
    python scripts/ux_probe.py [BASE] [OUTDIR]
默认 http://127.0.0.1:8012 → ../docs/screenshots/ux_final
"""
import json
import sys
import time
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8012"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "../docs/screenshots/ux_final")
OUT.mkdir(parents=True, exist_ok=True)

results: list[dict] = []
errors: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append({"name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + (f" — {detail}" if detail else ""))


def no_overflow(pg, name: str) -> None:
    ov = pg.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
    check(f"{name} 无横向滚动", not ov)


def main() -> int:
    email = f"ux_{uuid.uuid4().hex[:10]}@gflc.com"
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        pg.goto(f"{BASE}/login", wait_until="networkidle")
        r = pg.request.post(f"{BASE}/api/auth/register",
                            data={"email": email, "password": "password123"})
        check("注册可完成", r.ok, r.text()[:100] if not r.ok else "")
        pg.goto(f"{BASE}/", wait_until="networkidle")
        time.sleep(1.0)

        # 1. 全局命令面板 Ctrl+K
        pg.goto(f"{BASE}/dash", wait_until="networkidle")
        pg.keyboard.press("Control+k")
        time.sleep(0.4)
        palette = pg.locator("[class*=command], [class*=palette], [class*=cmd]")
        check("Ctrl+K 命令面板可打开", palette.count() > 0, f"matched={palette.count()}")
        pg.screenshot(path=str(OUT / "cmd_palette.png"))
        pg.keyboard.press("Escape")
        time.sleep(0.3)
        check("Esc 可关闭命令面板", palette.count() == 0)

        # 2. 复习页：四档间隔 + 快捷键（空态也应正常渲染）
        pg.goto(f"{BASE}/review", wait_until="networkidle")
        time.sleep(0.7)
        no_overflow(pg, "review")
        pg.screenshot(path=str(OUT / "review.png"))

        # 3. 背诵页：队列合并 + 评分闭环入口
        pg.goto(f"{BASE}/study", wait_until="networkidle")
        time.sleep(0.7)
        no_overflow(pg, "study")
        body = pg.inner_text("body")
        check("背诵/刷题页正常渲染", len(body) > 50, f"body_chars={len(body)}")
        pg.screenshot(path=str(OUT / "study.png"))

        # 4. 卡片浏览器：网格/表格切换 + 筛选条
        pg.goto(f"{BASE}/deck", wait_until="networkidle")
        time.sleep(0.9)
        no_overflow(pg, "deck")
        # 新账号无卡片，默认走网格视图；断言「卡片浏览器容器或空态存在」而非必须是表格
        has_table = pg.locator("table, .ant-segmented, [class*=browser]").count() > 0
        check("卡片浏览器视图与切换器存在", has_table)
        pg.screenshot(path=str(OUT / "deck.png"))

        # 5. 笔记页：vault 状态条 + 成卡行 + emoji 清理
        pg.goto(f"{BASE}/notes", wait_until="networkidle")
        time.sleep(0.8)
        no_overflow(pg, "notes")
        nb = pg.inner_text("body")
        check("无 emoji 图标残留", not any(e in nb for e in ("📄", "📂", "📁")))
        pg.screenshot(path=str(OUT / "notes.png"))

        # 6. 设置页：vault 本地文件库 + 账号安全 tab
        pg.goto(f"{BASE}/settings", wait_until="networkidle")
        time.sleep(0.8)
        no_overflow(pg, "settings")
        sb = pg.inner_text("body")
        check("设置页含本地文件库入口", "本地文件库" in sb or "vault" in sb.lower() or "本地" in sb)
        check("设置页含账号与安全入口", "账号" in sb)
        pg.screenshot(path=str(OUT / "settings.png"))

        # 7. 430 移动视口关键页
        pg.set_viewport_size({"width": 430, "height": 900})
        for name, path in (("review", "/review"), ("notes", "/notes"), ("settings", "/settings")):
            pg.goto(f"{BASE}{path}", wait_until="networkidle")
            time.sleep(0.6)
            no_overflow(pg, f"{name}_430")
            pg.screenshot(path=str(OUT / f"{name}_430.png"))

        b.close()

    check("无控制台错误", len(errors) == 0, "; ".join(errors[:3]))
    passed = sum(1 for r in results if r["ok"])
    print(f"\nUX_PROBE {passed}/{len(results)}")
    print(json.dumps({"out": str(OUT), "passed": passed, "total": len(results),
                      "errors": errors[:10], "results": results},
                     ensure_ascii=False, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
