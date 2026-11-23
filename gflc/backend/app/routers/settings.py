# -*- coding: utf-8 -*-
"""配置中心 API（对标 BiliNote 设置页）：供应商 / 模型 / 运行时 / Cookie / 诊断 / 监控。

安全约定：
- 任何接口都不返回明文 Key，只返回掩码；
- 所有写操作要求登录；配置为全局（单实例部署），不按用户隔离。
"""
import os
import shutil
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import ark
from app.core.config import settings
from app.core.errors import APIError, ErrCode
from app.db.session import get_db
from app.models.models import AiModel, AiProvider, PlatformCookie, Task
from app.routers.deps import get_current_user
from app.services import settings_store as store

router = APIRouter(prefix="/settings")


# --------------------------- 供应商 ---------------------------
class ProviderIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    kind: str = "openai"          # openai | ark | deepseek | groq
    base_url: str = ""
    api_key: str = ""             # 空=不修改（PATCH 时）
    enabled: bool = True
    is_default: bool = False


def _refresh(db: Session) -> None:
    try:
        store.refresh_cache(db)
    except Exception:  # noqa: BLE001
        pass


def _prov_out(p: AiProvider) -> dict:
    plain = store.decrypt(p.api_key_enc)
    return {"id": p.id, "name": p.name, "kind": p.kind, "base_url": p.base_url,
            "api_key_masked": store.mask(plain), "has_key": bool(plain),
            "enabled": bool(p.enabled), "is_default": bool(p.is_default), "sort": p.sort}


@router.get("/providers")
def list_providers(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AiProvider).order_by(AiProvider.sort, AiProvider.id)).all()
    counts = dict(db.execute(
        select(AiModel.provider_id, func.count(AiModel.id)).group_by(AiModel.provider_id)
    ).all())
    return {"ok": True, "data": [{**_prov_out(p), "model_count": counts.get(p.id, 0)} for p in rows]}


@router.post("/providers")
def create_provider(body: ProviderIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if body.is_default:
        db.query(AiProvider).update({AiProvider.is_default: 0})
    p = AiProvider(name=body.name, kind=body.kind, base_url=body.base_url.strip(),
                   api_key_enc=store.encrypt(body.api_key), enabled=1 if body.enabled else 0,
                   is_default=1 if body.is_default else 0, sort=99)
    db.add(p)
    db.commit()
    _refresh(db)
    db.refresh(p)
    return {"ok": True, "data": _prov_out(p)}


@router.patch("/providers/{pid}")
def update_provider(pid: int, body: ProviderIn, user=Depends(get_current_user),
                    db: Session = Depends(get_db)):
    p = db.get(AiProvider, pid)
    if p is None:
        raise APIError(ErrCode.COMMON_404, "供应商不存在", 404)
    p.name, p.kind, p.base_url = body.name, body.kind, body.base_url.strip()
    if body.api_key:
        p.api_key_enc = store.encrypt(body.api_key)
    p.enabled = 1 if body.enabled else 0
    if body.is_default:
        db.query(AiProvider).update({AiProvider.is_default: 0})
        p.is_default = 1
    db.commit()
    _refresh(db)
    return {"ok": True, "data": _prov_out(p)}


@router.delete("/providers/{pid}")
def delete_provider(pid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.get(AiProvider, pid)
    if p is None:
        raise APIError(ErrCode.COMMON_404, "供应商不存在", 404)
    db.query(AiModel).filter(AiModel.provider_id == pid).delete(synchronize_session=False)
    db.delete(p)
    db.commit()
    _refresh(db)
    return {"ok": True, "data": {"deleted": pid}}


# --------------------------- 模型 ---------------------------
class ModelIn(BaseModel):
    provider_id: int
    model_id: str = Field(min_length=1, max_length=96)
    label: str = ""
    purpose: str = "note"         # note | vision | long | chat | transcribe
    enabled: bool = True
    is_default: bool = False


def _model_out(m: AiModel) -> dict:
    return {"id": m.id, "provider_id": m.provider_id, "model_id": m.model_id,
            "label": m.label, "purpose": m.purpose, "enabled": bool(m.enabled),
            "is_default": bool(m.is_default), "probe_status": m.probe_status,
            "probe_note": m.probe_note,
            "probed_at": m.probed_at.isoformat() if m.probed_at else None}


@router.get("/models")
def list_models(purpose: str | None = None, user=Depends(get_current_user),
                db: Session = Depends(get_db)):
    stmt = select(AiModel).order_by(AiModel.purpose, AiModel.is_default.desc(), AiModel.id)
    if purpose:
        stmt = stmt.where(AiModel.purpose == purpose)
    rows = db.scalars(stmt).all()
    return {"ok": True, "data": [_model_out(m) for m in rows]}


@router.post("/models")
def create_model(body: ModelIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(AiProvider, body.provider_id) is None:
        raise APIError(ErrCode.COMMON_404, "供应商不存在", 404)
    if body.is_default:
        db.query(AiModel).filter(AiModel.purpose == body.purpose).update({AiModel.is_default: 0})
    m = AiModel(provider_id=body.provider_id, model_id=body.model_id.strip(), label=body.label,
                purpose=body.purpose, enabled=1 if body.enabled else 0,
                is_default=1 if body.is_default else 0)
    db.add(m)
    db.commit()
    _refresh(db)
    db.refresh(m)
    return {"ok": True, "data": _model_out(m)}


@router.patch("/models/{mid}")
def update_model(mid: int, body: ModelIn, user=Depends(get_current_user),
                 db: Session = Depends(get_db)):
    m = db.get(AiModel, mid)
    if m is None:
        raise APIError(ErrCode.COMMON_404, "模型不存在", 404)
    m.provider_id, m.model_id, m.label = body.provider_id, body.model_id.strip(), body.label
    m.purpose = body.purpose
    m.enabled = 1 if body.enabled else 0
    if body.is_default:
        db.query(AiModel).filter(AiModel.purpose == body.purpose).update({AiModel.is_default: 0})
        m.is_default = 1
    db.commit()
    _refresh(db)
    return {"ok": True, "data": _model_out(m)}


@router.delete("/models/{mid}")
def delete_model(mid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    m = db.get(AiModel, mid)
    if m is None:
        raise APIError(ErrCode.COMMON_404, "模型不存在", 404)
    db.delete(m)
    db.commit()
    _refresh(db)
    return {"ok": True, "data": {"deleted": mid}}


@router.post("/models/{mid}/probe")
def probe_model(mid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """真调一次 chat 探活：不仅看 /models 列表，而是确认「账号已开通」。"""
    m = db.get(AiModel, mid)
    if m is None:
        raise APIError(ErrCode.COMMON_404, "模型不存在", 404)
    prov = db.get(AiProvider, m.provider_id)
    key = store.decrypt(prov.api_key_enc) if prov else ""
    if not key:
        m.probe_status, m.probe_note = "error", "未配置 API Key"
        db.commit()
        return {"ok": True, "data": _model_out(m)}

    import asyncio
    from app.ai import ark as ark_mod
    from app.core.config import settings as cfg

    ok, note = False, ""
    t0 = time.perf_counter()
    try:
        if prov.kind == "ark":
            # 临时覆写，复用 ark.chat（不改全局配置）
            prev_key, prev_base = cfg.ARK_API_KEY, cfg.ARK_API_BASE
            cfg.ARK_API_KEY, cfg.ARK_API_BASE = key, prov.base_url or prev_base
            try:
                res = asyncio.run(ark_mod.chat(m.model_id, [{"role": "user", "content": "ok"}],
                                               max_tokens=8))
                ok = res.text is not None
            finally:
                cfg.ARK_API_KEY, cfg.ARK_API_BASE = prev_key, prev_base
        else:
            import httpx
            url = (prov.base_url or "https://api.deepseek.com/v1").rstrip("/") + "/chat/completions"
            r = httpx.post(url, headers={"Authorization": f"Bearer {key}"},
                           json={"model": m.model_id, "messages": [{"role": "user", "content": "ok"}],
                                 "max_tokens": 8}, timeout=40)
            ok = r.status_code == 200
            note = "" if ok else r.text[:120]
    except Exception as e:  # noqa: BLE001
        note = str(e)[:120]
    m.probe_status = "ok" if ok else ("not_activated" if "not activated" in note else "error")
    m.probe_note = note
    m.probed_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "data": {**_model_out(m), "latency_ms": round((time.perf_counter() - t0) * 1000)}}


# --------------------------- 运行时配置 ---------------------------
@router.get("/runtime")
def get_runtime(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return {"ok": True, "data": store.all_runtime(db)}


@router.put("/runtime")
def put_runtime(body: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    allowed = set(store.RUNTIME_DEFAULTS)
    changed = {}
    for k, v in (body or {}).items():
        if k in allowed:
            store.set_runtime(db, k, "" if v is None else str(v))
            changed[k] = str(v)
    return {"ok": True, "data": {"changed": changed, "all": store.all_runtime(db)}}


# --------------------------- Cookie ---------------------------
@router.get("/cookies")
def list_cookies(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(PlatformCookie)).all()
    out = [{"platform": r.platform, "has_cookie": bool(r.cookie_enc),
            "note": r.note, "updated_at": r.updated_at.isoformat() if r.updated_at else None}
           for r in rows]
    have = {r["platform"] for r in out}
    for p in ("bilibili", "youtube", "douyin"):
        if p not in have:
            out.append({"platform": p, "has_cookie": False, "note": "", "updated_at": None})
    return {"ok": True, "data": out}


@router.put("/cookies")
def put_cookie(body: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    platform = str((body or {}).get("platform") or "").strip()
    if platform not in ("bilibili", "youtube", "douyin"):
        raise APIError(ErrCode.COMMON_400, "不支持的平台", 400)
    cookie = str((body or {}).get("cookie") or "").strip()
    store.set_cookie(db, platform, cookie, str((body or {}).get("note") or "")[:120])
    return {"ok": True, "data": {"platform": platform, "has_cookie": bool(cookie)}}


# --------------------------- 诊断 / 监控 ---------------------------
@router.get("/diagnostics")
def diagnostics(user=Depends(get_current_user), db: Session = Depends(get_db)):
    def which(name: str) -> str:
        return shutil.which(name) or ""

    ffmpeg = which("ffmpeg")
    checks = [
        {"item": "ffmpeg", "ok": bool(ffmpeg), "detail": ffmpeg or "未安装（抽帧/抽音频不可用）"},
        {"item": "yt-dlp", "ok": bool(which("yt-dlp")) or _has_module("yt_dlp"),
         "detail": "内置 python 模块可用" if _has_module("yt_dlp") else "缺失"},
        {"item": "faster-whisper", "ok": _has_module("faster_whisper"),
         "detail": f"模型 {settings.WHISPER_MODEL}，并行 {getattr(settings, 'WHISPER_PARALLEL', 1)} 片"},
        {"item": "方舟 Key", "ok": ark.available(), "detail": "已配置" if ark.available() else "未配置"},
        {"item": "必剪云转写", "ok": settings.BCUT_ENABLED, "detail": "开启（失败自动降级）" if settings.BCUT_ENABLED else "关闭"},
        {"item": "B站 Cookie", "ok": bool(store.get_cookie(db, "bilibili")),
         "detail": "已配置（可拉官方字幕）" if store.get_cookie(db, "bilibili") else "未配置：AI 字幕不可用"},
        {"item": "存储目录", "ok": os.path.isdir(settings.LOCAL_STORAGE_DIR),
         "detail": os.path.abspath(settings.LOCAL_STORAGE_DIR)},
    ]
    return {"ok": True, "data": {"checks": checks, "app_env": settings.APP_ENV,
                                 "database": str(settings.DATABASE_URL).split("://")[0]}}


def _has_module(name: str) -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _alert_threshold(env: str, default: float, cast=float) -> tuple[float, dict]:
    """读取告警阈值：未配置/非法值回退默认值，并在响应里标明来源。"""
    raw = os.getenv(env)
    if raw is None or not str(raw).strip():
        return default, {"value": default, "source": "default", "env": env, "env_set": False}
    try:
        val = cast(str(raw).strip())
    except (TypeError, ValueError):
        return default, {"value": default, "source": f"invalid({env})->default",
                         "env": env, "env_set": True}
    return val, {"value": val, "source": f"env:{env}", "env": env, "env_set": True}


@router.get("/alerts")
def alerts(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """B15：失败率 / 队列积压 / 今日成本三类阈值状态。

    只做「计算并暴露状态」，不接任何外部 webhook（零外部依赖）。
    所有阈值用 os.getenv 读取，未配置时用默认值并在 thresholds.*.source 标出。
    """
    from datetime import timedelta

    from app.models.models import CostLedger
    from app.worker import runner as w

    fail_th, fail_src = _alert_threshold("GFLC_ALERT_FAILURE_RATE", 0.20, float)
    win_h, win_src = _alert_threshold("GFLC_ALERT_FAILURE_WINDOW_HOURS", 24, int)
    backlog_th, backlog_src = _alert_threshold("GFLC_ALERT_QUEUE_BACKLOG", 20, int)
    cost_th, cost_src = _alert_threshold("GFLC_ALERT_DAILY_COST_CNY", 50.0, float)

    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=max(1, win_h))
    total_tasks = int(db.scalar(select(func.count(Task.id)).where(Task.created_at >= since)) or 0)
    failed_tasks = int(db.scalar(
        select(func.count(Task.id)).where(Task.created_at >= since, Task.status == "failed")
    ) or 0)
    failure_rate = round(failed_tasks / total_tasks, 4) if total_tasks else 0.0

    day_row = db.execute(
        select(func.count(CostLedger.id), func.sum(CostLedger.cost_cny),
               func.sum(CostLedger.prompt_tokens + CostLedger.completion_tokens))
        .where(CostLedger.created_at >= now - timedelta(days=1))
    ).first()
    today_cost = round(float(day_row[1] or 0), 4) if day_row else 0.0
    today_calls = int(day_row[0] or 0) if day_row else 0
    today_tokens = int(day_row[2] or 0) if day_row else 0

    health = w.health()
    main_queue = int(health.get("queue_size") or 0)
    video_queue = int(health.get("video_queue_size") or 0)
    backlog = main_queue + video_queue

    def _alert(code: str, name: str, current, threshold, exceeded_hint: str) -> dict:
        exceeded = bool(current > threshold)
        return {"code": code, "name": name, "current": current, "threshold": threshold,
                "exceeded": exceeded, "level": "warn" if exceeded else "ok",
                "hint": exceeded_hint if exceeded else ""}

    checks = [
        _alert("FAILURE_RATE", "任务失败率", failure_rate, fail_th,
               f"近 {win_h} 小时失败率超过阈值，请查看 /settings/monitor 的最近失败任务"),
        _alert("QUEUE_BACKLOG", "队列积压", backlog, backlog_th,
               "主队列 + 视频队列积压超过阈值，请检查 Worker 健康状态"),
        _alert("DAILY_COST", "今日成本(元)", today_cost, cost_th,
               "近 24 小时模型成本超过阈值，请检查 /settings/monitor 的模型用量"),
    ]
    return {"ok": True, "data": {
        "generated_at": now.isoformat(),
        "window_hours": win_h,
        "metrics": {
            "failure_rate": failure_rate,
            "failure_counts": {"failed": failed_tasks, "total": total_tasks},
            "queue_backlog": backlog,
            "queue_detail": {"queue_size": main_queue, "video_queue_size": video_queue,
                             "worker_alive": bool(health.get("alive")),
                             "queue_backend": health.get("queue_backend")},
            "today_cost_cny": today_cost,
            "today_cost_detail": {"calls": today_calls, "tokens": today_tokens},
        },
        "thresholds": {
            "failure_rate": fail_src, "window_hours": win_src,
            "queue_backlog": backlog_src, "daily_cost_cny": cost_src,
        },
        "alerts": checks,
        "any_alert": any(a["exceeded"] for a in checks),
        "webhook_enabled": False,
        "note": "仅计算并暴露状态，不接外部 webhook；阈值来源见 thresholds.*.source",
    }}


@router.get("/monitor")
def monitor(user=Depends(get_current_user), db: Session = Depends(get_db)):
    by_status = dict(db.execute(select(Task.status, func.count(Task.id)).group_by(Task.status)).all())
    by_type = dict(db.execute(
        select(Task.type, func.count(Task.id)).where(Task.status == "running").group_by(Task.type)
    ).all())
    fails = db.scalars(select(Task).where(Task.status == "failed")
                       .order_by(Task.id.desc()).limit(8)).all()
    # 模型调用与成本：按模型聚合 + 今日合计（监控页要看的是"用了多少"，不只是任务数）
    from app.models.models import CostLedger
    from datetime import datetime as _dt, timedelta as _td, timezone as _tz
    today = _dt.now(_tz.utc) - _td(days=1)
    usage = db.execute(
        select(CostLedger.model, func.count(CostLedger.id), func.sum(CostLedger.prompt_tokens),
               func.sum(CostLedger.completion_tokens), func.sum(CostLedger.cost_cny))
        .group_by(CostLedger.model).order_by(func.sum(CostLedger.cost_cny).desc()).limit(10)
    ).all()
    day_row = db.execute(
        select(func.count(CostLedger.id), func.sum(CostLedger.cost_cny),
               func.sum(CostLedger.prompt_tokens + CostLedger.completion_tokens))
        .where(CostLedger.created_at >= today)
    ).first()
    by_type = dict(db.execute(
        select(Task.type, func.count(Task.id)).group_by(Task.type)
    ).all())
    from app.worker import runner as w
    return {"ok": True, "data": {
        "tasks_by_status": by_status,
        "running_by_type": by_type,
        "worker": w.health(),
        "recent_failures": [{"id": t.id, "type": t.type, "code": t.error_code,
                             "error": (t.error_message or "")[:300],
                             "at": t.updated_at.isoformat() if t.updated_at else None} for t in fails],
        "tasks_by_type": by_type,
        "model_usage": [{"model": m, "calls": c, "in": int(i or 0), "out": int(o or 0),
                         "cost": round(float(cost or 0), 4)} for m, c, i, o, cost in usage],
        "today": {"calls": int(day_row[0] or 0) if day_row else 0,
                  "cost": round(float(day_row[1] or 0), 4) if day_row else 0,
                  "tokens": int(day_row[2] or 0) if day_row else 0},
    }}
