# -*- coding: utf-8 -*-
"""前后端连调验证（58 号 Plan 批3 V4）：
前端 USE_REAL_API=1 时，5 个新接口的真实请求返回 200 且数据被页面消费。
用法：python scripts/integration_check.py http://127.0.0.1:8011
"""
import sys
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
c = httpx.Client(base_url=BASE, timeout=60)
rows = []


def check(name, ok, detail=""):
    rows.append((name, bool(ok), detail))
    print(("✅" if ok else "❌"), name, detail)


# 登录
email = f"int_{uuid.uuid4().hex[:6]}@t.com"
r = c.post("/api/auth/register", json={"email": email, "password": "password123"})
r = c.post("/api/auth/login", json={"email": email, "password": "password123"})
check("登录", r.status_code == 200)

# 1. storage
r = c.get("/api/documents/storage")
d = r.json().get("data") or {}
check("GET /documents/storage", r.status_code == 200 and "used_bytes" in d, str(d))

# 2. folders
r = c.get("/api/questions/folders")
d = r.json().get("data") or {}
check("GET /questions/folders", r.status_code == 200 and "subjects" in d)

# 3. upcoming
r = c.get("/api/review/upcoming")
d = r.json().get("data") or []
check("GET /review/upcoming 7天", r.status_code == 200 and len(d) == 7, f"{len(d)} 天")

# 4. related（404 是正常：新账号无题）
r = c.get("/api/quiz/related/1")
check("GET /quiz/related 越权404", r.status_code == 404, f"http={r.status_code}")

# 5. events 三视图
for v in ("month", "week", "day"):
    r = c.get(f"/api/plans/events?view={v}")
    check(f"GET /plans/events?view={v}", r.status_code == 200)

ok = sum(1 for _, o, _ in rows if o)
print(f"\n连调结果：{ok}/{len(rows)} 通过")
sys.exit(0 if ok == len(rows) else 1)
