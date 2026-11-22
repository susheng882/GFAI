"""CI 冒烟：不依赖任何外部模型，只验证"服务能起、能注册、能读数据"。

用法：服务已在 127.0.0.1:8010 运行时，python scripts/ci_smoke.py
"""
from __future__ import annotations

import os
import sys
import uuid

import httpx

BASE = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:8010")
ok, fail = 0, 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {name} {detail}")
    else:
        fail += 1
        print(f"  FAIL  {name} {detail}")


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=30)

    r = c.get("/health")
    check("GET /health", r.status_code == 200 and r.json().get("ok") is True)

    email = f"ci_{uuid.uuid4().hex[:8]}@example.com"
    r = c.post("/api/auth/register", json={"email": email, "password": "ci-password-123"})
    check("POST /auth/register", r.status_code == 200, f"({r.status_code})")

    r = c.get("/api/auth/me")
    body = r.json() if r.status_code == 200 else {}
    me = (body.get("data") or {}).get("user") or {}
    check("GET /auth/me", body.get("ok") is True and me.get("email") == email)

    for path in ("/api/documents", "/api/questions", "/api/notes",
                 "/api/decks", "/api/tasks", "/api/dashboard/stats"):
        r = c.get(path)
        check(f"GET {path}", r.status_code == 200 and r.json().get("ok") is True,
              f"({r.status_code})")

    r = c.post("/api/qa", json={"question": "冒烟测试", "strategy": "model"})
    check("POST /qa 可用（Mock 模式下允许拒答）", r.status_code == 200, f"({r.status_code})")

    print(f"\n冒烟结果：{ok} 通过 / {fail} 失败")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
