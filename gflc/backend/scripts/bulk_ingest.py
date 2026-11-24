# -*- coding: utf-8 -*-
"""批量导入真实数据，同时采集解析速度 / 文件大小 / token / CPU / 内存。

三种模式：
  question —— 真题/模拟卷 PDF → 题库（走 /questions/import，后台视觉识别抽题）
  document —— 教材 PDF → 解析 → 可选生成背诵卡片
  note     —— Markdown → 笔记（直接落库，走 /notes）

用法：
  python scripts/bulk_ingest.py --mode question --list files.txt --out perf/q.json
  python scripts/bulk_ingest.py --mode document --dir "C:/.../强化知识点" --cards --out perf/tb.json
  python scripts/bulk_ingest.py --mode note --dir "C:/.../knowledge/专业" --out perf/nt.json

设计要点：
- 断点续跑：读已有 --out，按「文件绝对路径」跳过已 succeeded 的条目
- 每文件记录：字节数、上传秒、任务秒、速度、token 前后差、CPU/内存采样峰值、progress 序列
- 不并发：串行才能让单文件耗时/资源读数有意义
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
import psutil

BASE_DEFAULT = "http://127.0.0.1:8012"
UA = {"User-Agent": "gflc-bulk-ingest/1.0"}


def login(client: httpx.Client, email: str, password: str) -> None:
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        raise SystemExit(f"登录失败 {r.status_code}: {r.text[:200]}")


def monitor_tokens(client: httpx.Client) -> dict:
    """取当前累计用量（用于前后差值）。失败时返回空，不影响主流程。"""
    try:
        d = (client.get("/api/settings/monitor").json() or {}).get("data") or {}
        today = d.get("today") or {}
        return {"calls": int(today.get("calls") or 0),
                "tokens": int(today.get("tokens") or 0),
                "cost": float(today.get("cost") or 0)}
    except Exception:  # noqa: BLE001
        return {"calls": 0, "tokens": 0, "cost": 0}


def wait_task(client: httpx.Client, task_id: int, timeout: float = 2400.0) -> dict:
    """轮询任务直到终态；返回 {status, progress_seq, cpu_peak, mem_peak, seconds}。"""
    t0 = time.perf_counter()
    seq: list[int] = []
    cpu_peak = 0.0
    mem_peak = 0.0
    status = "timeout"
    detail: dict = {}
    while time.perf_counter() - t0 < timeout:
        try:
            r = client.get(f"/api/tasks/{task_id}")
            d = (r.json() or {}).get("data") or {}
        except Exception:  # noqa: BLE001
            time.sleep(2)
            continue
        p = int(d.get("progress") or 0)
        if not seq or seq[-1] != p:
            seq.append(p)
        # 资源采样：跳过首个读数（cpu_percent 首次恒为 0）
        c = psutil.cpu_percent(interval=None)
        cpu_peak = max(cpu_peak, c)
        mem_peak = max(mem_peak, psutil.virtual_memory().percent)
        st = str(d.get("status") or "")
        # 任务终态：ready（成功）/ failed / canceled（项目里成功状态叫 ready，不是 succeeded）
        if st in ("ready", "failed", "canceled"):
            status = st
            detail = d
            break
        time.sleep(2)
    return {"status": "succeeded" if status == "ready" else status,
            "progress_seq": seq, "cpu_peak": round(cpu_peak, 1),
            "mem_peak": round(mem_peak, 1), "seconds": round(time.perf_counter() - t0, 2),
            "error": (detail.get("error_message") or "")[:300] if status == "failed" else "",
            "result": detail.get("result") or {}}


def upload_and_parse_question(client: httpx.Client, path: Path) -> dict:
    """真题/模拟卷 → 题库：一次 multipart 上传即入队 question_import。"""
    size = path.stat().st_size
    tok0 = monitor_tokens(client)
    t_up = time.perf_counter()
    with open(path, "rb") as f:
        r = client.post("/api/questions/import",
                        files={"file": (path.name, f, "application/pdf")}, timeout=300)
    up_s = round(time.perf_counter() - t_up, 2)
    if r.status_code != 200:
        return {"file": str(path), "name": path.name, "size": size, "status": "upload_failed",
                "upload_s": up_s, "error": f"{r.status_code} {r.text[:200]}"}
    d = (r.json() or {}).get("data") or {}
    task = wait_task(client, int(d["task_id"]))
    tok1 = monitor_tokens(client)
    return {
        "file": str(path), "name": path.name, "size": size, "kind": "question",
        "status": "succeeded" if task["status"] == "succeeded" else task["status"],
        "upload_s": up_s, "parse_s": task["seconds"],
        "total_s": round(up_s + task["seconds"], 2),
        "speed_mb_s": round((size / 1048576) / max(task["seconds"], 0.1), 3),
        "progress_seq": task["progress_seq"],
        "cpu_peak": task["cpu_peak"], "mem_peak": task["mem_peak"],
        "tokens_delta": tok1["tokens"] - tok0["tokens"],
        "calls_delta": tok1["calls"] - tok0["calls"],
        "cost_delta": round(tok1["cost"] - tok0["cost"], 5),
        "result": task["result"], "error": task["error"],
    }


def upload_parse_document(client: httpx.Client, path: Path, cards: bool) -> dict:
    """教材 → 解析 → 可选生成卡片。"""
    size = path.stat().st_size
    tok0 = monitor_tokens(client)
    t_up = time.perf_counter()
    with open(path, "rb") as f:
        r = client.post("/api/documents/upload",
                        files={"file": (path.name, f, "application/pdf")}, timeout=600)
    up_s = round(time.perf_counter() - t_up, 2)
    if r.status_code != 200:
        return {"file": str(path), "name": path.name, "size": size, "status": "upload_failed",
                "upload_s": up_s, "error": f"{r.status_code} {r.text[:200]}"}
    doc = ((r.json() or {}).get("data") or {}).get("document") or {}
    doc_id = int(doc["id"])

    # 触发解析
    pr = client.post(f"/api/documents/{doc_id}/parse")
    task_id = int(((pr.json() or {}).get("data") or {}).get("task_id") or 0) if pr.status_code == 200 else 0
    task = wait_task(client, task_id) if task_id else {"status": "parse_trigger_failed",
                                                       "seconds": 0, "progress_seq": [],
                                                       "cpu_peak": 0, "mem_peak": 0, "error": "",
                                                       "result": {}}
    card_task: dict = {}
    if cards and task["status"] == "succeeded":
        cr = client.post(f"/api/documents/{doc_id}/cards")
        cid = int(((cr.json() or {}).get("data") or {}).get("task_id") or 0) if cr.status_code == 200 else 0
        if cid:
            card_task = wait_task(client, cid)

    tok1 = monitor_tokens(client)
    total = up_s + task["seconds"] + card_task.get("seconds", 0)
    return {
        "file": str(path), "name": path.name, "size": size, "kind": "document", "document_id": doc_id,
        "status": "succeeded" if task["status"] == "succeeded" else task["status"],
        "upload_s": up_s, "parse_s": task["seconds"], "cards_s": card_task.get("seconds", 0),
        "total_s": round(total, 2),
        "speed_mb_s": round((size / 1048576) / max(task["seconds"], 0.1), 3),
        "progress_seq": task["progress_seq"],
        "cpu_peak": max(task["cpu_peak"], card_task.get("cpu_peak", 0)),
        "mem_peak": max(task["mem_peak"], card_task.get("mem_peak", 0)),
        "tokens_delta": tok1["tokens"] - tok0["tokens"],
        "calls_delta": tok1["calls"] - tok0["calls"],
        "cost_delta": round(tok1["cost"] - tok0["cost"], 5),
        "result": task["result"], "cards_result": card_task.get("result") or {},
        "error": task["error"] or card_task.get("error", ""),
    }


def import_note(client: httpx.Client, path: Path) -> dict:
    """Markdown → 笔记。取正文首行为标题，整篇作为 content。"""
    t0 = time.perf_counter()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        return {"file": str(path), "name": path.name, "status": "read_failed", "error": str(e)[:200]}
    if not text.strip():
        return {"file": str(path), "name": path.name, "status": "skipped_empty", "size": 0}
    # 标题：去掉 markdown 标记的首个非空行
    title = path.stem
    for line in text.splitlines():
        s = line.strip().lstrip("#").strip()
        if s:
            title = s[:80]
            break
    r = client.post("/api/notes", json={"title": title, "content": text})
    if r.status_code != 200:
        return {"file": str(path), "name": path.name, "status": "failed",
                "size": len(text.encode("utf-8")), "error": f"{r.status_code} {r.text[:200]}"}
    nid = ((r.json() or {}).get("data") or {}).get("id")
    return {"file": str(path), "name": path.name, "kind": "note", "note_id": nid,
            "size": path.stat().st_size, "chars": len(text),
            "status": "succeeded", "total_s": round(time.perf_counter() - t0, 3)}


def collect_files(args) -> list[Path]:
    out: list[Path] = []
    if args.list:
        for line in Path(args.list).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                p = Path(line)
                if p.is_file():
                    out.append(p)
    if args.dir:
        root = Path(args.dir)
        pats = args.pattern.split(",")
        for pat in pats:
            out.extend(sorted(root.rglob(pat.strip())))
    # 去重保序
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in out:
        k = str(p.resolve())
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["question", "document", "note"], required=True)
    ap.add_argument("--list", help="文件清单（每行一个绝对路径）")
    ap.add_argument("--dir", help="目录（配合 --pattern 递归）")
    ap.add_argument("--pattern", default="*.pdf", help="逗号分隔，如 *.pdf,*.md")
    ap.add_argument("--cards", action="store_true", help="document 模式下同时生成卡片")
    ap.add_argument("--out", required=True, help="输出 JSON 路径")
    ap.add_argument("--base", default=BASE_DEFAULT)
    ap.add_argument("--email", default=os.getenv("GFLC_EMAIL", "cfg_probe@gflc.com"))
    ap.add_argument("--password", default=os.getenv("GFLC_PASSWORD", "password123"))
    ap.add_argument("--limit", type=int, default=0, help="只处理前 N 个（0=全部）")
    ap.add_argument("--retry-failed", action="store_true", help="重跑上次失败的条目")
    args = ap.parse_args()

    files = collect_files(args)
    if not files:
        print("[FAIL] 没有匹配到文件")
        return 1
    if args.limit:
        files = files[: args.limit]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    prev: dict[str, dict] = {}
    if out_path.exists():
        try:
            old = json.loads(out_path.read_text(encoding="utf-8"))
            for it in old.get("items") or []:
                prev[it.get("file", "")] = it
        except Exception:  # noqa: BLE001
            pass

    print(f"[{args.mode}] 待处理 {len(files)} 个文件，输出 {out_path}")
    items: list[dict] = list(prev.values())
    done_keys = set()
    for p in files:
        k = str(p.resolve())
        old = prev.get(k) or prev.get(str(p))
        if old and old.get("status") == "succeeded":
            done_keys.add(k)
            print(f"  跳过（已完成）{p.name}")
            continue
        if old and old.get("status") and not args.retry_failed:
            # 允许非成功项重试，避免一次失败就永久放弃
            pass

        size_mb = p.stat().st_size / 1048576
        print(f"  → {p.name}  ({size_mb:.1f}MB)", flush=True)
        with httpx.Client(base_url=args.base, timeout=httpx.Timeout(600.0), headers=UA) as client:
            login(client, args.email, args.password)
            t0 = time.perf_counter()
            if args.mode == "question":
                rec = upload_and_parse_question(client, p)
            elif args.mode == "document":
                rec = upload_parse_document(client, p, args.cards)
            else:
                rec = import_note(client, p)
            rec["file"] = k
            rec["wall_s"] = round(time.perf_counter() - t0, 2)
        rec.setdefault("name", p.name)
        rec.setdefault("size", p.stat().st_size)
        items = [x for x in items if x.get("file") not in (k, str(p))] + [rec]
        print(f"     {rec.get('status')}  {rec.get('total_s', rec.get('wall_s'))}s"
              f"  {rec.get('speed_mb_s', '')}MB/s  tokens={rec.get('tokens_delta', 0)}"
              f"  cpu={rec.get('cpu_peak', 0)}% mem={rec.get('mem_peak', 0)}%", flush=True)
        # 每个文件都落盘，中断可续
        out_path.write_text(json.dumps(
            {"mode": args.mode, "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
             "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")

    ok = sum(1 for x in items if x.get("status") == "succeeded")
    print(f"\n[{args.mode}] 完成：成功 {ok}/{len(items)}，结果已写入 {out_path}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
