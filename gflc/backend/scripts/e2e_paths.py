# -*- coding: utf-8 -*-
"""主路径端到端验收：上传资料 → 生成笔记/卡片 → 刷题 → 复习（含延后 / 题型筛选 / 批量操作）。

用法：python scripts/e2e_paths.py [BASE]
输出：每步耗时 + 通过/失败；退出码 0=全通。

路径 1–4 为原有主干；路径 6–8 覆盖本轮新增能力：
- 6 延后复习（POST /review/{id}/defer）；
- 7 按题型组卷（POST /quiz/generate 的 qtype，无匹配题型记 SKIP 不算失败）；
- 8 批量重置 / 批量删除（越权与不存在的 id 走 failed，不返回 500）。
"""
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
rows: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    rows.append((name, ok, detail))
    print(f"{'✅' if ok else '❌'} {name}  {detail}")


def skip(name: str, detail: str = "") -> None:
    """SKIP 记通过：用例前提不满足（如题库里没有该题型），不算回归失败。"""
    rows.append((name, True, f"SKIP {detail}".strip()))
    print(f"⏭️ {name}  SKIP {detail}")


def _dt(value: str | None) -> datetime | None:
    """解析接口返回的 ISO 时间；无时区按 UTC 补齐，便于与 now 比较。"""
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo is not None else d.replace(tzinfo=timezone.utc)



def wait(c: httpx.Client, tid: int, limit: float = 300) -> dict:
    t0 = time.perf_counter()
    while time.perf_counter() - t0 < limit:
        d = c.get(f"/api/tasks/{tid}").json().get("data", {})
        if d.get("status") in ("ready", "failed", "interrupted"):
            return d
        time.sleep(0.4)
    return {"status": "timeout"}


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=300)
    c.post("/api/auth/register", json={"email": f"e2e_{uuid.uuid4().hex[:8]}@gflc.com",
                                       "password": "password123"})

    # 路径 1：上传 PDF → 解析
    t0 = time.perf_counter()
    with open("data/sample.pdf", "rb") as f:
        doc = c.post("/api/documents/upload",
                     files={"file": ("sample.pdf", f, "application/pdf")}).json()["data"]["document"]
    tid = c.post(f"/api/documents/{doc['id']}/parse").json()["data"]["task_id"]
    t = wait(c, tid)
    step("路径1 上传资料 → 解析完成", t.get("status") == "ready",
         f"{(time.perf_counter() - t0):.1f}s chunks={(t.get('result') or {}).get('chunks')}")

    # 路径 2：生成卡片/卡包 → 生成一篇笔记
    t0 = time.perf_counter()
    tid = c.post(f"/api/documents/{doc['id']}/cards").json()["data"]["task_id"]
    t = wait(c, tid)
    decks = c.get("/api/decks").json().get("data", [])
    step("路径2-1 生成卡片与卡包", t.get("status") == "ready" and len(decks) > 0,
         f"{(time.perf_counter() - t0):.1f}s decks={len(decks)} cards={(t.get('result') or {}).get('cards')}")

    note = c.post("/api/notes", json={"title": "E2E 极限笔记",
                                      "content": "# 极限\n- 夹逼定理\n- 等价无穷小 [[E2E 导数笔记]]",
                                      "source": "manual"}).json().get("data") or {}
    step("路径2-2 新建笔记 + 双链", bool(note.get("id")), f"id={note.get('id')}")

    # 路径 3：刷题（生成 → 提交 → 错题）
    t0 = time.perf_counter()
    # 刷题依赖题库：先导入一份真实题库
    with open("data/question_bank.xlsx", "rb") as f:
        imp = c.post("/api/questions/import",
                     files={"file": ("q.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    itid = (imp.json().get("data") or {}).get("task_id")
    if itid:
        wait(c, itid, limit=180)
    qs = c.post("/api/quiz/generate", json={"count": 3, "mode": "recommend"}).json().get("data") or []
    ok3 = bool(qs)
    if qs:
        sub = c.post("/api/quiz/submit",
                     json={"question_id": qs[0]["id"], "user_answer": "A"}).json().get("data", {})
        ok3 = "correct" in sub
        wrong = c.get("/api/quiz/wrong").json().get("data", [])
        ok3 = ok3 and isinstance(wrong, list)
    step("路径3 刷题：生成 → 提交", ok3, f"{(time.perf_counter() - t0):.1f}s 题数={len(qs)}")

    # 路径 4：复习（到期 → 评分）
    t0 = time.perf_counter()
    due = (c.get("/api/review/due?limit=5").json().get("data") or {}).get("cards") or []
    ok4 = bool(due) and c.post(f"/api/review/{due[0]['id']}",
                               json={"rating": 3}).status_code == 200
    step("路径4 复习：取到期卡 → 评分", ok4,
         f"{(time.perf_counter() - t0):.1f}s 到期={len(due)}")

    # 路径 6：延后复习 —— 只推 due_at，不改 mastery / reps
    # 优先取一张已到期的卡，才能验证「前移」不被原有远期排期干扰
    t0 = time.perf_counter()
    due6 = (c.get("/api/review/due?limit=5").json().get("data") or {}).get("cards") or []
    card = due6[0] if due6 else None
    if card is None:
        now6 = datetime.now(timezone.utc)
        cards = c.get("/api/cards?limit=50").json().get("data") or []
        card = next((k for k in cards
                     if _dt(k.get("due_at")) is None or _dt(k.get("due_at")) <= now6), None)
    ok6, detail6 = False, "无可用卡片"
    if card:
        before6 = _dt(card.get("due_at"))
        r6 = c.post(f"/api/review/{card['id']}/defer", json={"days": 2})
        body6 = (r6.json().get("data") or {}) if r6.status_code == 200 else {}
        after6 = _dt(body6.get("due_at"))
        expect6 = datetime.now(timezone.utc) + timedelta(days=2)
        # 三处断言：200 / deferred_days=2 / due_at 确实前移到 now+2d 且晚于原排期
        on_target = after6 is not None and abs((after6 - expect6).total_seconds()) <= 300
        forward = after6 is not None and (before6 is None or after6 > before6)
        ok6 = r6.status_code == 200 and body6.get("deferred_days") == 2 and on_target and forward
        detail6 = f"卡={card['id']} 状态={r6.status_code} 原={card.get('due_at')} 新={body6.get('due_at')}"
    step("路径6 复习：延后 2 天（due_at 前移）", ok6,
         f"{(time.perf_counter() - t0):.1f}s {detail6}")

    # 路径 7：按题型组卷 —— 返回题的 qtype 必须全部为 single；无单选题记 SKIP
    t0 = time.perf_counter()
    r7 = c.post("/api/quiz/generate", json={"count": 3, "mode": "new", "qtype": "single"})
    qs7 = (r7.json().get("data") or []) if r7.status_code == 200 else []
    if r7.status_code != 200:
        step("路径7 刷题：按题型筛选（qtype=single）", False,
             f"{(time.perf_counter() - t0):.1f}s 状态={r7.status_code} {r7.text[:120]}")
    elif not qs7:
        skip("路径7 刷题：按题型筛选（qtype=single）", "题库无单选题")
    else:
        types7 = sorted({(q.get("qtype") or "") for q in qs7})
        step("路径7 刷题：按题型筛选（qtype=single）", types7 == ["single"],
             f"{(time.perf_counter() - t0):.1f}s 题数={len(qs7)} 题型={types7}")

    # 路径 8：批量重置真实卡 + 批量删除不存在的 id（后者走 failed，不能 500）
    t0 = time.perf_counter()
    ok8, detail8 = False, "无可用卡片"
    if card:
        rr = c.post("/api/cards/batch-reset", json={"ids": [card["id"]]})
        rb = (rr.json().get("data") or {}) if rr.status_code == 200 else {}
        reset_ok = rr.status_code == 200 and int(rb.get("succeeded") or 0) >= 1
        rd = c.post("/api/cards/batch-delete", json={"ids": [999999999]})
        db8 = (rd.json().get("data") or {}) if rd.status_code == 200 else {}
        del_ok = rd.status_code == 200 and int(db8.get("failed") or 0) >= 1
        ok8 = reset_ok and del_ok
        detail8 = (f"重置={rb.get('succeeded')} 删除failed={db8.get('failed')} "
                   f"状态={rr.status_code}/{rd.status_code}")
    step("路径8 卡片：批量重置 + 批量删除异常 id", ok8,
         f"{(time.perf_counter() - t0):.1f}s {detail8}")

    passed = sum(1 for _, ok, _ in rows if ok)
    print(f"\n通过 {passed}/{len(rows)}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
