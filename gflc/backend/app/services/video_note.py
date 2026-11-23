# -*- coding: utf-8 -*-
"""单篇 Markdown 视频笔记（对标 BiliNote 的生成范式）。

与三模板 JSON 路径的区别：
- 模型**直接写 Markdown**，没有 JSON 结构可崩（长视频不再截断）；
- 每个 `##` 标题带 `*Content-[mm:ss]`，前端可点跳转；
- 需要图示处写 `*Screenshot-[mm:ss]`，后处理用 ffmpeg 精确抽帧替换成图片。

许可说明：生成范式参考开源项目 BiliNote（MIT, © JefferyHcool）的公开做法，
提示词与后处理为本项目重写，未复制其文件。
"""
import logging
import os
import re
import subprocess

from app.ai import ark
from app.core.config import settings
from app.services.settings_store import cached

_log = logging.getLogger(__name__)

_SYS = """你是资深学习笔记编辑，服务对象是考研/自学的中国学生。请把视频讲稿整理成一份可直接复习的 Markdown 笔记。

硬性要求：
1. 只输出 Markdown 正文，**不要**包裹在 ``` 代码块里，**不要**输出 JSON；
2. 用 ## 和 ### 组织层级，标题必须是信息性短语（不要「第一部分」这类空标题）；
3. 每个 ## 标题末尾追加该段起始时间，格式：`*Content-[mm:ss]`；
4. **必须配图（硬性要求）**：全片写 6–20 个 `*Screenshot-[mm:ss]` 标记，单独一行，间隔约 2–4 分钟；凡是屏幕上出现题目原文、板书、公式推导、图表、界面演示的段落都必须写一个；刷题类视频几乎每一题都该有一张，不要因为「文字已经说清」就省略；
5. 数学公式用 LaTeX：行内 $...$，独立 $$...$$；
6. 术语按上下文纠正语音识别错字（如「间隔重复」「泊松过程」），保留英文专有名词；
7. 去掉口水话、寒暄、重复，但**不要丢掉结论、数字、定义、步骤、易错点**；
8. 结尾加「## 一页速记」，用 5-8 条要点收束全文。
"""


def available() -> bool:
    return ark.available()


def build_markdown(transcript: str, title: str, *, max_tokens: int = 8000) -> str:
    """调方舟生成 Markdown 笔记；失败返回空串（调用方保留三模板结果）。"""
    if not available():
        return ""
    model = (cached("note") or (None, None, settings.ARK_NOTE_MODEL))[2]
    user = f"视频标题：{title}\n\n分段讲稿（行首 [mm:ss] 为时间戳）：\n{transcript[:60000]}"
    import asyncio
    try:
        md = asyncio.run(ark.generate_text(model, _SYS, user, max_tokens=max_tokens, temperature=0.3))
    except Exception as e:  # noqa: BLE001  失败不阻断，三模板仍可用
        _log.warning("Markdown 笔记生成失败：%s", e)
        return ""
    return _clean_md(md)


def _clean_md(md: str) -> str:
    md = (md or "").strip()
    if md.startswith("```"):
        md = re.sub(r"^```[a-zA-Z]*\n", "", md)
        md = re.sub(r"\n```$", "", md)
    return md.strip()


_SCREEN_RE = re.compile(r"\*?Screenshot-\[(\d{1,2}):(\d{2})\]")
_CONTENT_RE = re.compile(r"\*?Content-\[(\d{1,2}):(\d{2})\]")


def screenshot_points(md: str) -> list[tuple[str, int]]:
    """提取截图标记 [(原始标记, 秒)]，按时间排序去重。"""
    out, seen = [], set()
    for m in _SCREEN_RE.finditer(md or ""):
        sec = int(m.group(1)) * 60 + int(m.group(2))
        if sec in seen:
            continue
        seen.add(sec)
        out.append((m.group(0), sec))
    return sorted(out, key=lambda x: x[1])


def content_links(md: str) -> str:
    """把 `*Content-[mm:ss]` 转成可点击的时间链接（前端拦截 ?t= 跳转）。

    模型偶尔写成 `*Content-[00:00]*`（首尾都有星号），替换后要清掉残尾 `*`，
    否则渲染出来是一串裸星号。
    """
    out = _CONTENT_RE.sub(lambda m: f"[{m.group(1)}:{m.group(2)}](/video?t={int(m.group(1))*60+int(m.group(2))})", md or "")
    out = re.sub(r"(\]\(/video\?t=\d+\))\*+", r"\1", out)
    return out


def grab_frames(video_path: str, outdir: str, points: list[tuple[str, int]],
                *, doc_id: int, min_gap: int = 180, max_n: int = 20,
                width: int = 960) -> dict[int, str]:
    """按时间点精确抽帧（每点一次 ffmpeg -ss 定位，比全片解码快两个数量级）。

    返回 {秒: 公开URL}；失败的点跳过，不抛异常。
    """
    if not video_path or not os.path.isfile(video_path) or not points:
        return {}
    try:
        os.makedirs(outdir, exist_ok=True)
    except OSError as e:
        _log.warning("截图目录创建失败：%s", e)
        return {}

    picked, last = [], None
    for _, sec in points:
        if last is not None and sec - last < max(30, min_gap):
            continue
        picked.append(sec)
        last = sec
        if len(picked) >= max_n:
            break

    out: dict[int, str] = {}
    for sec in picked:
        name = f"shot{doc_id}_{sec:05d}.jpg"
        path = os.path.join(outdir, name)
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-ss", str(max(0, sec - 0.3)), "-i", video_path, "-frames:v", "1",
                 "-vf", f"scale={width}:-2", "-q:v", "3", path],
                check=True, capture_output=True, timeout=60,
            )
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                out[sec] = f"/api/videos/frames/{name}"
        except (OSError, subprocess.SubprocessError) as e:
            _log.warning("截图失败 ts=%ss：%s", sec, e)
    _log.info("截图完成 doc=%s 命中 %s/%s", doc_id, len(out), len(picked))
    return out


def apply_screenshots(md: str, shots: dict[int, str]) -> str:
    """把截图标记替换成 Markdown 图片；没抓到的标记直接删掉，避免露出裸标记。"""
    def rep(m: re.Match) -> str:
        sec = int(m.group(1)) * 60 + int(m.group(2))
        url = shots.get(sec)
        if not url:
            return ""
        return f"![{m.group(1)}:{m.group(2)}]({url})"
    out = _SCREEN_RE.sub(rep, md or "")
    out = re.sub(r"(\]\(/api/videos/frames/[^)]+\))\*+", r"\1", out)
    return out.replace("\n\n\n", "\n\n")


def stats(md: str, shots: dict[int, str]) -> dict:
    return {"chars": len(md or ""), "screenshots": len(shots),
            "headings": len(re.findall(r"^##\s", md or "", flags=re.M))}


def keypoints(md: str) -> list[dict]:
    """从 Markdown 笔记的 `## 标题 [mm:ss]` 提取时间轴关键点（不是整段转写）。

    用户明确要「时间轴只留关键点」：一段一小时视频的转写有上千段，摊开就是废话；
    这里只输出章节级锚点，前端点一下就 seek 到对应位置。
    """
    out = []
    for m in re.finditer(r"^##\s+(.+?)\s*\[(\d{1,2}):(\d{2})\]", md or "", flags=re.M):
        label = re.sub(r"[*`_#]", "", m.group(1)).strip()
        sec = int(m.group(2)) * 60 + int(m.group(3))
        if not label:
            continue
        out.append({"ts": sec, "label": label[:40]})
    # 同一时间点去重，按时间排序
    seen, uniq = set(), []
    for kp in sorted(out, key=lambda x: x["ts"]):
        if kp["ts"] in seen:
            continue
        seen.add(kp["ts"])
        uniq.append(kp)
    return uniq
