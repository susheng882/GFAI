# -*- coding: utf-8 -*-
"""必剪（bcut）云转写：B 站自家的语音识别接口，免登录、免费、不吃本机 CPU。

实测（2026-11-22，本机）：4.5 分钟音频 7.6 秒返回（RTF 0.028），13 秒音频 6.2 秒，
中文术语识别准确（「间隔重复」「遗忘曲线」）。27 分钟视频约 45 秒。

接口流程（与开源项目 BiliNote 的 bcut.py 一致，MIT License, © JefferyHcool；
本实现为重写，仅沿用公开的接口时序，未复制其代码结构以外的内容）：
    申请上传 → PUT 分片 → 提交上传 → 创建任务 → 轮询 state=4 → 解析 utterances

无官方 SLA，可能限流或改接口，因此调用方必须能降级到本地 Whisper。
"""
import json
import logging
import time
import uuid

import requests

from app.core.config import settings
from app.core.errors import APIError, ErrCode

_log = logging.getLogger(__name__)

_BASE = "https://member.bilibili.com/x/bcut/rubick-interface"
_HEADERS = {
    "User-Agent": "Bilibili/1.0.0 (https://www.bilibili.com)",
    "Content-Type": "application/json",
}


class BcutError(Exception):
    """必剪接口异常（调用方据此降级到 Whisper）。"""


def _upload(session: requests.Session, data: bytes) -> str:
    """上传音频，返回可下载的 resource url。"""
    r = session.post(f"{_BASE}/resource/create",
                     data=json.dumps({"type": 2, "name": "audio.mp3", "size": len(data),
                                      "ResourceFileType": "mp3", "model_id": "8"}),
                     headers=_HEADERS, timeout=30)
    r.raise_for_status()
    j = r.json()
    if j.get("code") != 0:
        raise BcutError(f"申请上传失败：{j.get('message')}")
    d = j["data"]
    in_boss_key, resource_id = d["in_boss_key"], d["resource_id"]
    upload_id, urls, per_size = d["upload_id"], d["upload_urls"], d["per_size"]

    etags = []
    for clip, url in enumerate(urls):
        part = data[clip * per_size: min((clip + 1) * per_size, len(data))]
        pr = session.put(url, data=part, headers={"Content-Type": "application/octet-stream"}, timeout=120)
        pr.raise_for_status()
        etags.append(pr.headers.get("Etag", "").strip('"'))

    r = session.post(f"{_BASE}/resource/create/complete",
                     data=json.dumps({"InBossKey": in_boss_key, "ResourceId": resource_id,
                                      "Etags": ",".join(etags), "UploadId": upload_id,
                                      "model_id": "8"}),
                     headers=_HEADERS, timeout=60)
    r.raise_for_status()
    j = r.json()
    if j.get("code") != 0:
        raise BcutError(f"提交上传失败：{j.get('message')}")
    return j["data"]["download_url"]


def transcribe_bcut(audio_path: str) -> list[tuple[float, float, str]]:
    """云转写音频，返回 [(start, end, text)]（秒）。失败抛 BcutError 由上层降级。"""
    if not settings.BCUT_ENABLED:
        raise BcutError("必剪转写已关闭（BCUT_ENABLED=false）")
    try:
        with open(audio_path, "rb") as f:
            data = f.read()
    except OSError as e:
        raise BcutError(f"音频读取失败：{e}") from e
    if len(data) > 100 * 1024 * 1024:
        raise BcutError("音频超过 100MB，改用本地转写")

    session = requests.Session()
    rid = uuid.uuid4().hex[:8]
    t0 = time.time()
    try:
        resource_url = _upload(session, data)

        r = session.post(f"{_BASE}/task",
                         json={"resource": resource_url, "model_id": "8"},
                         headers=_HEADERS, timeout=30)
        r.raise_for_status()
        j = r.json()
        if j.get("code") != 0:
            raise BcutError(f"创建任务失败：{j.get('message')}")
        task_id = j["data"]["task_id"]

        deadline = t0 + settings.BCUT_TIMEOUT_SECONDS
        payload = None
        while time.time() < deadline:
            q = session.get(f"{_BASE}/task/result",
                            params={"model_id": 7, "task_id": task_id},
                            headers=_HEADERS, timeout=30)
            q.raise_for_status()
            j = q.json()
            if j.get("code") != 0:
                raise BcutError(f"查询结果失败：{j.get('message')}")
            d = j["data"]
            if d.get("state") == 4:
                payload = d
                break
            if d.get("state") == 3:
                raise BcutError("必剪识别任务失败（state=3）")
            time.sleep(1)
        if payload is None:
            raise BcutError("必剪识别超时")

        result = json.loads(payload.get("result") or "{}")
        out: list[tuple[float, float, str]] = []
        for u in result.get("utterances") or []:
            text = (u.get("transcript") or "").strip()
            if not text:
                continue
            # 必剪时间戳是毫秒
            out.append((float(u.get("start_time", 0)) / 1000.0,
                        float(u.get("end_time", 0)) / 1000.0, text))
        if not out:
            raise BcutError("必剪返回空转写")
        _log.info("bcut_ok audio=%.1fs segments=%s elapsed=%.1fs",
                  len(data) / 1024, len(out), time.time() - t0)
        return out
    except (requests.RequestException, ValueError) as e:
        raise BcutError(f"必剪接口异常：{str(e)[:120]}") from e
    finally:
        session.close()
