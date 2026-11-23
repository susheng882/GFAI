# -*- coding: utf-8 -*-
"""视频取材链路：字幕优先 → ffmpeg 抽音频 → faster-whisper 转写 → 按时间戳切块。

差异收敛：
- S2/A1：先探测 sidecar(.srt/.vtt/.ass) 与视频内嵌字幕流，命中直接用字幕文本+时间轴，
  跳过 Whisper（日志 subtitle_hit，返回 whisper_calls=0）；无字幕保持原 ASR 路径。
- D9/A2：WHISPER_MODEL 可覆盖（默认沿用 settings 的 base，避免回归波动）；
  学科术语词典纠错；quality=low 时不写 ready（由 handlers 落 needs_review 标记）。
模型首次会下载（tiny ~75MB），之后缓存。"""
import json
import logging
import os
import re
import subprocess
import tempfile

from app.core.errors import APIError, ErrCode

_log = logging.getLogger(__name__)

_MODEL = None

# A2：学科术语纠错词典（whisper 中文常见同音/近形误识）。
# 命中的词直接替换；额外词典可用 VIDEO_TERMS_JSON（JSON 字符串或文件路径）覆盖/追加。
_TERM_CORRECTIONS: dict[str, str] = {
    "建格重复": "间隔重复",
    "建隔重复": "间隔重复",
    "间格重复": "间隔重复",
    "间膈重复": "间隔重复",
    "线代数": "线性代数",
    "线性带数": "线性代数",
    "概率论与数里统计": "概率论与数理统计",
    "微击分": "微积分",
    "矩陈": "矩阵",
    "特征直": "特征值",
}


def _extra_terms() -> dict[str, str]:
    """读取 VIDEO_TERMS_JSON（可选）：JSON 字符串或指向 JSON 文件的路径。失败 WARNING 不静默。"""
    raw = (os.getenv("VIDEO_TERMS_JSON") or "").strip()
    if not raw:
        return {}
    try:
        data = raw
        if os.path.isfile(raw):
            with open(raw, "r", encoding="utf-8") as f:
                data = f.read()
        obj = json.loads(data)
        if isinstance(obj, dict):
            return {str(k): str(v) for k, v in obj.items() if k and v}
    except Exception as e:
        _log.warning("学科术语词典 VIDEO_TERMS_JSON 解析失败，忽略额外词条：%s", e)
    return {}


def correct_terms(text: str) -> str:
    """A2：应用学科术语纠错（内置 + 可选外部词典）。纯函数，便于单测。"""
    if not text:
        return text
    out = text
    merged = dict(_TERM_CORRECTIONS)
    merged.update(_extra_terms())
    for wrong, right in merged.items():
        if wrong != right and wrong in out:
            out = out.replace(wrong, right)
    return out


def _whisper_model_name() -> str:
    """A2：默认维持当前模型（settings.WHISPER_MODEL，通常 base）；WHISPER_MODEL 可覆盖，small 可用。"""
    from app.core.config import settings
    return (os.getenv("WHISPER_MODEL") or getattr(settings, "WHISPER_MODEL", "base") or "base").strip()


def _model():
    global _MODEL
    if _MODEL is None:
        # 默认走国内镜像，避免 huggingface 直连失败
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
        try:
            from faster_whisper import WhisperModel
            from app.core.config import settings
            # 每片都要吃线程；给足 8 线程，然后靠片数并行把 CPU 吃满（20 核机器实测 6 片最优）
            threads = int(getattr(settings, "WHISPER_CPU_THREADS", 8) or 8)
            _MODEL = WhisperModel(_whisper_model_name(), device="cpu", compute_type="int8",
                                  cpu_threads=max(1, threads))
        except Exception as e:
            raise APIError(ErrCode.PARSE_001, f"转写模型不可用：{e}") from e
    return _MODEL


def extract_audio(src: str, dst: str) -> None:
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", "-f", "wav", dst],
            check=True, capture_output=True, timeout=600,
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


def _wav_duration(path: str) -> float:
    try:
        import wave
        with wave.open(path) as w:
            return float(w.getnframes()) / float(w.getframerate() or 1)
    except Exception:  # noqa: BLE001
        return 0.0


def _transcribe_slice(args) -> list[tuple[float, float, str]]:
    """转写单个切片（线程池任务）。offset 用于把片内时间还原成全片时间轴。"""
    path, offset, gain_span = args
    model = _model()
    segs, _ = model.transcribe(
        path, vad_filter=True, beam_size=1, condition_on_previous_text=False,
        initial_prompt="以下是普通话的句子，请使用简体中文。",
    )
    out = []
    for s in segs:
        t = correct_terms(_to_simplified((s.text or "").strip()))
        if t:
            st, en = float(s.start) + offset, float(s.end) + offset
            if gain_span and st >= gain_span:  # 切片重叠区，交给下一片，避免重复
                continue
            out.append((st, en, t))
    return out


def transcribe(audio_path: str, on_progress=None) -> list[tuple[float, float, str]]:
    """语音转写。长音频按片并行（Whisper 是 CPU 密集，串行跑满一核就停）。

    实测 4.5 分钟音频：单路 RTF 0.44（60 分钟视频≈26 分钟），6 片并行 RTF 0.11（≈6.6 分钟）。
    短音频（<120s）仍走单路，避免切分开销拖慢小文件。
    """
    from app.core.config import settings

    dur = _wav_duration(audio_path)
    parallel = max(1, int(getattr(settings, "WHISPER_PARALLEL", 1) or 1))
    if dur < 120 or parallel <= 1:
        segs, info = _model().transcribe(
            audio_path, vad_filter=True, beam_size=int(getattr(settings, "WHISPER_BEAM", 5) or 5),
            condition_on_previous_text=False,
            initial_prompt="以下是普通话的句子，请使用简体中文。",  # 引导简体输出
        )
        total = float(getattr(info, "duration", 0) or 0)
        out = []
        for s in segs:
            t = correct_terms(_to_simplified((s.text or "").strip()))
            if t:
                out.append((float(s.start), float(s.end), t))
            if on_progress and total > 0:
                on_progress(min(85, int(20 + 65 * (float(s.end) / total))))
        if not out:
            raise APIError(ErrCode.PARSE_002, "未识别到语音内容")
        return out

    workdir = tempfile.mkdtemp(prefix="gflc_asr_")
    span = dur / parallel
    overlap = 1.0  # 片间留 1s 重叠，边界词不被切断
    jobs, paths = [], []
    try:
        for i in range(parallel):
            start = max(0.0, i * span)
            length = min(dur - start, span + overlap)
            part = os.path.join(workdir, f"p{i}.wav")
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}",
                 "-t", f"{length:.3f}", "-i", audio_path, "-ac", "1", "-ar", "16000", "-f", "wav", part],
                check=True, capture_output=True, timeout=300,
            )
            paths.append(part)
            # gain_span：本片只收到 (start+span) 之前，重叠部分不重复计入
            jobs.append((part, start, (i + 1) * span if i < parallel - 1 else None))

        from concurrent.futures import ThreadPoolExecutor, as_completed
        results: list[list[tuple[float, float, str]]] = []
        done = 0
        with ThreadPoolExecutor(max_workers=parallel) as ex:
            futures = [ex.submit(_transcribe_slice, j) for j in jobs]
            for fu in as_completed(futures):
                try:
                    results.append(fu.result())
                except Exception as e:  # noqa: BLE001  单片刻失败不拖垮整体
                    _log.warning("转写切片失败，已跳过该片：%s", e)
                    results.append([])
                done += 1
                if on_progress:
                    on_progress(min(85, int(20 + 65 * done / parallel)))

        merged = sorted((s for part in results for s in part), key=lambda x: x[0])
        # 边界去重：相邻片段文本完全相同且时间重叠时只留一条
        out: list[tuple[float, float, str]] = []
        for item in merged:
            if out and item[2] == out[-1][2] and item[0] - out[-1][0] < 2.0:
                continue
            out.append(item)
        if not out:
            raise APIError(ErrCode.PARSE_002, "未识别到语音内容")
        _log.info("transcribe_parallel slices=%s dur=%.1fs segments=%s", parallel, dur, len(out))
        return out
    finally:
        for p in paths:
            try:
                os.remove(p)
            except OSError:
                pass
        try:
            os.rmdir(workdir)
        except OSError:
            pass


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
    """把 ASR/字幕片段合并成 ~size 字的块，保留统一时间轴锚点 ts_start/ts_end（D8）。"""
    chunks, cur, cur_len, start = [], [], 0, None
    prev_end = 0.0
    for st, en, text in segs:
        if start is None:
            start = st
        if cur and cur_len + len(text) > size:
            chunks.append({"content": "".join(cur), "ts_start": round(float(start), 2),
                           "ts_end": round(float(prev_end), 2)})
            cur, cur_len, start = [text], len(text), st
        else:
            cur.append(text)
            cur_len += len(text)
        prev_end = en
    if cur:
        chunks.append({"content": "".join(cur), "ts_start": round(float(start), 2),
                       "ts_end": round(float(prev_end), 2)})
    return chunks


# ---------------------------------------------------------------------------
# S2 / A1：字幕优先取材
# ---------------------------------------------------------------------------
_SUB_EXT = (".srt", ".vtt", ".ass")

_TS_HMS = re.compile(r"(\d{1,3}):(\d{2}):(\d{2})[,.](\d{1,3})")
_TS_MS = re.compile(r"(\d{1,2}):(\d{2})[,.](\d{1,3})")


def parse_ts(raw: str) -> float | None:
    """SRT/VTT/ASS 时间戳 → 秒。支持 HH:MM:SS,mmm / HH:MM:SS.mmm / MM:SS.mmm。"""
    if not raw:
        return None
    m = _TS_HMS.search(raw)
    if m:
        h, mm, ss, frac = m.groups()
        return int(h) * 3600 + int(mm) * 60 + int(ss) + int(frac) / (10 ** len(frac))
    m = _TS_MS.search(raw)
    if m:
        mm, ss, frac = m.groups()
        return int(mm) * 60 + int(ss) + int(frac) / (10 ** len(frac))
    return None


def _clean_cue(text: str) -> str:
    """清理字幕正文：合并行、去 ASS 特效标记、去 VTT 标签。"""
    if not text:
        return ""
    t = re.sub(r"\{\\[^}]*\}", "", text)          # ASS 覆盖标签 {\...}
    t = re.sub(r"<[^>]+>", "", t)                  # VTT/HTML 标签
    t = t.replace("\\N", " ").replace("\\n", " ").replace("\\h", " ")
    return re.sub(r"\s+", " ", t).strip()


def parse_srt(text: str) -> list[tuple[float, float, str]]:
    """解析 SRT：序号行 + `HH:MM:SS,mmm --> HH:MM:SS,mmm` + 正文。"""
    out: list[tuple[float, float, str]] = []
    for block in re.split(r"\r?\n\s*\r?\n", (text or "").replace("\ufeff", "")):
        lines = [ln for ln in block.strip().splitlines() if ln.strip()]
        if len(lines) < 2:
            continue
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue
        parts = [p.strip() for p in lines[idx].split("-->")]
        if len(parts) < 2:
            continue
        st, en = parse_ts(parts[0]), parse_ts(parts[1])
        if st is None or en is None:
            continue
        body = _clean_cue(" ".join(lines[idx + 1:]))
        if body:
            out.append((st, en, body))
    return out


def parse_vtt(text: str) -> list[tuple[float, float, str]]:
    """解析 WebVTT：跳过 WEBVTT/NOTE/样式头，时间行可带 cue settings。"""
    raw = (text or "").replace("\ufeff", "")
    out: list[tuple[float, float, str]] = []
    for block in re.split(r"\r?\n\s*\r?\n", raw):
        lines = [ln for ln in block.strip().splitlines() if ln.strip()]
        if not lines:
            continue
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue  # WEBVTT 头、STYLE、NOTE 等
        parts = [p.strip() for p in lines[idx].split("-->")]
        if len(parts) < 2:
            continue
        st, en = parse_ts(parts[0]), parse_ts(parts[1].split()[0] if parts[1] else "")
        if st is None or en is None:
            continue
        body = _clean_cue(" ".join(lines[idx + 1:]))
        if body and not body.upper().startswith("NOTE"):
            out.append((st, en, body))
    return out


def parse_ass(text: str) -> list[tuple[float, float, str]]:
    """解析 ASS/SSA：只取 [Events] 的 Dialogue 行，第 10 段起为正文。"""
    out: list[tuple[float, float, str]] = []
    raw = (text or "").replace("\ufeff", "")
    for ln in raw.splitlines():
        if not ln.lower().startswith("dialogue:"):
            continue
        fields = ln[len("dialogue:"):].split(",", 9)
        if len(fields) < 10:
            continue
        st, en = parse_ts(fields[1].strip()), parse_ts(fields[2].strip())
        if st is None or en is None:
            continue
        body = _clean_cue(fields[9])
        if body:
            out.append((st, en, body))
    return out


_PARSERS = {".srt": parse_srt, ".vtt": parse_vtt, ".ass": parse_ass}


def parse_subtitle(text: str, fmt: str) -> list[tuple[float, float, str]]:
    """按后缀分派解析器；解析异常不静默，WARNING 后返回空。"""
    try:
        return _PARSERS.get((fmt or "").lower(), parse_srt)(text)
    except Exception as e:
        _log.warning("字幕解析失败（格式=%s）：%s", fmt, e)
        return []


def _same_stem_candidates(path: str) -> list[str]:
    stem, _ = os.path.splitext(path)
    return [stem + ext for ext in _SUB_EXT] + [stem + ext.upper() for ext in _SUB_EXT]


def find_sidecar_subtitle(video_path: str, storage_key: str | None = None) -> tuple[str | None, str, bool]:
    """探测外挂字幕：先本地同目录同 stem，再 storage_key 同目录（若提供）。

    返回 (字幕路径, 格式后缀, 是否临时文件)。失败不抛异常，返回 (None, "", False)。
    """
    if video_path:
        for cand in _same_stem_candidates(video_path):
            if os.path.isfile(cand) and os.path.abspath(cand) != os.path.abspath(video_path):
                return cand, os.path.splitext(cand)[1].lower(), False
    if storage_key:
        try:
            from app.services.storage import get_storage
            root, _ = os.path.split(storage_key)
            stem, _ = os.path.splitext(storage_key)
            for ext in _SUB_EXT:
                key = (root + "/" if root else "") + os.path.basename(stem) + ext
                try:
                    data = get_storage().read(key)
                except Exception:
                    continue
                fd, tmp = tempfile.mkstemp(prefix="gflc_sub_", suffix=ext)
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                return tmp, ext, True
        except Exception as e:
            _log.warning("外挂字幕探测（storage_key=%s）失败：%s", storage_key, e)
    return None, "", False


def probe_embedded_subtitle(video_path: str) -> bool:
    """ffprobe 探测视频内嵌字幕流（-select_streams s）。"""
    if not video_path or not os.path.isfile(video_path):
        return False
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "s",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path],
            capture_output=True, timeout=60,
        )
        return b"subtitle" in (out.stdout or b"").lower()
    except Exception as e:
        _log.warning("内嵌字幕探测失败：%s", e)
        return False


def extract_embedded_subtitle(video_path: str, outdir: str) -> str | None:
    """把第一条内嵌字幕流转成 SRT。失败 WARNING 并返回 None（交给 ASR 兜底）。"""
    try:
        os.makedirs(outdir, exist_ok=True)
        dst = os.path.join(outdir, "embedded_subtitle.srt")
        res = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-v", "error", "-i", video_path,
             "-map", "0:s:0", "-c:s", "srt", "-f", "srt", dst],
            capture_output=True, timeout=300,
        )
        if res.returncode == 0 and os.path.isfile(dst) and os.path.getsize(dst) > 0:
            return dst
        msg = (res.stderr or b"")[-200:].decode("utf-8", "ignore")
        _log.warning("内嵌字幕提取失败，转用 ASR：%s", msg or f"returncode={res.returncode}")
    except Exception as e:
        _log.warning("内嵌字幕提取异常，转用 ASR：%s", e)
    return None


def load_subtitle_segments(video_path: str, storage_key: str | None = None,
                           workdir: str | None = None,
                           log_ctx: str = "") -> tuple[list[tuple[float, float, str]] | None, dict]:
    """S2/A1 总入口：外挂 → 内嵌。命中返回 (segments, meta)，否则 (None, meta)。

    meta 含 source / whisper_calls=0 / temp_files，调用方据此跳过 Whisper。
    """
    meta = {"source": "", "whisper_calls": 0, "temp_files": []}
    path, fmt, is_tmp = find_sidecar_subtitle(video_path, storage_key)
    if path:
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
                text = f.read()
            segs = parse_subtitle(text, fmt)
            if segs:
                meta.update({"source": f"sidecar:{fmt}", "path": path})
                if is_tmp:
                    meta["temp_files"].append(path)
                _log.info("subtitle_hit source=%s segments=%s %s", meta["source"], len(segs), log_ctx)
                return segs, meta
            _log.warning("外挂字幕解析为空（%s），尝试内嵌字幕 %s", path, log_ctx)
        except Exception as e:
            _log.warning("外挂字幕读取失败（%s）：%s", path, e)
        if is_tmp:
            try:
                os.remove(path)
            except OSError:
                pass

    if probe_embedded_subtitle(video_path):
        srt = extract_embedded_subtitle(video_path, workdir or tempfile.gettempdir())
        if srt:
            try:
                with open(srt, "r", encoding="utf-8-sig", errors="replace") as f:
                    segs = parse_subtitle(f.read(), ".srt")
                if segs:
                    meta.update({"source": "embedded:srt", "path": srt})
                    meta["temp_files"].append(srt)
                    _log.info("subtitle_hit source=%s segments=%s %s", meta["source"], len(segs), log_ctx)
                    return segs, meta
                _log.warning("内嵌字幕转写结果为空，转用 ASR %s", log_ctx)
            except Exception as e:
                _log.warning("内嵌字幕读取失败：%s %s", e, log_ctx)
    return None, meta


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


def download_media(url: str, outdir: str, want_video: bool = True) -> str:
    """通用下载（yt-dlp 支持 B站/YouTube/抖音/快手等）。失败按平台给明确原因。

    want_video=True 时优先拿「视频+音频」并合并成 mp4：图文笔记要抽关键帧，
    只下 bestaudio 会让 `_is_video_src()` 判成音频、图文笔记静默跳过（线上踩过）。
    """
    try:
        import yt_dlp
    except ImportError as e:
        raise APIError(ErrCode.PARSE_001, "未安装 yt-dlp") from e
    platform = detect_platform(url)
    opts = {
        "outtmpl": os.path.join(outdir, "media.%(ext)s"),
        "quiet": True, "noplaylist": True, "no_warnings": True,
        "socket_timeout": 20, "retries": 2,
    }
    if want_video:
        # 480p 上限：够 OCR 看清板书，体积/解码时间是 1080p 的 1/4 左右
        opts.update({
            "format": "bv*[height<=480]+ba/b[height<=480]/b/bestaudio",
            "merge_output_format": "mp4",
        })
    else:
        opts.update({"format": "bestaudio/best"})
    from app.core.config import settings
    if settings.COOKIES_FILE and os.path.exists(settings.COOKIES_FILE):
        opts["cookiefile"] = settings.COOKIES_FILE
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
    except Exception as e:
        hint = _PLATFORM_HINTS.get(platform, _PLATFORM_HINTS["other"])
        raise APIError(ErrCode.PARSE_003, f"链接解析失败：{str(e)[:140]}。{hint}") from e
    # 合并输出（bv+ba → mp4）时 prepare_filename 可能指向合并前的容器名，回退按目录找真实文件
    if path and os.path.isfile(path):
        return path
    for name in sorted(os.listdir(outdir)):
        if name.startswith("media."):
            cand = os.path.join(outdir, name)
            if os.path.isfile(cand) and os.path.getsize(cand) > 0:
                return cand
    raise APIError(ErrCode.PARSE_003, "下载完成但未找到媒体文件，请重试")


# 兼容旧名
def download_bilibili(url: str, outdir: str) -> str:
    return download_media(url, outdir)
