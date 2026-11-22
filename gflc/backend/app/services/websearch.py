# -*- coding: utf-8 -*-
"""免 Key 联网搜索：Bing HTML/RSS 为主引擎（本机实测 DuckDuckGo 不可达），DDG 作后备。
只依赖 httpx + 标准库；任何异常都吞掉返回 []，绝不把接口打挂。"""
import base64
import html as _html
import json
import re
import time
from urllib.parse import parse_qs, urlparse

import httpx

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_HEADERS = {"User-Agent": _UA, "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
_TIMEOUT = 6.0          # 单引擎超时
_TTL = 600             # 同一 query 10 分钟内复用
_COOLDOWN = 600        # 引擎连续失败后静默 10 分钟，避免拖慢接口
_CACHE: dict[str, tuple[float, list[dict]]] = {}
_DEAD: dict[str, float] = {}
_CACHE_MAX = 200

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")


def _clean(text: str) -> str:
    """去标签、反转义、压空白。"""
    if not text:
        return ""
    text = re.sub(r"(?is)<(script|style).*?</\1>", " ", text)
    text = _html.unescape(_TAG.sub(" ", text)).replace("\u00a0", " ")
    return _WS.sub(" ", text).strip()


def _unwrap(url: str) -> str:
    """还原 DDG/Bing 的跳转链接。"""
    if not url:
        return ""
    if url.startswith("//"):
        url = "https:" + url
    if "duckduckgo.com/l/" in url or "bing.com/ck/a" in url:
        qs = parse_qs(urlparse(url).query)
        for key in ("uddg", "u"):
            val = (qs.get(key) or [""])[0]
            if val.startswith("http"):
                return val
            if key == "u" and val.startswith("a1"):  # Bing: a1 + base64(url)
                try:
                    raw = val[2:]
                    dec = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)).decode("utf-8", "ignore")
                    if dec.startswith("http"):
                        return dec
                except Exception:
                    pass
    return url


def _fetch(url: str, params: dict | None = None, data: dict | None = None) -> str:
    with httpx.Client(timeout=_TIMEOUT, follow_redirects=True, headers=_HEADERS) as c:
        r = c.post(url, data=data) if data is not None else c.get(url, params=params)
    return r.text if r.status_code == 200 else ""


def _bing(query: str) -> list[dict]:
    body = _fetch("https://www.bing.com/search", params={"q": query})
    out = []
    for block in re.findall(r'(?is)<li class="b_algo".*?</li>', body):
        m = re.search(r'(?is)<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block)
        if not m:
            continue
        url = _unwrap(m.group(1))
        if not url.startswith("http"):
            continue
        s = re.search(r"(?is)<p[^>]*>(.*?)</p>", block)
        out.append({"title": _clean(m.group(2)), "url": url,
                    "snippet": _clean(s.group(1)) if s else ""})
    return out


def _bing_rss(query: str) -> list[dict]:
    body = _fetch("https://www.bing.com/search", params={"q": query, "format": "rss"})
    out = []
    for item in re.findall(r"(?is)<item>(.*?)</item>", body):
        t = re.search(r"(?is)<title>(.*?)</title>", item)
        l = re.search(r"(?is)<link>(.*?)</link>", item)
        d = re.search(r"(?is)<description>(.*?)</description>", item)
        if not (t and l):
            continue
        out.append({"title": _clean(t.group(1)), "url": _clean(l.group(1)),
                    "snippet": _clean(d.group(1)) if d else ""})
    return out


def _ddg_html(query: str) -> list[dict]:
    body = _fetch("https://html.duckduckgo.com/html/", data={"q": query})
    out = []
    for m in re.finditer(r'(?is)<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body):
        tail = body[m.end():m.end() + 1200]
        s = re.search(r'(?is)class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', tail)
        out.append({"title": _clean(m.group(2)), "url": _unwrap(m.group(1)),
                    "snippet": _clean(s.group(1)) if s else ""})
    return out


def _ddg_lite(query: str) -> list[dict]:
    body = _fetch("https://lite.duckduckgo.com/lite/", data={"q": query})
    rows = re.findall(r'(?is)<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', body)
    snips = re.findall(r'(?is)<td[^>]+class="result-snippet"[^>]*>(.*?)</td>', body)
    return [{"title": _clean(title), "url": _unwrap(url),
             "snippet": _clean(snips[i]) if i < len(snips) else ""}
            for i, (url, title) in enumerate(rows)]


def _ddg_api(query: str) -> list[dict]:
    raw = _fetch("https://api.duckduckgo.com/", params={"q": query, "format": "json", "no_html": 1})
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except Exception:
        return []
    out: list[dict] = []
    if data.get("AbstractURL"):
        out.append({"title": _clean(data.get("Heading", "")) or query,
                    "url": data["AbstractURL"], "snippet": _clean(data.get("AbstractText", ""))})

    def walk(items):
        for it in items or []:
            if not isinstance(it, dict):
                continue
            if it.get("FirstURL"):
                out.append({"title": _clean(it.get("Text", ""))[:120],
                            "url": it["FirstURL"], "snippet": _clean(it.get("Text", ""))})
            elif it.get("Topics"):
                walk(it["Topics"])

    walk(data.get("RelatedTopics"))
    return out


# 顺序即优先级：Bing 在国内可用且稳定，DDG 在后备
_ENGINES = (_bing, _bing_rss, _ddg_html, _ddg_lite, _ddg_api)


def search(query: str, top_k: int = 5) -> list[dict]:
    """返回 [{"title","url","snippet"}]；全部失败返回 []。"""
    query = (query or "").strip()
    if not query:
        return []
    key = query.lower()
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < _TTL:
        return cached[1][:top_k]

    raw_results: list[dict] = []
    for engine in _ENGINES:
        name = engine.__name__
        if time.time() < _DEAD.get(name, 0):
            continue
        try:
            got = engine(query)
        except Exception:
            got = []
        if got:
            raw_results = got
            break
        _DEAD[name] = time.time() + _COOLDOWN

    results: list[dict] = []
    seen: set[str] = set()
    for r in raw_results:
        url = r.get("url", "")
        if not url.startswith("http") or not r.get("title") or url in seen:
            continue
        seen.add(url)
        results.append({"title": r["title"][:200], "url": url,
                        "snippet": (r.get("snippet") or "")[:500]})
        if len(results) >= max(top_k, 1):
            break

    if len(_CACHE) > _CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = (time.time(), results)
    return results
