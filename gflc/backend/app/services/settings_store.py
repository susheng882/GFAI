# -*- coding: utf-8 -*-
"""配置中心：密钥加解密 + 运行时配置读写 + 模型解析（DB 优先，env 兜底）。

设计约束
- 密钥只以密文落库（Fernet，key 由 SESSION_SECRET 派生），接口只返回掩码 `sk-****abcd`；
- 未在 DB 配置时自动回落到 .env（ARK_* / LLM_*），保证老部署不改也能跑；
- 所有读取都带默认值，任何一项缺失都不抛异常。
"""
import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import AiModel, AiProvider, AppSetting, PlatformCookie

_log = logging.getLogger(__name__)

# 运行时配置默认值（DB 无记录时使用；设置页可改）
RUNTIME_DEFAULTS: dict[str, str] = {
    "transcriber": "auto",          # auto(字幕→必剪→whisper) | subtitle | bcut | whisper
    "whisper_model": "base",
    "whisper_parallel": "6",
    "whisper_cpu_threads": "8",
    "bcut_enabled": "1",
    "video_concurrency": "5",
    "screenshot_enabled": "1",      # 图文：按时间点抽帧插图
    "screenshot_min_gap": "180",    # 相邻截图最小间隔（秒）
    "screenshot_max": "20",
    "frames_ocr": "0",             # 网格 OCR 图文（Markdown 截图已覆盖，默认关，省 90s)
    "note_markdown": "1",           # 生成单篇 Markdown 笔记
    "note_templates": "1",          # 同时保留摘要/大纲/问答三模板
    "download_format_height": "480",
    "proxy_url": "",
}


def _fernet() -> Fernet:
    raw = (settings.SESSION_SECRET or "gflc").encode()
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw).digest()))


def encrypt(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError):
        # SESSION_SECRET 变了或历史明文：当作空，避免整站不可用
        _log.warning("密钥解密失败（SESSION_SECRET 可能已更换），请到设置页重新填写")
        return ""


def mask(plain: str) -> str:
    if not plain:
        return ""
    if len(plain) <= 8:
        return "*" * len(plain)
    return f"{plain[:4]}{'*' * 8}{plain[-4:]}"


# --------------------------- 运行时配置 ---------------------------
def get_runtime(db: Session, key: str, default: str | None = None) -> str:
    row = db.get(AppSetting, key)
    if row is not None and row.value != "":
        return row.value
    if default is not None:
        return default
    return RUNTIME_DEFAULTS.get(key, "")


def set_runtime(db: Session, key: str, value: str) -> None:
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=str(value)))
    else:
        row.value = str(value)
    db.commit()


def all_runtime(db: Session) -> dict[str, str]:
    out = dict(RUNTIME_DEFAULTS)
    for row in db.scalars(select(AppSetting)).all():
        if row.value != "":
            out[row.key] = row.value
    return out


# --------------------------- Cookie ---------------------------
def set_cookie(db: Session, platform: str, cookie: str, note: str = "") -> None:
    row = db.get(PlatformCookie, platform)
    enc = encrypt(cookie)
    if row is None:
        db.add(PlatformCookie(platform=platform, cookie_enc=enc, note=note))
    else:
        row.cookie_enc = enc
        if note:
            row.note = note
    db.commit()


def get_cookie(db: Session, platform: str) -> str:
    row = db.get(PlatformCookie, platform)
    return decrypt(row.cookie_enc) if row else ""


# --------------------------- 供应商 / 模型 ---------------------------
def default_provider(db: Session) -> AiProvider | None:
    return db.scalars(select(AiProvider).where(AiProvider.enabled == 1)
                      .order_by(AiProvider.is_default.desc(), AiProvider.sort, AiProvider.id)).first()


def resolve_model(db: Session | None, purpose: str) -> tuple[str, str, str] | None:
    """返回 (base_url, api_key, model_id)；DB 无配置返回 None（调用方回落 env）。"""
    if db is None:
        return None
    try:
        rows = db.execute(
            select(AiModel, AiProvider).join(AiProvider, AiModel.provider_id == AiProvider.id)
            .where(AiModel.purpose == purpose, AiModel.enabled == 1, AiProvider.enabled == 1)
            .order_by(AiModel.is_default.desc(), AiModel.id)
        ).all()
    except Exception as e:  # noqa: BLE001  配置表缺失时不能让主流程挂
        _log.warning("模型解析失败（按 env 兜底）：%s", e)
        return None
    for model, prov in rows:
        key = decrypt(prov.api_key_enc)
        if key:
            return (prov.base_url or "", key, model.model_id)
    return None


def seed_defaults(db: Session) -> None:
    """首次启动写入默认供应商与模型（密钥取自 .env，之后可在设置页改）。"""
    try:
        if db.scalars(select(AiProvider)).first() is not None:
            return
        provs = []
        if settings.ARK_API_KEY:
            provs.append(AiProvider(name="火山方舟", kind="ark", base_url=settings.ARK_API_BASE,
                                    api_key_enc=encrypt(settings.ARK_API_KEY), is_default=1, sort=0))
        if settings.LLM_API_KEY:
            provs.append(AiProvider(name="DeepSeek 官方", kind="deepseek", base_url=settings.LLM_API_BASE,
                                    api_key_enc=encrypt(settings.LLM_API_KEY), is_default=0, sort=1))
        for p in provs:
            db.add(p)
        db.flush()
        ark = next((p for p in provs if p.kind == "ark"), None)
        ds = next((p for p in provs if p.kind == "deepseek"), None)
        if ark:
            db.add(AiModel(provider_id=ark.id, model_id=settings.ARK_NOTE_MODEL,
                           label="笔记生成（方舟）", purpose="note", is_default=1))
            db.add(AiModel(provider_id=ark.id, model_id=settings.ARK_VISION_MODEL,
                           label="视觉识图（方舟）", purpose="vision", is_default=1))
            db.add(AiModel(provider_id=ark.id, model_id=settings.ARK_LONG_MODEL,
                           label="长文理解（方舟）", purpose="long"))
        if ds:
            db.add(AiModel(provider_id=ds.id, model_id=settings.LLM_MID_MODEL,
                           label="备用（DeepSeek 官方）", purpose="note", is_default=0))
        db.commit()
        _log.info("配置中心已写入默认供应商 %s 个", len(provs))
    except Exception as e:  # noqa: BLE001
        db.rollback()
        _log.warning("默认供应商写入失败（不影响启动）：%s", e)


def materialize_cookie(db: Session, platform: str) -> str:
    """把库里的 Cookie 落成 Netscape cookies.txt，返回路径（供 yt-dlp 用）。

    yt-dlp 只认文件，不认内存字符串；缓存到 data/cookies/<platform>.txt，
    内容变化才重写（比较密文摘要）。
    """
    import os
    row = db.get(PlatformCookie, platform)
    if row is None or not row.cookie_enc:
        return ""
    plain = decrypt(row.cookie_enc)
    if not plain:
        return ""
    digest = hashlib.sha256(row.cookie_enc.encode()).hexdigest()[:12]
    base = os.path.abspath(os.path.join(settings.LOCAL_STORAGE_DIR, "..", "cookies"))
    try:
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"{platform}.txt")
        stamp = path + ".hash"
        if os.path.exists(path) and os.path.exists(stamp):
            with open(stamp, "r", encoding="utf-8") as f:
                if f.read().strip() == digest:
                    return path
        # 用户可能粘整段 "SESSDATA=xxx; bili_jct=yyy"，转成 Netscape 行
        lines = ["# Netscape HTTP Cookie File", f"# generated by gflc ({platform})"]
        domain = ".bilibili.com" if platform == "bilibili" else (
            ".youtube.com" if platform == "youtube" else ".douyin.com")
        for part in plain.replace("\n", ";").split(";"):
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            k, v = k.strip(), v.strip()
            if not k:
                continue
            lines.append(f"{domain}\tTRUE\t/\tFALSE\t0\t{k}\t{v}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        with open(stamp, "w", encoding="utf-8") as f:
            f.write(digest)
        return path
    except OSError as e:
        _log.warning("Cookie 落盘失败：%s", e)
        return ""


# --------------------------- 运行时缓存（DB → 内存） ---------------------------
# 每次改配置都刷一次；读路径（LLM 调用）只查内存，不碰 DB，避免每次生成都开 session。
_CACHE: dict[str, tuple[str, str, str]] = {}


def refresh_cache(db: Session) -> dict[str, str]:
    """把各用途的默认模型解析进内存：{purpose: model_id}。返回概览用于日志。"""
    global _CACHE
    out: dict[str, str] = {}
    try:
        rows = db.execute(
            select(AiModel, AiProvider).join(AiProvider, AiModel.provider_id == AiProvider.id)
            .where(AiModel.enabled == 1, AiProvider.enabled == 1)
            .order_by(AiModel.is_default.desc(), AiModel.id)
        ).all()
    except Exception as e:  # noqa: BLE001
        _log.warning("配置缓存刷新失败：%s", e)
        return out
    cache: dict[str, tuple[str, str, str]] = {}
    for model, prov in rows:
        if model.purpose in cache:
            continue  # 只取每个用途的第一条（is_default 优先）
        key = decrypt(prov.api_key_enc)
        if not key:
            continue
        cache[model.purpose] = (prov.base_url or "", key, model.model_id)
        out[model.purpose] = model.model_id
    _CACHE = cache
    return out


def cached(purpose: str) -> tuple[str, str, str] | None:
    return _CACHE.get(purpose)
