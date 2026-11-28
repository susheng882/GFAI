# -*- coding: utf-8 -*-
"""缺口补齐接口测试（58 号 Plan 批2）：storage/folders/upcoming/related/events。

每个接口 ≥2 条用例（正常 + 边界/越权）。
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth(client):
    email = f"gap_{uuid.uuid4().hex[:8]}@t.com"
    client.post("/api/auth/register", json={"email": email, "password": "password123"})
    client.post("/api/auth/login", json={"email": email, "password": "password123"})
    return client


# ---------- storage ----------
def test_storage_empty_user(auth):
    r = auth.get("/api/documents/storage")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["used_bytes"] == 0
    assert isinstance(d["dist"], list)


def test_storage_shape(auth):
    d = auth.get("/api/documents/storage").json()["data"]
    for k in ("used_bytes", "used", "quota", "dist"):
        assert k in d


# ---------- folders ----------
def test_folders_empty(auth):
    r = auth.get("/api/questions/folders")
    assert r.status_code == 200
    d = r.json()["data"]
    assert "subjects" in d and "total" in d


def test_folders_shape(auth):
    d = auth.get("/api/questions/folders").json()["data"]
    assert d["total"] == 0  # 新账号无题库
    assert d["subjects"] == []


# ---------- upcoming ----------
def test_upcoming_seven_days(auth):
    r = auth.get("/api/review/upcoming")
    assert r.status_code == 200
    data = r.json()["data"]
    assert len(data) == 7
    for x in data:
        assert "day" in x and "count" in x
        assert x["count"] == 0  # 新账号无到期卡


def test_upcoming_days_monotonic(auth):
    data = auth.get("/api/review/upcoming").json()["data"]
    days = [x["day"] for x in data]
    assert days == sorted(days)  # 日期递增


# ---------- related ----------
def test_related_not_found(auth):
    r = auth.get("/api/quiz/related/999999")
    assert r.status_code == 404


def test_related_cross_user(auth):
    """他人题目返回 404（user_id 过滤）。"""
    r = auth.get("/api/quiz/related/1")  # uid=111 的题目 id=1
    assert r.status_code == 404


# ---------- events ----------
def test_events_month_empty(auth):
    r = auth.get("/api/plans/events?view=month")
    assert r.status_code == 200
    assert r.json()["data"] == []


def test_events_views(auth):
    for v in ("month", "week", "day"):
        r = auth.get(f"/api/plans/events?view={v}")
        assert r.status_code == 200
