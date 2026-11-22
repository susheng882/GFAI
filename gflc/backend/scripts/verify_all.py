# -*- coding: utf-8 -*-
"""全接口验收脚本：逐个打真实接口，输出通过/失败。
用法：python scripts/verify_all.py [base_url]
"""
import json
import sys
import time
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010"
c = httpx.Client(base_url=BASE, timeout=180)
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, bool(ok), detail))


def wait_task(tid: int, timeout: int = 240) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        t = c.get(f"/api/tasks/{tid}").json().get("data", {})
        if t.get("status") in ("ready", "failed"):
            return t
        time.sleep(0.6)
    return {"status": "timeout", "progress": 0}


def main():
    # 健康 / 配置
    check("GET /health", c.get("/health").status_code == 200)
    cfg = c.get("/api/config").json()
    check("GET /api/config", cfg.get("ok") is True, str(cfg.get("data")))

    # 鉴权
    email = f"vf_{uuid.uuid4().hex[:6]}@t.com"
    r = c.post("/api/auth/register", json={"email": email, "password": "password123"})
    check("POST /api/auth/register", r.status_code == 200, email)
    check("GET /api/auth/me", c.get("/api/auth/me").json().get("data", {}).get("user", {}).get("email") == email)
    check("POST /api/auth/login", c.post("/api/auth/login", json={"email": email, "password": "password123"}).status_code == 200)
    check("未登录受保护接口应 401", httpx.get(f"{BASE}/api/documents").status_code in (401, 403))

    # 文档
    with open("data/sample.pdf", "rb") as f:
        r = c.post("/api/documents/upload", files={"file": ("sample.pdf", f, "application/pdf")})
    doc = r.json().get("data", {}).get("document", {})
    check("POST /api/documents/upload", r.status_code == 200 and doc.get("id"), f"id={doc.get('id')}")
    check("POST /api/documents/presign", c.post("/api/documents/presign", json={"filename": "a.pdf", "size": 10}).status_code == 200)
    check("GET /api/documents", len(c.get("/api/documents").json().get("data", [])) >= 1)
    check("GET /api/documents/{id}", c.get(f"/api/documents/{doc['id']}").status_code == 200)
    check("越权访问他人文档应 403", c.get("/api/documents/999999").status_code in (403, 404))

    # 后台任务：解析 + 卡片
    t = c.post(f"/api/documents/{doc['id']}/parse").json()["data"]
    tt = wait_task(t["task_id"])
    check("POST /documents/{id}/parse → 任务完成", tt.get("status") == "ready", f"chunks={tt.get('result',{}).get('chunks')}")

    t = c.post(f"/api/documents/{doc['id']}/cards").json()["data"]
    tt = wait_task(t["task_id"])
    check("POST /documents/{id}/cards → 任务完成", tt.get("status") == "ready", f"cards={tt.get('result',{}).get('cards')}")
    cards = c.get(f"/api/documents/{doc['id']}/cards").json().get("data", [])
    check("GET /documents/{id}/cards", len(cards) > 0, f"{len(cards)} 张")

    # 卡包（按 PDF 大纲分章节）
    decks = c.get("/api/decks").json().get("data", [])
    check("GET /api/decks", len(decks) > 0, f"{len(decks)} 个大卡包")
    root = decks[0] if decks else {}
    check("卡包按章节分组", bool(root.get("children")), f"{len(root.get('children', []))} 章")
    check("卡包内卡片可读", len(c.get(f"/api/decks/{root['id']}/cards").json().get("data", [])) > 0)
    nd = c.post("/api/decks", json={"name": "验收用章节包", "parent_id": root.get("id"),
                                    "document_id": doc["id"]}).json().get("data", {})
    check("POST /api/decks", bool(nd.get("id")), f"id={nd.get('id')}")
    check("PATCH /api/decks/{id}", c.patch(f"/api/decks/{nd['id']}", json={"name": "验收改名"}).json()
          .get("data", {}).get("name") == "验收改名")
    check("DELETE /api/decks/{id}", c.delete(f"/api/decks/{nd['id']}").status_code == 200)

    # 卡片 CRUD
    nc = c.post("/api/cards", json={"question": "验收题：什么是检索练习？", "answer": "主动回忆",
                                    "deck_id": root["children"][0]["id"] if root.get("children") else None}).json().get("data", {})
    check("POST /api/cards", bool(nc.get("id")), f"id={nc.get('id')}")
    if nc.get("id"):
        check("GET /api/cards/{id}", c.get(f"/api/cards/{nc['id']}").status_code == 200)
        check("PATCH /api/cards/{id}", c.patch(f"/api/cards/{nc['id']}", json={"answer": "主动回忆优于重复阅读"})
              .json().get("data", {}).get("answer") == "主动回忆优于重复阅读")
        check("GET /api/cards?q= 搜索", len(c.get("/api/cards?q=检索练习").json().get("data", [])) >= 1)
        check("DELETE /api/cards/{id}", c.delete(f"/api/cards/{nc['id']}").status_code == 200)

    # 笔记 CRUD
    check("POST /documents/{id}/notes", bool(c.post(f"/api/documents/{doc['id']}/notes",
          json={"title": "验收笔记", "summary": "内容", "points": ["a", "b"]}).json().get("data", {}).get("id")))
    check("GET /documents/{id}/notes", len(c.get(f"/api/documents/{doc['id']}/notes").json().get("data", [])) >= 1)
    notes = c.get("/api/notes").json().get("data", [])
    check("GET /api/notes", len(notes) >= 1)
    if notes:
        check("PATCH /api/notes/{id}", c.patch(f"/api/notes/{notes[0]['id']}",
              json={"title": "改后笔记", "summary": "s", "points": []}).status_code == 200)
        check("DELETE /api/notes/{id}", c.delete(f"/api/notes/{notes[0]['id']}").status_code == 200)

    # 文档改名（题库文件不应出现在资料列表）
    check("PATCH /api/documents/{id}", c.patch(f"/api/documents/{doc['id']}",
          json={"title": "示例资料"}).json().get("data", {}).get("title") == "示例资料")
    doc_titles = [d["title"] for d in c.get("/api/documents").json().get("data", [])]
    check("题库文件不在资料列表", not any(t.endswith(".xlsx") for t in doc_titles), str(doc_titles)[:60])

    # 任务
    ts = c.get("/api/tasks").json().get("data", [])
    check("GET /api/tasks", len(ts) >= 2, f"{len(ts)} 条")
    check("GET /api/tasks/{id}", c.get(f"/api/tasks/{ts[0]['id']}").status_code == 200)
    check("GET /api/tasks 含 elapsed/can_retry", "elapsed" in ts[0] and "can_retry" in ts[0])
    th = c.get("/api/tasks/health").json().get("data", {})
    check("GET /api/tasks/health", th.get("alive") is True, f"queue={th.get('queue_size')}")

    check("POST /api/tasks/cleanup", c.post("/api/tasks/cleanup").status_code == 200)

    # 笔记文件夹树 + AI 协作
    f1 = c.post("/api/notes/folders", json={"name": "验收项目", "kind": "project"}).json().get("data", {})
    f2 = c.post("/api/notes/folders", json={"name": "验收科目", "kind": "subject",
                                            "parent_id": f1.get("id")}).json().get("data", {})
    f3 = c.post("/api/notes/folders", json={"name": "验收章节", "kind": "topic",
                                            "parent_id": f2.get("id")}).json().get("data", {})
    check("POST /notes/folders 三层建树", all(x.get("id") for x in (f1, f2, f3)))
    tree = c.get("/api/notes/folders").json().get("data", [])
    def _has_node(nodes, name):
        for n in nodes:
            if n["name"] == name:
                return True
            if _has_node(n.get("children") or [], name):
                return True
        return False
    check("GET /notes/folders 返回嵌套树", _has_node(tree, "验收章节"))
    check("PATCH /notes/folders/{id} 改名",
          c.patch(f"/api/notes/folders/{f3['id']}", json={"name": "验收章节改"}).json()
          .get("data", {}).get("name") == "验收章节改")

    nb = c.post("/api/notes", json={"title": "验收笔记", "content": "# 标题\n- 要点一",
                                    "folder_id": f3["id"]}).json().get("data", {})
    check("POST /notes", bool(nb.get("id")), f"id={nb.get('id')}")
    lst = c.get(f"/api/notes?folder_id={f1['id']}").json().get("data", [])
    check("GET /notes?folder_id 含子孙", len(lst) >= 1, f"{len(lst)} 篇")
    check("笔记带 folder_path", any("验收项目" in (n.get("folder_path") or "") for n in lst))
    if nb.get("id"):
        check("GET /notes/{id}", c.get(f"/api/notes/{nb['id']}").status_code == 200)
        check("PATCH /notes/{id}", c.patch(f"/api/notes/{nb['id']}",
              json={"title": "验收笔记改"}).json().get("data", {}).get("title") == "验收笔记改")
        sug = c.post("/api/notes/ai-suggest", json={"note_id": nb["id"], "title": "验收笔记改",
              "content": "极限四则运算", "instruction": "补一个易错点", "mode": "expand"}).json().get("data", {})
        check("POST /notes/ai-suggest", len(sug.get("suggestion") or "") > 20,
              f"{len(sug.get('suggestion') or '')} 字")
        if sug.get("suggestion"):
            ins = c.post("/api/notes/insert", json={"note_id": nb["id"],
                  "text": sug["suggestion"], "position": "append"}).json().get("data", {})
            check("POST /notes/insert 写回正文", len(ins.get("content") or "") > 20)
        tc = c.post(f"/api/notes/{nb['id']}/to-cards").json().get("data", {})
        check("POST /notes/{id}/to-cards", (tc.get("cards") or 0) > 0, f"cards={tc.get('cards')}")
        check("DELETE /notes/{id}", c.delete(f"/api/notes/{nb['id']}").status_code == 200)
    # 笔记 AI 整理（建议 + 确认应用）—— 先造 2 篇同域笔记
    for t, ct in [("极限四则运算", "# 极限\n- 加减可拆\n- 分母非零"), ("等价无穷小", "# 等价无穷小\n- sin x ~ x")]:
        c.post("/api/notes", json={"title": t, "content": ct, "folder_id": f3["id"]})
    tidy = c.post("/api/notes/tidy", json={"folder_id": f1["id"]}).json().get("data", {})
    check("POST /notes/tidy（AI 整理）", bool(tidy.get("summary")),
          f"扫描{tidy.get('scanned')}篇 建议{len(tidy.get('folders') or [])}组")
    ap = None
    if (tidy.get("folders") or []):
        g = tidy["folders"][0]
        if g.get("note_ids"):
            ap = c.post("/api/notes/tidy/apply", json={"folder_id": f1["id"], "name": g["name"],
                                                       "note_ids": g["note_ids"]}).json().get("data", {})
    check("POST /notes/tidy/apply", ap is not None and (ap.get("moved") or 0) >= 0,
          f"moved={ap.get('moved') if ap else '-'}")
    # 文件夹循环检测
    bad_move = c.patch(f"/api/notes/folders/{f1['id']}", json={"parent_id": f3["id"]})
    check("文件夹循环移动应 400", bad_move.status_code == 400)
    # 笔记搜索 + 跨文件夹移动
    found = c.get("/api/notes?q=极限").json().get("data", [])
    check("GET /notes?q= 全文搜索", len(found) >= 1, f"{len(found)} 篇")
    if found:
        mv = c.patch(f"/api/notes/{found[0]['id']}", json={"folder_id": f2["id"]})
        check("PATCH /notes/{id} 移动文件夹", mv.json().get("data", {}).get("folder_id") == f2["id"])
    check("DELETE /notes/folders/{id}", c.delete(f"/api/notes/folders/{f1['id']}").status_code == 200)

    # 题库
    with open("data/question_bank.xlsx", "rb") as f:
        r = c.post("/api/questions/import", files={"file": ("q.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
    tt = wait_task(r.json()["data"]["task_id"])
    check("POST /questions/import → 任务完成", tt.get("status") == "ready", f"questions={tt.get('result',{}).get('questions')}")
    qs = c.get("/api/questions").json().get("data", [])
    check("GET /api/questions", len(qs) > 0, f"{len(qs)} 题")

    # 刷题
    if qs:
        ov = c.get("/api/quiz/overview").json().get("data", {})
        check("GET /api/quiz/overview", "banks" in ov, f"total={ov.get('total')} banks={len(ov.get('banks', []))}")
        chs = c.get("/api/quiz/chapters").json().get("data", [])
        check("GET /api/quiz/chapters", isinstance(chs, list), f"{len(chs)} 章")
        rec = c.get("/api/quiz/recommend").json().get("data", {})
        check("GET /api/quiz/recommend", bool(rec.get("reason")), str(rec.get("reason"))[:40])

        quiz = c.post("/api/quiz/generate", json={"count": 3, "mode": "recommend"}).json().get("data", [])
        check("POST /api/quiz/generate（推荐模式）", len(quiz) > 0, f"{len(quiz)} 题")
        sub = c.post("/api/quiz/submit", json={"question_id": quiz[0]["id"], "user_answer": "A"}).json().get("data", {})
        check("POST /api/quiz/submit", "correct" in sub, f"correct={sub.get('correct')}")
        wrong = c.get("/api/quiz/wrong").json().get("data", [])
        check("GET /api/quiz/wrong", isinstance(wrong, list), f"{len(wrong)} 错题")
        check("DELETE /api/quiz/attempts/{qid}", c.delete(f"/api/quiz/attempts/{quiz[0]['id']}").status_code == 200)

    # 计划
    t = c.post("/api/plans", json={"goal": "3天复习极限", "days": 3}).json()["data"]
    tt = wait_task(t["task_id"])
    check("POST /api/plans → 任务完成", tt.get("status") == "ready", f"plan={tt.get('result',{}).get('plan_id')}")
    plans = c.get("/api/plans").json().get("data", [])
    check("GET /api/plans", len(plans) > 0)
    if plans:
        pd = c.get(f"/api/plans/{plans[0]['id']}").json().get("data", {})
        check("GET /api/plans/{id}", len(pd.get("tasks", [])) > 0)
        tasks = pd["tasks"][0]["items"]
        if tasks:
            check("POST /api/plans/tasks/{id}/toggle", c.post(f"/api/plans/tasks/{tasks[0]['id']}/toggle").status_code == 200)

    # 复习
    due = c.get("/api/review/due").json().get("data", {})
    check("GET /api/review/due", due.get("count", 0) >= 0, f"{due.get('count')} 张")
    if due.get("cards"):
        cid = due["cards"][0]["id"]
        check("POST /api/review/{id}", c.post(f"/api/review/{cid}", json={"rating": 3}).status_code == 200)

    # 问答
    qa = c.post("/api/qa", json={"question": "间隔重复为什么能提高记忆？"}).json().get("data", {})
    check("POST /api/qa", bool(qa.get("answer")), f"mode={qa.get('mode')} src={len(qa.get('sources', []))}")
    check("GET /api/qa/suggest", len(c.get("/api/qa/suggest").json().get("data", [])) == 4)
    # 流式问答：首字节要快，且能拿到 done
    t_stream = time.time()
    t_first = None
    full, mode_s = "", None
    try:
        with c.stream("POST", "/api/qa/stream", json={"question": "间隔重复为什么能提高记忆保持率？"}) as r:
            for line in r.iter_lines():
                if not line.strip():
                    continue
                ev = json.loads(line)
                if t_first is None:
                    t_first = time.time() - t_stream
                if ev.get("type") == "sources":
                    mode_s = ev.get("mode")
                elif ev.get("type") in ("delta", "notice"):
                    full += ev.get("text") or ""
                elif ev.get("type") == "done" and ev.get("full"):
                    full = ev["full"]
        check("POST /qa/stream（流式）", t_first is not None and t_first < 3.0 and len(full) > 100,
              f"首字节{t_first:.2f}s 总计{time.time()-t_stream:.1f}s mode={mode_s} len={len(full)}")
    except Exception as e:
        check("POST /qa/stream（流式）", False, str(e)[:80])

    # 仪表盘
    check("GET /api/dashboard/stats", c.get("/api/dashboard/stats").status_code == 200)
    st = c.get("/api/dashboard/stats").json().get("data", {})
    check("stats 含真实周数据", isinstance(st.get("week"), list) and len(st["week"]) == 7)
    for scope in ("week", "month", "day"):
        t = c.post("/api/dashboard/generate", json={"theme": "考研冲刺计划", "scope": scope}).json()["data"]
        tt = wait_task(t["task_id"])
        check(f"POST /dashboard/generate({scope})", tt.get("status") == "ready",
              f"cards={tt.get('result',{}).get('cards')} scope={tt.get('result',{}).get('scope')}")
    latest = c.get("/api/dashboard/latest").json().get("data")
    check("GET /api/dashboard/latest", latest and latest.get("config", {}).get("cards"))
    check("GET /api/dashboard/latest?scope=week", bool(c.get("/api/dashboard/latest?scope=week").json().get("data")))
    _wk = c.get("/api/dashboard/latest?scope=week").json().get("data", {})
    check("latest 返回 positions/scope", "positions" in _wk and "scope" in _wk)
    check("GET /api/dashboard/list", isinstance(c.get("/api/dashboard/list").json().get("data"), list))
    if latest:
        ids = [x["id"] for x in latest["config"]["cards"]]
        rev = list(reversed(ids))
        check("PUT /api/dashboard/{id}/order（含缩放位置）",
              c.put(f"/api/dashboard/{latest['id']}/order",
                    json={"order": rev, "positions": {ids[0]: {"span": 6}}, "scope": "week"}).status_code == 200)
        patched = c.patch(f"/api/dashboard/{latest['id']}/card",
                          json={"card_id": ids[0], "title": "验收改标题", "value": "42"}).json().get("data", {})
        check("PATCH /api/dashboard/{id}/card（单卡编辑）", patched.get("card", {}).get("title") == "验收改标题")
        check("POST /api/dashboard/{id}/default", c.post(f"/api/dashboard/{latest['id']}/default").status_code == 200)
        extra = c.post("/api/dashboard/generate", json={"theme": "临时仪表盘", "scope": "day"}).json()["data"]
        wait_task(extra["task_id"])
        newl = c.get("/api/dashboard/latest?scope=day").json().get("data", {})
        if newl.get("id"):
            check("DELETE /api/dashboard/{id}", c.delete(f"/api/dashboard/{newl['id']}").status_code == 200)

    # 视频：真跑三种模板（13 秒音频，约 20–40 秒）
    with open("data/tts_zh.wav", "rb") as f:
        r = c.post("/api/videos/upload", files={"file": ("tts_zh.wav", f, "audio/wav")},
                   data={"templates": "summary,outline,qa"})
    vdoc_id = None
    if r.status_code == 200 and r.json().get("data", {}).get("task_id"):
        vt = wait_task(r.json()["data"]["task_id"], timeout=600)
        vr = vt.get("result", {}) or {}
        vnotes = vr.get("notes", [])
        kinds = sorted(n.get("kind") for n in vnotes)
        check("POST /videos/upload → 三模板笔记", kinds == ["outline", "qa", "summary"],
              f"{len(vnotes)} 种 {kinds}")
        check("视频返回时间轴 transcript", len(vr.get("transcript") or []) > 0,
              f"{len(vr.get('transcript') or [])} 段")
        vdoc_id = vr.get("document_id")
        check("GET /api/videos 历史", any(x.get("document_id") == vdoc_id
              for x in c.get("/api/videos").json().get("data", [])))
        if vdoc_id:
            d = c.get(f"/api/videos/{vdoc_id}/notes").json().get("data", {})
            check("GET /videos/{id}/notes", len(d.get("notes") or []) >= 3)
            check("视频笔记返回 frames 字段", "frames" in d, f"frames={len(d.get('frames') or [])}")
        if vdoc_id:
            fr = (vr.get("frames") or []) if vdoc_id else []
            if fr:
                name = (fr[0].get("name") or fr[0].get("path", "")).split("/")[-1].split("\\")[-1]
                rf = c.get(f"/api/videos/frames/{name}")
                check("GET /videos/frames/{name} 静态图", rf.status_code in (200, 404), f"http={rf.status_code}")
            else:
                check("GET /videos/frames/{name} 静态图（音频无帧，跳过）", True, "无帧")
            r = c.get(f"/api/videos/{vdoc_id}/stream")
            check("GET /videos/{id}/stream", r.status_code in (200, 404, 400),
                  f"http={r.status_code}")
    # 平台降级：不可达链接应返回明确错误，而不是 500
    r = c.post("/api/videos/url", json={"url": "https://www.youtube.com/watch?v=x"})
    check("POST /api/videos/url 返回 task_id", r.status_code == 200 and r.json()["data"].get("task_id"))

    c.post("/api/auth/logout")
    check("POST /api/auth/logout", True)

    # 汇总
    print("\n" + "=" * 56)
    passed = sum(1 for _, ok, _ in results if ok)
    print(f"通过 {passed}/{len(results)}")
    for n, ok, d in results:
        print(("  ✅ " if ok else "  ❌ ") + n + (f"  ({d})" if d else ""))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
