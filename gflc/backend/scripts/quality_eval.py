# -*- coding: utf-8 -*-
"""多维度质量评测：检索相关性 / 回答完整性 / 引用规范性 / 时延 / 成本。

用法：
    D:/anaconda3/python.exe scripts/quality_eval.py [--base-url http://127.0.0.1:8010]
                                                    [--seed-sample] [--keep-going]

脚本自己注册账号（POST /api/auth/register），按 8 道题（3 数学 / 2 英语 / 1 学习方法 /
2 诱饵）逐题打 /api/qa，再从 cost_ledger 读每题花费，输出表格 + 加权总分（满分 10，≥7.5 达标）。
不引入任何新依赖：标准库 sqlite3 + 项目已有的 httpx。
"""
import argparse
import os
import re
import sqlite3
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 维度权重（合计 10）
W_RELEVANCE, W_COMPLETE, W_CITE, W_LATENCY, W_COST = 3.0, 2.5, 2.0, 1.5, 1.0
PASS_LINE = 7.5

# 题目：kind = math / english / study / decoy
QUESTIONS = [
    {"q": "解一元二次方程 x^2 - 5x + 6 = 0，并写出求根过程。", "kind": "math"},
    {"q": "直角三角形两条直角边分别是 3 和 4，求斜边长，并说明用的是哪个定理。", "kind": "math"},
    {"q": "函数 f(x)=x^3-3x 的极大值点和极小值点分别在 x 等于多少？请给出求导过程。", "kind": "math"},
    {"q": "affect 和 effect 的用法有什么区别？请各举一个例句。", "kind": "english"},
    {"q": "英语中现在完成时和一般过去时的区别是什么？请举例说明。", "kind": "english"},
    {"q": "如何用间隔重复的方法安排一周的复习计划？请给出具体到天的安排。", "kind": "study"},
    {"q": "今天天气怎么样？适合出门跑步吗？", "kind": "decoy"},          # 库里没有、也不该编
    {"q": "推荐几首适合跑步时听的流行歌曲。", "kind": "decoy"},           # 娱乐类诱饵
]

# 无关实词黑名单：出现在答案里说明检索串味/答偏
_BLACKLIST = {
    "math": ["歌手", "专辑", "音乐", "歌词", "明星", "电影", "天气", "综艺"],
    "english": ["专辑", "歌手", "电影", "天气", "综艺"],
    "study": ["专辑", "歌手", "电影", "天气"],
    "decoy": [],
}
# 编造事实的迹象（诱饵题里出现具体天气/歌名即视为幻觉）
_WEATHER_FAKE = ["晴", "多云", "阴天", "℃", "摄氏度", "气温", "降雨", "风力"]
_REFUSAL_WORDS = ["未在资料中", "没有找到", "无法", "建议", "不清楚", "未提供", "不能提供",
                  "没有实时", "无法获取", "依据不足"]

_LIST_RE = re.compile(r"(?m)^\s*(?:[-*·]|\d+[.)、])\s+\S")
_HEAD_RE = re.compile(r"(?m)^\s*(?:#{2,4}\s+\S|\*\*[^*\n]{2,30}\*\*)")
_FORMULA_RE = re.compile(r"\$[^$\n]{2,}\$|\\frac|\\sqrt|[a-zA-Z]\s*=\s*[-+0-9a-zA-Z(]")
_CITE_RE = re.compile(r"\[\d+\]")


# ------------------------------------------------------------------ 账本
def _sqlite_path() -> str | None:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        env_file = ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
                    break
    if not url.startswith("sqlite"):
        return None
    raw = url.split("///", 1)[-1]
    p = Path(raw)
    if not p.is_absolute():
        p = (ROOT / raw).resolve()
    return str(p) if p.exists() else None


def _cost_between(path: str | None, user_id: int, t0: datetime, t1: datetime) -> float:
    if not path:
        return -1.0
    fmt = "%Y-%m-%d %H:%M:%S.%f"
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        try:
            row = con.execute(
                "select coalesce(sum(cost_cny),0) from cost_ledger "
                "where user_id=? and created_at >= ? and created_at <= ?",
                (user_id, t0.strftime(fmt), t1.strftime(fmt)),
            ).fetchone()
            return round(float(row[0] or 0.0), 6)
        finally:
            con.close()
    except sqlite3.Error:
        return -1.0


# ------------------------------------------------------------ 评分函数
def _score_relevance(kind: str, mode: str, answer: str) -> float:
    if kind == "decoy":
        if mode == "none":
            return 1.0
        if mode == "knowledge":
            return 0.0                                   # 编造引用作答，最差
        if mode == "web":
            return 0.3
        # mode == "model"：未拒答但标了"未经资料佐证"
        fake = sum(1 for w in _WEATHER_FAKE if w in answer) if "天气" in answer else 0
        return 0.4 if fake else 0.6
    if mode == "none":
        return 0.3                                       # 该答却拒答
    hits = sum(1 for w in _BLACKLIST.get(kind, []) if w in answer)
    return 1.0 if hits == 0 else (0.5 if hits == 1 else 0.0)


def _score_complete(mode: str, answer: str) -> float | None:
    if mode == "none":
        return None                                      # 拒答题不评价完整性
    n = len(answer)
    base = min(1.0, n / 150.0)
    bonus = 0.0
    if _LIST_RE.search(answer):
        bonus += 0.5
    if _HEAD_RE.search(answer):
        bonus += 0.5
    if _FORMULA_RE.search(answer):
        bonus += 0.5
    return round(min(1.0, (base + bonus) / 2.0), 3)      # 满分口径：150 字 + 两类结构


def _score_cite(mode: str, answer: str, sources: list) -> float | None:
    if mode == "none":
        return 1.0                                       # 诚实拒答，给满分
    if mode == "knowledge":
        return 1.0 if _CITE_RE.search(answer) else 0.0
    if mode == "model":
        return 1.0 if "模型知识" in answer else 0.0
    if mode == "web":
        ok = bool(sources) or "http" in answer or bool(re.search(r"(?m)^\s*\d+[.、]", answer))
        return 1.0 if ok else 0.0
    return None


def _score_latency(seconds: float) -> float:
    if seconds < 15:
        return 1.0
    if seconds <= 30:
        return 0.5
    return 0.0


def _score_cost(cost: float) -> float | None:
    if cost < 0:
        return None
    if cost <= 0.02:
        return 1.0
    if cost <= 0.05:
        return 0.6
    return 0.0


# ---------------------------------------------------------------- 主流程
def _avg(values: list[float]) -> float | None:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:8010")
    ap.add_argument("--seed-sample", action="store_true", help="先上传 data/sample.pdf，让知识库路径也能被评测")
    ap.add_argument("--timeout", type=float, default=180.0)
    args = ap.parse_args()

    c = httpx.Client(base_url=args.base_url.rstrip("/"), timeout=args.timeout)
    email = f"qe_{uuid.uuid4().hex[:8]}@t.com"
    r = c.post("/api/auth/register", json={"email": email, "password": "password123"})
    if r.status_code != 200:
        print(f"注册失败：{r.status_code} {r.text[:200]}")
        return 2
    me = c.get("/api/auth/me").json().get("data", {}).get("user", {})
    user_id = int(me.get("id") or 0)
    print(f"评测账号 {email}（user_id={user_id}）→ {args.base_url}\n")

    if args.seed_sample:
        pdf = ROOT / "data" / "sample.pdf"
        if pdf.exists():
            with open(pdf, "rb") as f:
                up = c.post("/api/documents/upload", files={"file": ("sample.pdf", f, "application/pdf")})
            doc_id = (up.json().get("data") or {}).get("document", {}).get("id")
            if doc_id:
                tid = c.post(f"/api/documents/{doc_id}/parse").json().get("data", {}).get("task_id")
                print(f"已上传 sample.pdf（id={doc_id}），解析任务 {tid}")

    db_path = _sqlite_path()
    rows = []
    for i, item in enumerate(QUESTIONS, 1):
        t0_wall, t0 = time.time(), datetime.now(timezone.utc).replace(tzinfo=None)
        body = None
        try:
            # 优先走流式（与真实前端一致，时延口径才对得上）
            full, mode_s, srcs = "", None, []
            with c.stream("POST", "/api/qa/stream", json={"question": item["q"]}) as rs:
                for line in rs.iter_lines():
                    if not line.strip():
                        continue
                    ev = json.loads(line)
                    ty = ev.get("type")
                    if ty == "sources":
                        mode_s, srcs = ev.get("mode"), ev.get("sources") or []
                    elif ty in ("delta", "notice"):
                        full += ev.get("text") or ""
                    elif ty == "done" and ev.get("full"):
                        full = ev["full"]
            elapsed = time.time() - t0_wall
            body = {"ok": True, "data": {"mode": mode_s, "answer": full, "sources": srcs}}
        except Exception as e:                            # 网络/超时
            elapsed = time.time() - t0_wall
            body = {"ok": False, "error": {"code": "NET", "message": str(e)[:80]}}
        t1 = datetime.now(timezone.utc).replace(tzinfo=None)

        data = body.get("data") or {}
        mode = data.get("mode") or "-"
        answer = data.get("answer") or ""
        sources = data.get("sources") or []
        err = (body.get("error") or {}).get("code", "") if not body.get("ok") else ""
        cost = _cost_between(db_path, user_id, t0, t1) if user_id else -1.0

        rel = _score_relevance(item["kind"], mode, answer)
        comp = _score_complete(mode, answer)
        cite = _score_cite(mode, answer, sources)
        lat = _score_latency(elapsed)
        cst = _score_cost(cost)
        parts = [(rel, W_RELEVANCE), (comp, W_COMPLETE), (cite, W_CITE), (lat, W_LATENCY), (cst, W_COST)]
        num = sum(v * w for v, w in parts if v is not None)
        den = sum(w for v, w in parts if v is not None)
        score = round(num / den * 10 if den else 0.0, 2)   # 单题 0–10 制
        rows.append({"i": i, "kind": item["kind"], "q": item["q"], "mode": mode, "err": err,
                     "chars": len(answer), "cost": cost, "t": elapsed, "score": score,
                     "rel": rel, "comp": comp, "cite": cite, "lat": lat, "cst": cst})
        print(f"[{i}/{len(QUESTIONS)}] {item['kind']:<7} mode={mode:<9} {len(answer):>4}字 "
              f"{elapsed:>5.1f}s 花费={cost if cost >= 0 else '?'} 得分={score}")

    # ---- 维度均分 → 加权总分 ----
    dims = {
        "检索相关性": (_avg([r["rel"] for r in rows]), W_RELEVANCE),
        "回答完整性": (_avg([r["comp"] for r in rows]), W_COMPLETE),
        "引用规范性": (_avg([r["cite"] for r in rows]), W_CITE),
        "时延": (_avg([r["lat"] for r in rows]), W_LATENCY),
        "成本": (_avg([r["cst"] for r in rows]), W_COST),
    }
    active = {k: v for k, v in dims.items() if v[0] is not None}
    total_w = sum(w for _, w in active.values()) or 1.0
    total = sum(s * w for s, w in active.values()) / total_w * 10

    print("\n" + "-" * 68)
    print(f"{'题号':<4}{'类型':<9}{'mode':<10}{'字数':>6}{'耗时':>9}{'花费(元)':>10}{'得分':>7}")
    for r in rows:
        print(f"{r['i']:<4}{r['kind']:<9}{r['mode']:<10}{r['chars']:>6}{r['t']:>8.1f}s"
              f"{r['cost'] if r['cost'] >= 0 else 0:>10.4f}{r['score']:>7}")
    print("-" * 68)
    for k, (s, w) in dims.items():
        print(f"{k:<10} 均分 {('%.2f' % s) if s is not None else ' n/a '} × 权重 {w:<4} = "
              f"{('%.2f' % (s * w)) if s is not None else '  -  '}")
    print("-" * 68)
    print(f"加权总分：{total:.2f} / 10    达标线 {PASS_LINE}    "
          f"{'达标 ✔' if total >= PASS_LINE else '未达标 ✘'}")
    total_cost = sum(r["cost"] for r in rows if r["cost"] >= 0)
    print(f"本次总花费：{total_cost:.4f} 元，平均时延：{sum(r['t'] for r in rows) / len(rows):.1f}s")
    worst = sorted(rows, key=lambda r: r["score"])[:2]
    print("最差两题：" + "；".join(f"#{w['i']}({w['kind']}, {w['score']}分) {w['q'][:18]}" for w in worst))
    return 0 if total >= PASS_LINE else 1


if __name__ == "__main__":
    sys.exit(main())
