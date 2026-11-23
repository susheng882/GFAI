# -*- coding: utf-8 -*-
"""关键帧图文笔记：按场景变化抽帧 → 感知哈希去重 → 文档帧识别 → 多模态转写 → 图文笔记。

视频里博主用 PPT / 讲义 / 板书讲解时，只看语音转写会丢掉图里的公式、表格与结构，
本模块把「图里的信息」也提取出来，与语音笔记互补。
"""
import asyncio
import base64
import logging
import os
import re
import subprocess
import uuid

from pydantic import BaseModel

from app.ai.deepseek import chat
from app.ai.prompts import (FRAME_NOTE_SYSTEM, FRAME_OCR_SYSTEM, frame_note_user,
                            frame_ocr_user)
from app.ai.router import generate_json
from app.core.config import settings

_log = logging.getLogger(__name__)

_TS_RE = re.compile(r"pts_time:\s*([0-9]+(?:\.[0-9]+)?)")
_VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".m4v", ".avi", ".flv", ".wmv", ".ts"}

try:  # PIL 是可选增强，没装则跳过去重与文档帧判断
    from PIL import Image, ImageFilter
except Exception:  # pragma: no cover
    Image = None
    ImageFilter = None


def frame_dir() -> str:
    """帧图持久化目录（不能放临时目录，会被清理）。"""
    path = os.path.join(os.path.abspath(settings.LOCAL_STORAGE_DIR), "frames")
    os.makedirs(path, exist_ok=True)
    return path


def public_path(name: str) -> str:
    """前端可直接访问的帧图路径（非服务器绝对路径）。"""
    return f"/api/videos/frames/{name}"


def _ts_label(sec: float) -> str:
    sec = max(0, int(round(float(sec or 0))))
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _probe_duration(path: str) -> float:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            capture_output=True, timeout=60,
        )
        return float((out.stdout or b"").decode("utf-8", "ignore").strip() or 0)
    except Exception:
        return 0.0


def has_video_stream(path: str) -> bool:
    """纯音频（如只有 bestaudio 的 webm/m4a）没有视频流，跳过抽帧。"""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
            capture_output=True, timeout=60,
        )
        return b"video" in (out.stdout or b"")
    except Exception:
        return os.path.splitext(path)[1].lower() in _VIDEO_EXT


def _run_ffmpeg(src: str, vf: str, outdir: str, prefix: str) -> tuple[list[str], list[float]]:
    pattern = os.path.join(outdir, f"{prefix}%04d.jpg")
    cmd = ["ffmpeg", "-y", "-hide_banner", "-i", src, "-vf", vf,
           "-fps_mode", "vfr", "-q:v", "3", pattern]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        _log.warning("抽帧 ffmpeg 执行失败：%s", e)
        return [], []
    stderr = (res.stderr or b"").decode("utf-8", "ignore")
    files = sorted(f for f in os.listdir(outdir) if f.startswith(prefix) and f.endswith(".jpg"))
    paths = [os.path.join(outdir, f) for f in files]
    ts = [float(x) for x in _TS_RE.findall(stderr)]
    return paths, ts


def extract_frames(video_path: str, outdir: str, max_frames: int = 24,
                   interval: float | None = None) -> list[dict]:
    """按场景变化抽帧；命中太少则退化为等间隔抽帧。失败返回 []（不抛异常）。"""
    if not video_path or not os.path.isfile(video_path):
        return []
    try:
        os.makedirs(outdir, exist_ok=True)
    except OSError:
        return []

    uid = uuid.uuid4().hex[:8]
    try:
        # 1) 场景切换抽帧（PPT 翻页、板书切换会被捕捉到）
        paths, ts = _run_ffmpeg(video_path, "select='gt(scene,0.3)',scale=1280:-1,showinfo",
                                outdir, f"s{uid}_")
        # 2) 场景帧不足 → 等间隔抽帧（静态画面/测试视频）
        if len(paths) < 6:
            for p in paths:
                try:
                    os.remove(p)
                except OSError:
                    pass
            duration = _probe_duration(video_path)
            step = interval or (duration / max(1, max_frames) if duration > 0 else 0)
            if step <= 0:
                step = 1.0
            paths, ts = _run_ffmpeg(video_path,
                                    f"fps=1/{step:.6f},scale=1280:-1,showinfo",
                                    outdir, f"q{uid}_")
            if not ts:
                ts = [i * step for i in range(len(paths))]
    except Exception as e:  # 抽帧失败不影响主流程
        _log.warning("关键帧抽取失败：%s", e)
        return []

    if not paths:
        return []

    # 超过上限时均匀采样，保证覆盖全片
    if len(paths) > max_frames:
        step = len(paths) / max_frames
        picked = [int(i * step) for i in range(max_frames)]
        picked[-1] = min(picked[-1], len(paths) - 1)
        keep = []
        for i in picked:
            if i not in keep:
                keep.append(i)
        for idx, p in enumerate(paths):
            if idx not in keep:
                try:
                    os.remove(p)
                except OSError:
                    pass
        paths = [paths[i] for i in keep]
        ts = [ts[i] if i < len(ts) else 0.0 for i in keep]

    frames: list[dict] = []
    for i, p in enumerate(paths):
        t = float(ts[i]) if i < len(ts) else 0.0
        label = _ts_label(t)
        # 文件名带上时间戳，避免不同视频互相覆盖且便于排查
        name = f"{uid}_{i:02d}_{label.replace(':', '-')}.jpg"
        dst = os.path.join(outdir, name)
        try:
            os.replace(p, dst)
        except OSError:
            dst = p
            name = os.path.basename(p)
        frames.append({"path": dst, "ts": round(t, 2), "ts_label": label, "name": name})
    return frames


def _ahash(path: str) -> int | None:
    if Image is None:
        return None
    try:
        with Image.open(path) as im:
            g = im.convert("L").resize((16, 16))
            px = list(g.getdata())
    except Exception:
        return None
    avg = sum(px) / len(px)
    bits = 0
    for v in px:
        bits = (bits << 1) | (1 if v >= avg else 0)
    return bits


def dedupe_frames(frames: list[dict], threshold: float = 0.985) -> list[dict]:
    """均值哈希去重：汉明相似度 >= threshold 视为重复帧。"""
    if Image is None or len(frames) < 2:
        return frames
    min_diff = max(1, int(round((1 - threshold) * 256)))
    kept: list[dict] = []
    hashes: list[int] = []
    for f in frames:
        h = _ahash(f["path"])
        if h is None:
            kept.append(f)
            continue
        dup = False
        for hk in hashes:
            if (h ^ hk).bit_count() < min_diff:
                dup = True
                break
        if dup:
            try:
                os.remove(f["path"])
            except OSError:
                pass
            continue
        kept.append(f)
        hashes.append(h)
    return kept


def is_doc_frame(frame: dict) -> bool:
    """粗判文档/PPT 帧：大面积浅色背景 + 中等密度文字边缘。"""
    if Image is None or ImageFilter is None:
        return False
    try:
        with Image.open(frame["path"]) as im:
            g = im.convert("L")
            if g.width > 360:
                g = g.resize((360, max(1, int(g.height * 360 / g.width))))
            px = list(g.getdata())
            if not px:
                return False
            white_ratio = sum(1 for v in px if v >= 200) / len(px)
            edges = g.filter(ImageFilter.FIND_EDGES)
            ep = list(edges.getdata())
            if not ep:
                return False
            edge_ratio = sum(1 for v in ep if v >= 60) / len(ep)
    except Exception:
        return False
    return white_ratio >= 0.45 and 0.004 <= edge_ratio <= 0.30


class _FrameSection(BaseModel):
    ts: str = ""
    title: str = ""
    content: str = ""


class _FrameNote(BaseModel):
    summary: str = ""
    sections: list[_FrameSection] = []


async def _ocr_one(frame: dict) -> str:
    with open(frame["path"], "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    messages = [{"role": "user", "content": [
        {"type": "text", "text": FRAME_OCR_SYSTEM + "\n" + frame_ocr_user(frame.get("ts_label", ""))},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
    ]}]
    res = await chat(settings.LLM_LIGHT_MODEL, messages, temperature=0,
                     max_tokens=6000, json_mode=False, effort="low")
    return (res.text or "").strip()


async def ocr_frames(frames: list[dict], max_ocr: int = 12, on_progress=None) -> list[dict]:
    """对关键帧做视觉转写，文档帧优先；单帧失败跳过。

    提速（2026-11-22）：并发识别（Semaphore 限流，默认 4 路），
    替代原来逐帧串行 await（12 帧 × 单次 LLM 往返）。每帧完成回写进度，
    避免抽帧/OCR 阶段长时间无进度被看门狗误判超时。
    """
    if not frames or max_ocr <= 0:
        return []
    # 文档帧优先送识别，剩余名额给其他帧，最终仍按时间顺序输出
    ordered = [f for f in frames if f.get("is_doc")] + [f for f in frames if not f.get("is_doc")]
    picked = ordered[:max_ocr]
    picked_ids = {id(f) for f in picked}
    results: dict[int, dict] = {}
    sem = asyncio.Semaphore(4)
    done = 0

    async def _one(frame: dict):
        nonlocal done
        async with sem:
            try:
                text = await _ocr_one(frame)
                if text:
                    results[id(frame)] = {
                        "ts": frame.get("ts"), "ts_start": frame.get("ts"),
                        "ts_label": frame.get("ts_label"),
                        "path": frame.get("name") or os.path.basename(frame.get("path", "")),
                        "text": text, "is_doc": bool(frame.get("is_doc")),
                    }
            except Exception as e:
                _log.warning("帧 %s 转写失败：%s", frame.get("ts_label"), e)
            finally:
                done += 1
                if on_progress:
                    on_progress(done, len(picked))

    await asyncio.gather(*[_one(f) for f in picked])
    return [results[id(f)] for f in frames if id(f) in results and id(f) in picked_ids]


async def build_frame_note(ocr_items: list[dict]) -> dict:
    """多关键帧 → 图文笔记；失败返回空结构。"""
    if not ocr_items:
        return {"summary": "", "sections": []}
    texts = [{"ts_label": it.get("ts_label", ""), "text": it.get("text", "")} for it in ocr_items]
    obj = None
    # light 档 1500 token 装不下多节图文，且 JSON 严格度不够；先 mid 再 strong 兜底
    for tier, mt in (("mid", 4000), ("strong", 6000)):
        try:
            obj, _ = await generate_json(tier, FRAME_NOTE_SYSTEM, frame_note_user(texts),
                                         _FrameNote, max_tokens=mt)
            break
        except Exception as e:  # noqa: BLE001  换档重试，最后仍失败返回空结构
            _log.warning("图文笔记生成失败（tier=%s）：%s", tier, e)
    if obj is None:
        return {"summary": "", "sections": []}
    return {"summary": (obj.summary or "").strip(),
            "sections": [{"ts": s.ts.strip(), "title": s.title.strip(), "content": s.content.strip()}
                         for s in obj.sections if (s.title or s.content)]}


def render_frame_note_md(note: dict, ocr_items: list[dict]) -> str:
    """Markdown：每节 `## [mm:ss] 标题` + 图 + 文档帧「图内文字」折叠块。"""
    by_ts: dict[str, dict] = {}
    for it in ocr_items:
        by_ts.setdefault(it.get("ts_label", ""), it)
    lines: list[str] = []
    summary = (note.get("summary") or "").strip()
    if summary:
        lines += ["> " + summary.replace("\n", " "), ""]
    for sec in note.get("sections") or []:
        title = (sec.get("title") or "").strip()
        content = (sec.get("content") or "").strip()
        ts = (sec.get("ts") or "").strip()
        head = f"## [{ts}] {title}" if ts else f"## {title}"
        lines += [head, content, ""]
        it = by_ts.get(ts) or (ocr_items[0] if len(note.get("sections") or []) == 1 else None)
        if it:
            lines += [f"![{it.get('ts_label', '')}]({public_path(it['path'])})", ""]
            if it.get("is_doc") and (it.get("text") or "").strip():
                lines += ["<details>", "<summary>图内文字</summary>", "",
                          (it.get("text") or "").strip(), "", "</details>", ""]
    if ocr_items:
        lines += ["## 关键帧", ""]
        for it in ocr_items:
            lines.append(f"- [{it.get('ts_label', '')}]({public_path(it['path'])})"
                         + ("（文档）" if it.get("is_doc") else ""))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


# ---------------------------------------------------------------------------
# A3 / D8：网格拼图（一次解码抽多帧 + 拼图，视觉 OCR 调用压到 ≤2 次/视频）
# ---------------------------------------------------------------------------
_GRID_OCR_SYSTEM = (
    "你是文档图像识别助手。输入是一张由多张视频截图按「从左到右、从上到下」拼成的网格。"
    "请逐格提取图中可见的文字与公式：\n"
    "- 每行输出一条：`序号|转写文本`，序号从 1 开始，与格子顺序一一对应；\n"
    "- 没有文字的格子输出 `序号|`；\n"
    "- 公式用 LaTeX，表格用 Markdown；只输出逐格结果，不要描述图片外观，不要编造。"
)
_GRID_LINE_RE = re.compile(r"^\s*(\d{1,2})\s*[|｜:：]\s*(.*)$")


def build_grid_vf(step: float, cols: int, rows: int, cell_w: int = 320) -> str:
    """构造 ffmpeg filter：等间隔取帧 → 缩放 → showinfo(取时间轴锚点) → tile 拼图。"""
    return (f"fps=1/{step:.6f},scale={cell_w}:-2,showinfo,"
            f"tile={cols}x{rows}:padding=4:margin=4:color=white")


def extract_grid_frames(video_path: str, outdir: str, max_frames: int = 24,
                        cols: int = 4, rows: int = 3,
                        cell_w: int = 320) -> list[dict]:
    """一次解码生成网格拼图；返回 ≤2 张网格，每张带 cell 时间轴锚点 times/ts_start（D8）。

    与逐帧抽图相比：ffmpeg 只解码一次，视觉模型只调用 ≤2 次（每网格一次）。
    失败返回 [] 并打 WARNING，由调用方回退到 extract_frames + ocr_frames。
    """
    if not video_path or not os.path.isfile(video_path):
        return []
    try:
        os.makedirs(outdir, exist_ok=True)
    except OSError as e:
        _log.warning("网格拼图目录创建失败：%s", e)
        return []
    duration = _probe_duration(video_path)
    total = max(1, min(int(max_frames or 24), cols * rows * 2))
    step = (duration / total) if duration > 0 else 1.0
    if step <= 0:
        step = 1.0
    uid = uuid.uuid4().hex[:8]
    prefix = f"grid{uid}_"
    pattern = os.path.join(outdir, f"{prefix}%02d.jpg")
    # -skip_frame nokey：只解码关键帧，27 分钟视频抽帧 63s → 10s 级（B 站编码 2-10s 一个关键帧）
    cmd = ["ffmpeg", "-y", "-hide_banner", "-skip_frame", "nokey", "-an", "-i", video_path,
           "-vf", build_grid_vf(step, cols, rows, cell_w),
           "-fps_mode", "vfr", "-q:v", "3", pattern]
    try:
        res = subprocess.run(cmd, capture_output=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as e:
        _log.warning("网格拼图 ffmpeg 执行失败，回退逐帧 OCR：%s", e)
        return []
    if res.returncode != 0:
        msg = (res.stderr or b"")[-200:].decode("utf-8", "ignore")
        _log.warning("网格拼图 ffmpeg 返回 %s：%s，回退逐帧 OCR", res.returncode, msg)
        return []
    times = [float(x) for x in _TS_RE.findall((res.stderr or b"").decode("utf-8", "ignore"))]
    files = sorted(f for f in os.listdir(outdir) if f.startswith(prefix) and f.endswith(".jpg"))
    grids: list[dict] = []
    per = cols * rows
    for i, name in enumerate(files[:2]):  # 至多 2 张 → 至多 2 次视觉调用
        cell_ts = times[i * per:(i + 1) * per]
        grids.append({
            "path": os.path.join(outdir, name), "name": name, "index": i,
            "times": cell_ts, "ts_start": round(cell_ts[0], 2) if cell_ts else 0.0,
            "cols": cols, "rows": rows, "source": "grid",
        })
    if not grids:
        _log.warning("网格拼图未产出图片（video=%s），回退逐帧 OCR", os.path.basename(video_path))
    return grids


def parse_grid_ocr(text: str, grid: dict, cols: int = 4, rows: int = 3) -> list[dict]:
    """把 `序号|文本` 行解析成带 ts_start 的逐格 OCR 项（纯函数，便于单测）。"""
    times = grid.get("times") or []
    out: list[dict] = []
    matched = 0
    for line in (text or "").splitlines():
        m = _GRID_LINE_RE.match(line)
        if not m:
            continue
        idx = int(m.group(1))
        if idx < 1 or idx > cols * rows:
            continue
        matched += 1
        body = (m.group(2) or "").strip()
        if not body:
            continue
        t = times[idx - 1] if idx - 1 < len(times) else float(grid.get("ts_start") or 0)
        out.append({
            "ts": round(float(t), 2), "ts_start": round(float(t), 2),
            "ts_label": _ts_label(t), "path": grid.get("name") or os.path.basename(grid.get("path", "")),
            "text": body, "is_doc": True, "source": "grid", "cell": idx,
        })
    if not matched and (text or "").strip():
        # 不静默失败：模型没按格式输出时，保留整段文本并打 WARNING，按网格首帧锚点定位。
        _log.warning("网格 OCR 返回格式无法逐格解析，退化为整段文本（grid=%s）", grid.get("name"))
        t = float(grid.get("ts_start") or 0)
        out = [{
            "ts": round(t, 2), "ts_start": round(t, 2), "ts_label": _ts_label(t),
            "path": grid.get("name") or os.path.basename(grid.get("path", "")),
            "text": (text or "").strip(), "is_doc": True, "source": "grid", "cell": 0,
        }]
    out.sort(key=lambda x: (x.get("ts_start") or 0, x.get("cell") or 0))
    return out


async def ocr_grid_one(grid: dict, on_progress=None) -> list[dict]:
    """对一张网格图调用一次视觉模型。失败 WARNING 并返回 []。"""
    try:
        with open(grid["path"], "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
    except OSError as e:
        _log.warning("网格图读取失败（%s）：%s", grid.get("name"), e)
        return []
    cols, rows = int(grid.get("cols") or 4), int(grid.get("rows") or 3)
    times = grid.get("times") or []
    hint = "；".join(f"{i + 1}={_ts_label(t)}" for i, t in enumerate(times[:cols * rows]))
    messages = [{"role": "user", "content": [
        {"type": "text", "text": f"{_GRID_OCR_SYSTEM}\n格子对应视频时间点：{hint}\n共 {cols * rows} 格。"},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
    ]}]
    try:
        # 视觉通道：方舟 deepseek-v4-1-flash 实测 13.2s/张（现有 DeepSeek light 档 100s+）
        from app.ai import ark
        from app.services.settings_store import cached
        if ark.available():
            _v = cached("vision")
            res = await ark.chat(
                _v[2] if _v else settings.ARK_VISION_MODEL,
                [{"role": "user", "content": [
                    {"type": "text", "text": f"{_GRID_OCR_SYSTEM}\n格子对应视频时间点：{hint}\n共 {cols * rows} 格。"},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
                ]}],
                temperature=0, max_tokens=2000,
            )
        else:
            res = await chat(settings.LLM_LIGHT_MODEL, messages, temperature=0,
                             max_tokens=3500, json_mode=False, effort="low")
        return parse_grid_ocr(res.text or "", grid, cols, rows)
    except Exception as e:
        _log.warning("网格 %s 视觉识别失败：%s", grid.get("name"), e)
        return []
    finally:
        if on_progress:
            on_progress(1, 1)


async def ocr_grids(grids: list[dict], max_calls: int = 2, on_progress=None) -> tuple[list[dict], int]:
    """A3：逐网格 OCR，硬上限 max_calls 次视觉调用（默认 2）。返回 (逐格 OCR 项, 实际调用次数)。

    两张网格是独立 IO，串行要跑两次 60s 级视觉调用；并发后总耗时≈一次（实测 120s → 60s）。
    """
    import asyncio

    picked = grids[:max(0, int(max_calls))]
    if not picked:
        _log.warning("网格 OCR 未执行（grids=%s）；视频没有可识别的视觉流", len(grids or []))
        return [], 0
    results = await asyncio.gather(*[ocr_grid_one(g, on_progress) for g in picked],
                                   return_exceptions=True)
    items: list[dict] = []
    calls = 0
    for res in results:
        calls += 1
        if isinstance(res, BaseException):
            _log.warning("网格 OCR 单张失败：%s", res)
            continue
        items.extend(res)
    return items, calls
