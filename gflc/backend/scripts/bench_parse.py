# -*- coding: utf-8 -*-
"""真实材料解析压测：上传 → 解析（页/块）→ 生成背诵卡片，全程计时。

用法：python scripts/bench_parse.py "<pdf 路径>" [BASE]
"""
import os
import sys
import time
import uuid

import httpx

BASE = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8011"
PATH = sys.argv[1]
rows = []


def rec(name, sec, extra=""):
    rows.append((name, sec, extra))
    print(f"| {name} | {sec:.2f}s | {extra} |", flush=True)


def wait(c, tid, limit=600):
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < limit:
        d = c.get(f"/api/tasks/{tid}").json().get("data", {})
        if d.get("status") in ("ready", "failed", "interrupted"):
            return d
        time.sleep(0.3)
    return {"status": "timeout"}


def main():
    size_mb = os.path.getsize(PATH) / 1048576
    print(f"样本：{os.path.basename(PATH)}  {size_mb:.1f} MB\n")
    print("| 阶段 | 耗时 | 结果 |\n|---|---|---|")
    c = httpx.Client(base_url=BASE, timeout=900)
    c.post("/api/auth/register", json={"email": f"bench_{uuid.uuid4().hex[:8]}@gflc.com",
                                       "password": "password123"})

    t0 = time.perf_counter()
    with open(PATH, "rb") as f:
        r = c.post("/api/documents/upload", files={"file": (os.path.basename(PATH), f, "application/pdf")})
    doc = r.json()["data"]["document"]
    rec("上传", time.perf_counter() - t0, f"id={doc['id']}")

    t0 = time.perf_counter()
    tid = c.post(f"/api/documents/{doc['id']}/parse").json()["data"]["task_id"]
    t = wait(c, tid)
    el = time.perf_counter() - t0
    chunks = (t.get("result") or {}).get("chunks")
    rec("解析（含去噪/切块/入库）", el, f"status={t.get('status')} chunks={chunks}")
    parse_el, parse_chunks = el, chunks or 0

    t0 = time.perf_counter()
    tid = c.post(f"/api/documents/{doc['id']}/cards").json()["data"]["task_id"]
    t = wait(c, tid)
    cards = (t.get("result") or {}).get("cards")
    rec("生成背诵卡片（LLM）", time.perf_counter() - t0, f"status={t.get('status')} cards={cards}")

    decks = c.get("/api/decks").json().get("data", [])
    rec("卡包分组", 0.0, f"decks={len(decks)}")

    total = parse_el + (time.perf_counter() - t0)
    print(f"\n**解析速度**：{size_mb:.1f}MB → {parse_el:.2f}s（{size_mb / max(parse_el, 0.01):.1f} MB/s，"
          f"{parse_chunks} 块）")
    print(f"**默认卡片数**：{cards}（如需更多卡片可调 `cards` 接口的批量参数）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
