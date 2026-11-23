# -*- coding: utf-8 -*-
"""试卷视觉解析：PDF 逐页渲染 → 多模态识别 → 结构化题目（含 LaTeX）。
解决「文本层公式丢失导致题目残破」的问题。

同时提供资料解析路径的扫描件 OCR 兜底（ocr_pdf_to_pages）：复用同一视觉通道，
逐页转录文字，返回 [(页码, 文本)]，与文字层 PDF 共用分块/入库链路。
"""
import asyncio
import base64
import hashlib
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

import pymupdf

from app.ai.deepseek import chat, extract_json
from app.core.config import settings
from app.core.errors import APIError, ErrCode

_log = logging.getLogger(__name__)

PROMPT = """这是考研试卷的一页。识别其中所有题目，数学公式用 LaTeX（$...$）。
输出 JSON：
{"paper_meta":{"subject":"考研数学/英语/政治/专业课等","title":""},
 "questions":[{"no":"1","section":"选择题|填空题|解答题","chapter":"高等数学|线性代数|概率论与数理统计|其他","stem":"","options":["A. ...","B. ...","C. ...","D. ..."],"answer":""}]}
要求：
- 题干完整，公式必须用 LaTeX 还原，不要丢失
- 选择题给 4 个选项；填空题/解答题 options 为空数组
- answer 只填试卷中明确印出的答案；没有就留空，禁止编造
- 卷首说明、分值表、答题提示不是题目，不要放进 questions
- chapter 按题目知识点判断（数学卷：高数/线代/概率）
只输出 JSON，不要解释。"""


def _render_one(path: str, index: int, dpi: int, jpeg_quality: int) -> bytes:
    """渲染单页。每页独立 open，避免 PyMuPDF 文档对象跨线程共享（非线程安全）。"""
    doc = pymupdf.open(path)
    try:
        return doc[index].get_pixmap(dpi=dpi).tobytes("jpeg", jpg_quality=jpeg_quality)
    finally:
        doc.close()


def render_pages(path: str, dpi: int = 140, jpeg_quality: int = 72,
                 parallel: int | None = None) -> list[bytes]:
    """逐页渲染为 JPEG。实测同页 PNG 197KB / JPEG 85KB，视觉转录耗时减半且文字量不变。

    jpeg_quality 默认 72 保持 parse_paper 旧行为；OCR 链路按 profile 传入（quality 85 / fast 60）。
    parallel>1 时按页并行渲染（13 页实测 7.65s → 4.92s）；PyMuPDF 文档非线程安全，
    因此每页独立 open。页序由 map 保证，与串行一致。
    """
    if parallel is None:
        parallel = max(1, min(4, int(os.getenv("OCR_RENDER_WORKERS", "4") or 4)))
    doc = pymupdf.open(path)
    try:
        n = doc.page_count
    finally:
        doc.close()
    if parallel <= 1 or n <= 1:
        return [_render_one(path, i, dpi, jpeg_quality) for i in range(n)]
    with ThreadPoolExecutor(max_workers=parallel) as ex:
        return list(ex.map(lambda i: _render_one(path, i, dpi, jpeg_quality), range(n)))


async def extract_page(png: bytes) -> dict:
    b64 = base64.b64encode(png).decode()
    messages = [{"role": "user", "content": [
        {"type": "text", "text": PROMPT},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
    ]}]
    res = await chat(settings.LLM_LIGHT_MODEL, messages, temperature=0,
                     max_tokens=16000, json_mode=False, effort="low")
    return extract_json(res.text)


async def parse_paper(path: str, on_progress=None) -> dict:
    pages = render_pages(path)
    questions: list[dict] = []
    meta: dict = {}
    for i, png in enumerate(pages):
        if on_progress:
            on_progress(int(5 + 85 * (i + 1) / max(1, len(pages))))
        try:
            data = await extract_page(png)
        except Exception:
            continue
        if not meta and data.get("paper_meta"):
            meta = data.get("paper_meta") or {}
        for q in data.get("questions", []) or []:
            q["page"] = i + 1
            questions.append(q)
    return {"meta": meta, "questions": questions, "pages": len(pages)}


# ---------------------------------------------------------------------------
# 资料解析路径：扫描件（无文字层）视觉 OCR 兜底
# 复用上面的 render_pages / chat / extract_json 同一视觉通道，不另起一套调用。
# ---------------------------------------------------------------------------
# prompt 版本：任何 prompt 文案改动都必须 +1，使页级缓存自动失效（缓存 key 含此值）
OCR_PROMPT_VERSION = "v2-plain-20261123"

# 旧 JSON 提示词保留，仅 OCR_OUTPUT_FORMAT=json 时使用（回归对照），保持原文不改。
OCR_TEXT_PROMPT = """这是一份考研试卷/学习资料的一页扫描图。请把页面上**所有可见文字**完整转录出来，
包括题目、选项、答案、公式、表格文字、页眉页脚；数学公式用 LaTeX（$...$）表示，
保持原有顺序与换行；不要总结、不要翻译、不要补写页面上看不见的内容。
只输出 JSON：{"text": "本页完整文字"}"""

# 复杂版面下模型偶发输出非法 JSON；用纯文本直出重试一次，避免整页丢失（仅 json 模式）
OCR_RAW_PROMPT = """逐字转录这页扫描图上的所有可见文字，保持原有顺序与换行，公式用 LaTeX。
不要总结、不要解释、不要补写页面上看不见的内容，直接输出文字本身。"""

# 纯文本直出提示词（核心改动）：合并 OCR_RAW_PROMPT 的覆盖要求与 JSON 版的
# 「表格/页眉页脚/公式」枚举，只去掉「只输出 JSON」的结构约束。
_OCR_PLAIN_BASE = """这是一份考研试卷/学习资料的一页扫描图。请把页面上所有可见文字完整转录出来，
包括题目、选项、答案、公式、表格文字、页眉页脚；不要总结、不要翻译、不要补写页面上看不见的内容。
表格按行列转录为 Markdown 表格并保留表头；数学公式用 LaTeX（$...$）表示；保持原有阅读顺序与换行。
直接输出文字本身，不要 JSON、不要解释、不要代码围栏。"""

_OCR_COLUMN_HINT = "若为分栏版面，先左栏后右栏逐栏转录，不要左右栏交错。"

_OCR_QUALITY_FORMULA_HINT = "公式中的分式用 \\frac、根号用 \\sqrt、矩阵用 matrix 环境，上下标用 ^ 与 _。"

_OCR_FAST_HINT = """逐字转录这页扫描图上的所有可见文字，包括题目、选项、答案、表格与页眉页脚；
数学公式用 LaTeX（$...$）表示。不要总结、不要解释，直接输出文字本身。"""


def _ocr_bool(name: str, default: bool) -> bool:
    """读取布尔型 OCR 环境变量；未设置时用 profile 默认值。"""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _output_format() -> str:
    """plain（默认纯文本直出）/ json（旧行为兼容）。"""
    fmt = (os.getenv("OCR_OUTPUT_FORMAT")
           or getattr(settings, "OCR_OUTPUT_FORMAT", "plain") or "plain").strip().lower()
    return fmt if fmt in ("plain", "json") else "plain"


def _ocr_profile() -> str:
    """三档预设：quality / balanced / fast，非法值回落 balanced。"""
    profile = (os.getenv("OCR_PROFILE")
               or getattr(settings, "OCR_PROFILE", "balanced") or "balanced").strip().lower()
    return profile if profile in ("balanced", "quality", "fast") else "balanced"


def _profile_defaults(profile: str) -> dict:
    """28 号报告 §4.1 的三档旋钮取值（DPI 固定 140、并发固定 2，不随档位变）。

    DPI 180 已于 2026-11-23 做单页 A/B（quality 档 prompt + q85，第 8/4 页各 1 次）：
    公式配对数 86→86、78→78（提升 0%），字符数 +2.75% / −11.4%（方向不一致、均值 −4.3%），
    图像字节 +47%；无实质质量收益，故 quality 档不引入 dpi 键，三档统一 140。
    """
    return {
        "balanced": {"jpeg_quality": 72, "max_tokens": 16000, "formula_check": True, "retry": True},
        "quality": {"jpeg_quality": 85, "max_tokens": 16000, "formula_check": True, "retry": True},
        "fast": {"jpeg_quality": 60, "max_tokens": 12000, "formula_check": True, "retry": False},
    }[profile]


def _build_ocr_prompt(output_format: str, profile: str) -> str:
    """按输出格式与档位构造提示词。json 模式保持原文，便于 A/B 对照。"""
    if output_format == "json":
        return OCR_TEXT_PROMPT
    prompt = _OCR_FAST_HINT if profile == "fast" else _OCR_PLAIN_BASE
    if profile == "quality":
        prompt += "\n" + _OCR_QUALITY_FORMULA_HINT
    if _ocr_bool("OCR_COLUMN_AWARE", True):
        prompt += "\n" + _OCR_COLUMN_HINT
    return prompt


# 公式配平正则：只匹配单行 $...$；跨行公式在 OCR 文本中罕见，按「$ 奇数」兜底捕获。
_FORMULA_RE = re.compile(r"\$[^$\n]*\$")


def check_formula_balance(text: str) -> dict:
    """对 $...$ 做数量配平 / 长度异常 / 花括号与 \\left-\\right 配平检测。

    只生成诊断结果，不修改文本、不阻断入库；调用方把可疑页码记入 stats。
    """
    dollar_count = text.count("$")
    spans = list(_FORMULA_RE.finditer(text))
    issues: list[str] = []
    if dollar_count % 2:
        issues.append("dollar_odd")
    if len(spans) * 2 != dollar_count:
        issues.append("dollar_unpaired")
    for m in spans:
        formula = m.group(0)
        if len(formula) > 500:
            issues.append("formula_too_long")
            break
        if formula.count("{") != formula.count("}"):
            issues.append("brace_unbalanced")
            break
    if len(re.findall(r"\\left\b", text)) != len(re.findall(r"\\right\b", text)):
        issues.append("left_right_unbalanced")
    return {"formula_count": dollar_count // 2, "suspect": bool(issues), "issues": issues}


# 页级缓存：进程内字典，key 含 内容hash+页码+dpi+模型+prompt版本+profile，
# 任一要素变化即失效；上限保护避免长期 worker 无限增长。
_OCR_CACHE: dict[str, str] = {}
_OCR_CACHE_MAX = 2000


def _page_cache_key(content_hash: str, page_no: int, dpi: int, png: bytes,
                    prompt: str, profile: str) -> str:
    digest = hashlib.sha256(png).hexdigest()
    raw = "|".join([
        content_hash, str(page_no), str(dpi), digest,
        str(getattr(settings, "ARK_VISION_MODEL", "")),
        OCR_PROMPT_VERSION, profile, prompt,
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# 按事件循环缓存信号量（与 app/ai/ark.py 的 _sem 同一做法）：
# 每个任务用 asyncio.run 起独立 loop，跨 loop 复用 Semaphore 会报错。
# 上限对齐方舟 ARK_MAX_CONCURRENCY=2，避免 3 并发即 429 的坑。
_OCR_SEMS: dict[int, "asyncio.Semaphore"] = {}


def _ocr_sem() -> "asyncio.Semaphore":
    loop = asyncio.get_running_loop()
    key = id(loop)
    sem = _OCR_SEMS.get(key)
    if sem is None:
        cap = int(os.getenv("OCR_MAX_CONCURRENCY",
                            str(getattr(settings, "ARK_MAX_CONCURRENCY", 2) or 2)) or 2)
        sem = asyncio.Semaphore(max(1, cap))
        _OCR_SEMS[key] = sem
    return sem


async def _vision_chat(prompt: str, png: bytes, max_tokens: int):
    """方舟视觉优先，失败回落 DeepSeek；两次调用都受 _ocr_sem 限流。"""
    b64 = base64.b64encode(png).decode()
    messages = [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + b64}},
    ]}]
    async with _ocr_sem():
        if getattr(settings, "ARK_ENABLED", True):
            try:
                from app.ai import ark
                if ark.available():
                    return await ark.chat(settings.ARK_VISION_MODEL, messages, temperature=0,
                                          max_tokens=max_tokens, effort="low")
            except APIError as e:
                _log.warning("方舟视觉 OCR 失败，回落 DeepSeek：%s", e)
        return await chat(settings.LLM_LIGHT_MODEL, messages, temperature=0,
                          max_tokens=max_tokens, json_mode=False, effort="low")


async def ocr_page_text(png: bytes, *, max_tokens: int | None = None,
                        output_format: str | None = None,
                        meta: dict | None = None) -> str:
    """识别单页扫描图并转录为文字；并发受 _ocr_sem 限制，失败向上抛由调用方统计。

    默认纯文本直出（实测 15.41s/页）；output_format='json' 时恢复旧的
    JSON + 失败重试行为，仅用于回归对照。meta 为可选出参，回填 json_retry 标记，
    供 ocr_pdf_to_pages 写入 stats（不新增 API 契约字段）。
    """
    profile = _ocr_profile()
    fmt = output_format or _output_format()
    default_tokens = _profile_defaults(profile)["max_tokens"]
    tokens = int(max_tokens or os.getenv("OCR_MAX_TOKENS", str(default_tokens)) or default_tokens)
    if meta is not None:
        meta["json_retry"] = False

    if fmt != "json":
        res = await _vision_chat(_build_ocr_prompt(fmt, profile), png, tokens)
        text = (res.text or "").strip()
        if not text:
            raise APIError(ErrCode.AI_003, "视觉 OCR 本页未返回文字")
        return text

    # 兼容旧行为：强制 JSON，解析失败时用纯文本提示重试一次（语义覆盖与 JSON 版一致）。
    res = await _vision_chat(OCR_TEXT_PROMPT, png, tokens)
    try:
        data = extract_json(res.text)
        text = (data.get("text") or "").strip() if isinstance(data, dict) else ""
    except APIError:
        text = ""
    if text:
        return text
    if meta is not None:
        meta["json_retry"] = True
    _log.warning("扫描页 OCR 的 JSON 输出不可用，改用纯文本转录重试")
    res2 = await _vision_chat(OCR_RAW_PROMPT, png, tokens)
    text = (res2.text or "").strip()
    if not text:
        raise APIError(ErrCode.AI_003, "视觉 OCR 本页未返回文字")
    return text


async def ocr_pdf_to_pages(path: str, *, document_id=None, dpi: int | None = None,
                           on_progress=None, stats: dict | None = None) -> list[tuple[int, str]]:
    """扫描件兜底：逐页渲染 → 并发视觉 OCR → 返回 [(页码, 文本)]。

    与文字层 PDF 返回同构，直接复用 chunk_pages 分块链路。
    部分页失败：记 WARNING 日志（带 document_id）。若 OCR_FAILED_PAGE_RETRY 开启，
    先对失败页串行纯文本重试 1 次（提高 max_tokens），仍失败才跳过；其余照常入库。
    全部失败 / 空 PDF / 渲染失败：抛 APIError，由上层写入 task.error_message，禁止静默。
    stats 为可选出参，把失败页码与每页观测指标带回 task.result（不新增 API 契约字段）。
    """
    dpi = int(dpi or os.getenv("OCR_DPI", "140") or 140)
    profile = _ocr_profile()
    defaults = _profile_defaults(profile)
    jpeg_quality = int(os.getenv("OCR_JPEG_QUALITY", str(defaults["jpeg_quality"]))
                       or defaults["jpeg_quality"])
    try:
        pages_bytes = render_pages(path, dpi=dpi, jpeg_quality=jpeg_quality)
    except Exception as e:
        raise APIError(ErrCode.PARSE_001,
                       f"扫描件 OCR 渲染失败（document_id={document_id}）：{e}") from e
    total = len(pages_bytes)
    if total == 0:
        raise APIError(ErrCode.PARSE_002,
                       f"PDF 为空（0 页），无法进行视觉 OCR（document_id={document_id}）")
    ctx = f"document_id={document_id}"

    fmt = _output_format()
    prompt = _build_ocr_prompt(fmt, profile)
    cache_enabled = _ocr_bool("OCR_CACHE_ENABLED", True)
    observability = _ocr_bool("OCR_OBSERVABILITY", True)
    formula_check_enabled = _ocr_bool("OCR_FORMULA_CHECK", defaults["formula_check"])
    retry_enabled = _ocr_bool("OCR_FAILED_PAGE_RETRY", defaults["retry"])
    if cache_enabled:
        with open(path, "rb") as f:
            content_hash = hashlib.sha256(f.read()).hexdigest()
    else:
        content_hash = ""
    cache_hits = 0

    async def _one(idx: int, png: bytes):
        nonlocal cache_hits
        page_no = idx + 1
        t0 = time.perf_counter()
        meta: dict = {}
        cache_key = (_page_cache_key(content_hash, page_no, dpi, png, prompt, profile)
                     if cache_enabled else None)
        if cache_key and cache_key in _OCR_CACHE:
            cache_hits += 1
            return page_no, _OCR_CACHE[cache_key], {
                "seconds": 0.0, "json_retry": False, "formula_suspect": False, "cached": True,
            }

        text = None
        try:
            text = await ocr_page_text(png, output_format=fmt, meta=meta)
        except Exception as e:  # noqa: BLE001 单页失败不能拖垮整份资料
            _log.warning("扫描件 OCR 单页失败（%s，page=%s/%s）：%s", ctx, page_no, total, e)
            if retry_enabled:
                # 28 号 Q11：失败页串行重试 1 次，强制纯文本并放宽 max_tokens
                retry_tokens = max(int(os.getenv("OCR_MAX_TOKENS", "16000") or 16000),
                                   defaults["max_tokens"])
                _log.warning("扫描件 OCR 失败页串行重试（%s，page=%s/%s，max_tokens=%s）",
                             ctx, page_no, total, retry_tokens)
                try:
                    text = await ocr_page_text(png, max_tokens=retry_tokens,
                                               output_format="plain")
                except Exception as e2:  # noqa: BLE001 重试仍失败才跳过该页
                    _log.warning("扫描件 OCR 失败页重试后仍失败（%s，page=%s/%s）：%s",
                                 ctx, page_no, total, e2)

        seconds = time.perf_counter() - t0
        if text is None:
            return page_no, None, {"seconds": seconds, "json_retry": bool(meta.get("json_retry")),
                                   "formula_suspect": False, "cached": False}
        if cache_key:
            if len(_OCR_CACHE) >= _OCR_CACHE_MAX:
                _OCR_CACHE.clear()
            _OCR_CACHE[cache_key] = text
        suspect = bool(formula_check_enabled and check_formula_balance(text)["suspect"])
        return page_no, text, {
            "seconds": seconds, "json_retry": bool(meta.get("json_retry")),
            "formula_suspect": suspect, "cached": False,
        }

    # 并发全部提交，由 _ocr_sem 把同时在途的请求压到上限（默认 2），避免 429。
    results = await asyncio.gather(*[_one(i, png) for i, png in enumerate(pages_bytes)])
    pages: list[tuple[int, str]] = []
    failed_pages: list[int] = []
    page_chars: list[int] = []
    page_formula_counts: list[int] = []
    page_seconds: list[float] = []
    json_retry_pages: list[int] = []
    formula_suspect_pages: list[int] = []
    for page_no, text, info in sorted(results, key=lambda x: x[0]):
        if text is None:
            failed_pages.append(page_no)
            continue
        pages.append((page_no, text))
        # 以下指标按成功页顺序排列（下标与 pages 对齐，失败页不入列）
        page_chars.append(len(text))
        page_formula_counts.append(text.count("$") // 2)
        page_seconds.append(round(float(info.get("seconds") or 0.0), 3))
        if info.get("json_retry"):
            json_retry_pages.append(page_no)
        if info.get("formula_suspect"):
            formula_suspect_pages.append(page_no)
        if on_progress:
            on_progress(int(40 + 55 * len(pages) / total))

    if stats is not None:
        stats.update({
            "parse_mode": "ocr",
            "ocr_pages_total": total,
            "ocr_pages_ok": len(pages),
            "ocr_failed_pages": failed_pages,
        })
        if observability:
            # 最小可观测 4 项（28 号 §6），全部落在既有 stats，不改 API 契约
            stats.update({
                "ocr_json_retry_pages": json_retry_pages,
                "ocr_page_chars": page_chars,
                "ocr_page_formula_count": page_formula_counts,
                "ocr_page_seconds": page_seconds,
            })
        if formula_check_enabled:
            stats["ocr_formula_suspect_pages"] = formula_suspect_pages
        if cache_enabled:
            stats["ocr_cache_hits"] = cache_hits
    if not pages:
        raise APIError(ErrCode.PARSE_003,
                       f"视觉 OCR 全部失败（{len(failed_pages)}/{total} 页，{ctx}），请检查模型/密钥或稍后重试")
    if failed_pages:
        _log.warning("扫描件 OCR 部分页失败（%s）：成功 %s/%s 页，失败页码 %s 已从知识库跳过",
                     ctx, len(pages), total, failed_pages)
    _log.info("扫描件 OCR 完成（%s）：成功 %s/%s 页，失败 %s 页，缓存命中 %s 页",
              ctx, len(pages), total, len(failed_pages), cache_hits)
    return pages
