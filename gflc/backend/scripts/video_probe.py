# -*- coding: utf-8 -*-
"""B站长视频真实链路压测：提交 → 轮询 → 落盘阶段时间线 + 结果快照。

用法：
    python scripts/video_probe.py "<url>" [templates] [poll_seconds]
输出：
    data/video_probe.jsonl   每次轮询一行（t / progress / status）
    data/video_probe.json    结束快照（阶段时间线、笔记结构、字数、帧数）
"""
import json
import sys
import time
import uuid
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8011"
URL = sys.argv[1]
TEMPLATES = (sys.argv[2] if len(sys.argv) > 2 else "summary,outline,qa").split(",")
POLL = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0
# 传固定账号可复用已有转写（秒传）；不传则临时注册新账号（完整跑 ASR）
FIXED_EMAIL = sys.argv[4] if len(sys.argv) > 4 else ""

OUT_JSONL = Path("data/video_probe.jsonl")
OUT_JSON = Path("data/video_probe.json")


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=180)
    email = FIXED_EMAIL or f"vp_{uuid.uuid4().hex[:8]}@gflc.com"
    if FIXED_EMAIL:
        r0 = c.post("/api/auth/login", json={"email": email, "password": "password123"})
        if r0.status_code != 200:
            c.post("/api/auth/register", json={"email": email, "password": "password123"})
    else:
        c.post("/api/auth/register", json={"email": email, "password": "password123"})
    print("account", email, flush=True)

    t0 = time.perf_counter()
    r = c.post("/api/videos/url", json={"url": URL, "templates": TEMPLATES})
    print("submit", r.status_code, r.text[:200], flush=True)
    task_id = r.json()["data"]["task_id"]

    OUT_JSONL.write_text("", encoding="utf-8")
    last = None
    with OUT_JSONL.open("a", encoding="utf-8") as f:
        while True:
            el = round(time.perf_counter() - t0, 1)
            try:
                t = c.get(f"/api/tasks/{task_id}").json()["data"]
            except Exception as e:  # noqa: BLE001
                print("poll error", e, flush=True)
                time.sleep(POLL)
                continue
            cur = (t["status"], t["progress"])
            if cur != last:
                rec = {"elapsed": el, "status": t["status"], "progress": t["progress"]}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                print(f"  t={el:7.1f}s  {t['progress']:3d}%  {t['status']}", flush=True)
                last = cur
            if t["status"] in ("ready", "failed", "interrupted", "canceled"):
                snap = {"elapsed_total": el, "status": t["status"], "task_id": task_id,
                        "error": t.get("error_message"), "result": t.get("result")}
                # 阶段时间线 + 笔记正文（供报告引用）
                try:
                    openapi = c.get(f"/api/tasks/{task_id}").json()["data"]
                    snap["checkpoint_timeline"] = (openapi.get("checkpoint") or {}).get("stage_timeline")
                except Exception:  # noqa: BLE001
                    pass
                doc_id = (t.get("result") or {}).get("document_id")
                if doc_id:
                    try:
                        notes = c.get(f"/api/videos/{doc_id}/notes").json().get("data") or {}
                        snap["notes"] = {
                            k: {"chars": len(str((v or {}).get("content") if isinstance(v, dict) else v)),
                                "keys": list(v)[:6] if isinstance(v, dict) else None}
                            for k, v in notes.items() if k in ("notes", "frames", "transcript")
                        }
                    except Exception as e:  # noqa: BLE001
                        snap["notes_error"] = str(e)[:120]
                OUT_JSON.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
                print("DONE", t["status"], "elapsed", el, flush=True)
                return 0
            time.sleep(POLL)


if __name__ == "__main__":
    sys.exit(main())
