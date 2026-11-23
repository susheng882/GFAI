# -*- coding: utf-8 -*-
"""W0 性能探针：把「解析 / 卡片 / 问答」的真实耗时打成一张表。

用法：
    python scripts/perf_probe.py [BASE]        # 默认 http://127.0.0.1:8011
输出：markdown 表格 + 机器可读 JSON（data/perf_probe.json）

只读测量：注册一个临时账号、上传仓库自带 data/sample.pdf，不碰已有数据。
"""
import json
import os
import sys
import time
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
ROWS: list[dict] = []


def rec(name: str, ms: float, extra: str = "") -> None:
    ROWS.append({"item": name, "ms": round(ms, 1), "note": extra})
    print(f"| {name} | {ms/1000:.2f}s | {extra} |")


def wait_task(c: httpx.Client, task_id: int, limit: float = 600.0) -> dict:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < limit:
        d = c.get(f"/api/tasks/{task_id}").json().get("data", {})
        if d.get("status") in ("ready", "failed", "interrupted", "canceled"):
            return d
        time.sleep(0.3)
    return {"status": "timeout"}


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=300)
    email = f"perf_{uuid.uuid4().hex[:10]}@gflc.com"
    c.post("/api/auth/register", json={"email": email, "password": "password123"})

    # 1) PDF 解析 + 卡片
    with open("data/sample.pdf", "rb") as f:
        doc = c.post("/api/documents/upload",
                     files={"file": ("sample.pdf", f, "application/pdf")}).json()["data"]["document"]
    t0 = time.perf_counter()
    tid = c.post(f"/api/documents/{doc['id']}/parse").json()["data"]["task_id"]
    tt = wait_task(c, tid)
    rec("PDF 解析（sample.pdf，含切块+向量入库）", (time.perf_counter() - t0) * 1000,
        f"status={tt.get('status')} chunks={(tt.get('result') or {}).get('chunks')}")

    t0 = time.perf_counter()
    tid = c.post(f"/api/documents/{doc['id']}/cards").json()["data"]["task_id"]
    tt = wait_task(c, tid)
    rec("卡片生成（LLM，按大纲分章）", (time.perf_counter() - t0) * 1000,
        f"status={tt.get('status')} cards={(tt.get('result') or {}).get('cards')}")

    # 2) 问答：非流式（冷 / 热各一次，看检索缓存效果）
    for idx, tag in enumerate(("首次（冷索引）", "第二次（热缓存）"), 1):
        t0 = time.perf_counter()
        r = c.post("/api/qa", json={"question": "间隔重复算法依据什么安排复习时间？",
                                    "mode": "knowledge", "document_id": doc["id"]})
        rec(f"问答非流式 {tag}", (time.perf_counter() - t0) * 1000,
            f"http={r.status_code} src={len((r.json().get('data') or {}).get('sources') or [])}")

    # 3) 流式：status 帧 / 首个正文 delta / 总时长（三个指标分开，避免"首字节"虚报）
    with c.stream("POST", "/api/qa/stream", json={"question": "这部分资料讲了哪些核心概念？",
                                                 "mode": "knowledge", "document_id": doc["id"]}) as s:
        t0 = time.perf_counter()
        t_status = t_delta = None
        for line in s.iter_lines():
            if not line:
                continue
            el = time.perf_counter() - t0
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = ev.get("event") or ev.get("type")
            if kind == "status" and t_status is None:
                t_status = el
            elif kind == "delta" and t_delta is None:
                t_delta = el
        total = time.perf_counter() - t0
    rec("问答流式 status 帧", (t_status or 0) * 1000, "仅表示已受理，不是可用内容")
    rec("问答流式 首个正文字节", (t_delta or 0) * 1000, "真正的「看到答案」时间")
    rec("问答流式 总时长", total * 1000, "含生成全文")

    out = {"base": BASE, "rows": ROWS}
    os.makedirs("data", exist_ok=True)
    with open("data/perf_probe.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("\nJSON → data/perf_probe.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
