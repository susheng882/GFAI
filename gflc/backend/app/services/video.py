# -*- coding: utf-8 -*-
"""视频链路：ffmpeg 抽音频 → faster-whisper 转写 → 按时间戳切块。
模型首次会下载（tiny ~75MB），之后缓存。"""
import os
import re
import subprocess

from app.core.errors import APIError, ErrCode

_MODEL = None


def _model():
    global _MODEL
    if _MODEL is None:
        # 默认走国内镜像，避免 huggingface 直连失败
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        try:
            from faster_whisper import WhisperModel
            from app.core.config import settings
            _MODEL = WhisperModel(settings.WHISPER_MODEL, device="cpu", compute_type="int8")
        except Exception as e:
            raise APIError(ErrCode.PARSE_001, f"转写模型不可用：{e}") from e
    return _MODEL


def extract_audio(src: str, dst: str) -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", dst],
            check=True, capture_output=True, timeout=1800,
        )
    except FileNotFoundError as e:
        raise APIError(ErrCode.PARSE_001, "未安装 ffmpeg，无法抽取音频") from e
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or b"")[-300:].decode("utf-8", "ignore")
        raise APIError(ErrCode.PARSE_001, f"音频抽取失败：{msg}") from e


_CC = None


def _to_simplified(text: str) -> str:
    """whisper 中文常输出繁体（尤其港台训练语料），统一转简体。"""
    global _CC
    if not text:
        return text
    if _CC is None:
        try:
            from opencc import OpenCC
            _CC = OpenCC("t2s")
        except Exception:
            _CC = False
    if _CC is False:
        return text
    try:
        return _CC.convert(text)
    except Exception:
        return text


def transcribe(audio_path: str, on_progress=None) -> list[tuple[float, float, str]]:
    segs, info = _model().transcribe(
        audio_path, vad_filter=True,
        initial_prompt="以下是普通话的句子，请使用简体中文。",  # 引导简体输出
    )
    dur = float(getattr(info, "duration", 0) or 0)
    out = []
    for s in segs:
        t = _to_simplified((s.text or "").strip())
        if t:
            out.append((float(s.start), float(s.end), t))
        if on_progress and dur > 0:
            on_progress(min(85, int(20 + 65 * (float(s.end) / dur))))
    if not out:
        raise APIError(ErrCode.PARSE_002, "未识别到语音内容")
    return out


def quality(text: str) -> str:
    """粗判转写质量：过短 / 字符过于集中 / 大量重复 → low。"""
    t = text or ""
    if len(t) < 15:
        return "low"
    uniq = len(set(t))
    if uniq / max(len(t), 1) < 0.08:
        return "low"
    if re.search(r"(.{1,4})\1{3,}", t):
        return "low"
    return "ok"


def segments_to_chunks(segs: list[tuple[float, float, str]], size: int = 300) -> list[dict]:
    """把 ASR 片段合并成 ~size 字的块，保留时间戳溯源。"""
    chunks, cur, cur_len, start = [], [], 0, None
    for st, en, text in segs:
        if start is None:
            start = st
        if cur and cur_len + len(text) > size:
            chunks.append({"content": "".join(cur), "ts_start": start, "ts_end": prev_end})
            cur, cur_len, start = [text], len(text), st
        else:
            cur.append(text)
            cur_len += len(text)
        prev_end = en
    if cur:
        chunks.append({"content": "".join(cur), "ts_start": start, "ts_end": prev_end})
    return chunks


_PLATFORM_HINTS = {
    "youtube": "YouTube 在当前网络不可达，请配置代理，或改用 B站 / 本地上传。",
    "douyin": "抖音请使用分享短链（v.douyin.com/…），可能触发风控；失败请改用本地上传。",
    "kuaishou": "快手在当前网络不可达，请改用本地上传。",
    "other": "暂不支持该站点，请改用 B站 链接或本地上传。",
}


def detect_platform(url: str) -> str:
    u = (url or "").lower()
    if "bilibili.com" in u or "b23.tv" in u:
        return "bilibili"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "douyin.com" in u:
        return "douyin"
    if "kuaishou.com" in u:
        return "kuaishou"
    return "other"


def download_media(url: str, outdir: str) -> str:
    """通用下载（yt-dlp 支持 B站/YouTube/抖音/快手等）。失败按平台给明确原因。"""
    try:
        import yt_dlp
    except ImportError as e:
        raise APIError(ErrCode.PARSE_001, "未安装 yt-dlp") from e
    platform = detect_platform(url)
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(outdir, "audio.%(ext)s"),
        "quiet": True, "noplaylist": True, "no_warnings": True,
        "socket_timeout": 20, "retries": 2,
    }
    from app.core.config import settings
    if settings.COOKIES_FILE and os.path.exists(settings.COOKIES_FILE):
        opts["cookiefile"] = settings.COOKIES_FILE
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)
    except Exception as e:
        hint = _PLATFORM_HINTS.get(platform, _PLATFORM_HINTS["other"])
        raise APIError(ErrCode.PARSE_003, f"链接解析失败：{str(e)[:140]}。{hint}") from e


# 兼容旧名
def download_bilibili(url: str, outdir: str) -> str:
    return download_media(url, outdir)
