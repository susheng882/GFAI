# -*- coding: utf-8 -*-
"""V3/N5 离线评测引擎（零外部依赖，仅标准库）。

设计要点：
  - 不联网、不调用任何 LLM 付费接口；检索用纯 Python 的 BM25 式词频/IDF 打分。
  - 中文分词采用「汉字二元组 + 连续 ASCII 词」的确定性方案，不依赖 jieba。
  - 语义问法通过本地同义词扩展表（EXPANSIONS）兑现，例如「记住公式」扩展到「推导过程」。
  - 六项指标：召回率 / 命中率 / MRR / 忠实度 / 拒答准确率 / 卡片可用率，均以 0–100 的
    百分比口径输出，便于 eval_gate.py 直接按「百分点（pp）」比较。

指标口径（离线可复现代理指标）：
  召回率      非诱饵题：命中期望 chunk 数 / 期望 chunk 总数，取平均。
  命中率      非诱饵题：top-K 中至少命中 1 个期望 chunk 的题占比。
  MRR         非诱饵题：第一个期望 chunk 排名倒数的平均。
  忠实度      非诱饵题：答案要点在被引证据块（top-K）中得到文本支撑的比例（证据可证实率）。
  拒答准确率  全量题：诱饵题正确拒答 + 非诱饵题正确作答 的占比。
  卡片可用率  非诱饵题：能用检索证据生成「问题 + 答案要点 + 来源」完整卡片的比例。
"""
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

# 本地语义扩展：仅在离线评测中用于把语义问法映射到语料用词，属于确定性规则，不是模型调用。
EXPANSIONS = {
    "记住": ["记忆", "理解", "推导", "背诵"],
    "记不牢": ["推导", "理解", "遗忘"],
    "记不住": ["推导", "理解", "遗忘"],
    "死记硬背": ["推导过程", "理解记忆", "配方"],
    "公式": ["推导", "求根公式", "求和公式"],
    "加深理解": ["费曼", "以教促学", "主动回忆", "复述"],
    "忘": ["遗忘", "间隔重复", "复习"],
    "办法": ["方法", "技巧", "法"],
}

# 疑问词/量词二元组：本身不承载知识点，若参与打分会把诱饵题误判为可作答。
STOP_TOKENS = {
    "怎么", "什么", "多少", "是多", "现在", "一张", "不是", "这个", "那个",
    "如何", "哪些", "几个", "哪个", "可以", "没有", "一个", "我们", "你们",
    "他们", "一样", "这样", "那样", "是否", "还有", "以及", "并且",
}

_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_ASCII_RE = re.compile(r"[a-zA-Z0-9]+")
_SENT_RE = re.compile(r"[^。！？\n]+[。！？]?")


def tokenize(text: str) -> list[str]:
    """汉字二元组 + 连续 ASCII 词，返回去重后的 token 列表。"""
    tokens: set[str] = set()
    for run in _CJK_RE.findall(text):
        if len(run) == 1:
            tokens.add(run)
        else:
            for i in range(len(run) - 1):
                tokens.add(run[i:i + 2])
    for w in _ASCII_RE.findall(text):
        tokens.add(w.lower())
    return sorted(tokens)


def query_tokens(question: str) -> dict[str, float]:
    """原始问题 token（权重 1.0）+ 本地语义扩展 token（权重 0.65）。"""
    qt: dict[str, float] = {}
    for t in tokenize(question):
        if t not in STOP_TOKENS:
            qt[t] = max(qt.get(t, 0.0), 1.0)
    for key, synonyms in EXPANSIONS.items():
        if key in question:
            for syn in synonyms:
                for t in tokenize(syn):
                    if t not in STOP_TOKENS:
                        qt[t] = max(qt.get(t, 0.0), 0.65)
    return qt


def load_corpus(corpus_dir: Path | None = None) -> list[dict]:
    corpus_dir = corpus_dir or (HERE / "corpus")
    chunks: list[dict] = []
    for path in sorted(corpus_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for c in data["chunks"]:
            chunks.append({
                "chunk_id": c["chunk_id"],
                "doc_id": data["id"],
                "source_type": data["source_type"],
                "page": c.get("page"),
                "ts_start": c.get("ts_start"),
                "text": c["text"],
                "tokens": set(tokenize(c["text"])),
            })
    return chunks


def build_idf(chunks: list[dict]) -> dict[str, float]:
    n = len(chunks) or 1
    df: dict[str, int] = {}
    for c in chunks:
        for t in c["tokens"]:
            df[t] = df.get(t, 0) + 1
    return {t: math.log(1.0 + n / (1.0 + freq)) for t, freq in df.items()}


def retrieve(question: str, chunks: list[dict], idf: dict[str, float],
             top_k: int = 5) -> list[tuple[dict, float]]:
    qt = query_tokens(question)
    denom = sum(w * idf.get(t, 1.0) for t, w in qt.items()) or 1.0
    scored = []
    for c in chunks:
        num = sum(w * idf.get(t, 1.0) for t, w in qt.items() if t in c["tokens"])
        if num > 0:
            scored.append((c, round(num / denom, 4)))
    scored.sort(key=lambda x: (-x[1], x[0]["chunk_id"]))
    return scored[:top_k]


def _covered(point: str, evidence: str) -> bool:
    """答案要点是否被证据文本支撑：要点 token 覆盖率 ≥60% 视为支撑。"""
    pts = tokenize(point)
    if not pts:
        return False
    ev = set(tokenize(evidence))
    hit = sum(1 for t in pts if t in ev)
    return hit / len(pts) >= 0.6


def _metadata_complete(chunk: dict) -> bool:
    return bool(chunk.get("chunk_id")) and (chunk.get("page") is not None or chunk.get("ts_start") is not None) \
        and len(chunk.get("text") or "") >= 40


def evaluate(version: str, top_k: int = 5, refusal_threshold: float = 0.12,
             corpus_dir: Path | None = None, questions_path: Path | None = None) -> dict:
    corpus_dir = corpus_dir or (HERE / "corpus")
    questions_path = questions_path or (HERE / "questions.json")
    chunks = load_corpus(corpus_dir)
    idf = build_idf(chunks)
    questions = json.loads(questions_path.read_text(encoding="utf-8"))
    by_id = {c["chunk_id"]: c for c in chunks}

    details = []
    for item in questions:
        ranked = retrieve(item["question"], chunks, idf, top_k=top_k)
        retrieved_ids = [c["chunk_id"] for c, _ in ranked]
        max_score = ranked[0][1] if ranked else 0.0
        qt = query_tokens(item["question"])
        matched = len([t for t in qt if ranked and t in ranked[0][0]["tokens"]])
        # 作答判定：既要分数过线，也要至少 2 个内容词命中（防止单个疑问词误触发）
        should_answer = max_score >= refusal_threshold and matched >= 2
        expected = set(item["expected_chunk_ids"])
        hits = [cid for cid in retrieved_ids if cid in expected]
        is_decoy = bool(item["is_decoy"])

        if is_decoy:
            recall = hit = mrr = faith = card = None
            correct = not should_answer
        else:
            recall = len(hits) / len(expected) if expected else 0.0
            hit = 1.0 if hits else 0.0
            rank = next((i for i, cid in enumerate(retrieved_ids, 1) if cid in expected), None)
            mrr = 1.0 / rank if rank else 0.0
            evidence = "\n".join(c["text"] for c, _ in ranked)
            points = item["expected_answer_points"]
            faith = (sum(1 for p in points if _covered(p, evidence)) / len(points)) if points else 0.0
            usable = [by_id[cid] for cid in hits if cid in by_id and _metadata_complete(by_id[cid])]
            card = 1.0 if (hits and usable and any(_covered(p, evidence) for p in points)) else 0.0
            correct = should_answer

        details.append({
            "id": item["id"],
            "question": item["question"],
            "kind": item["kind"],
            "is_decoy": is_decoy,
            "is_semantic": bool(item.get("is_semantic")),
            "max_score": max_score,
            "matched_tokens": matched,
            "retrieved": retrieved_ids,
            "expected": sorted(expected),
            "hits": hits,
            "decision": "拒答" if max_score < refusal_threshold else "作答",
            "decision_correct": correct,
            "recall": recall, "hit": hit, "mrr": mrr,
            "faithfulness": faith, "card_usability": card,
        })

    def avg(key, decoys=False):
        vals = [d[key] for d in details
                if d[key] is not None and (decoys or not d["is_decoy"])]
        return round(sum(vals) / len(vals) * 100, 2) if vals else 0.0

    non_decoy = [d for d in details if not d["is_decoy"]]
    metrics = {
        "召回率": avg("recall"),
        "命中率": avg("hit"),
        "MRR": avg("mrr"),
        "忠实度": avg("faithfulness"),
        "拒答准确率": round(sum(1 for d in details if d["decision_correct"]) / len(details) * 100, 2),
        "卡片可用率": avg("card_usability"),
    }
    type_count: dict[str, int] = {}
    for path in sorted(corpus_dir.glob("*.json")):
        st = json.loads(path.read_text(encoding="utf-8"))["source_type"]
        type_count[st] = type_count.get(st, 0) + 1

    return {
        "version": version,
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "mode": "offline",
        "config": {"top_k": top_k, "refusal_threshold": refusal_threshold,
                   "expansion_enabled": True, "llm_called": False},
        "corpus": {"documents": len(list(corpus_dir.glob("*.json"))),
                   "by_type": type_count,
                   "questions": len(questions),
                   "decoys": sum(1 for q in questions if q["is_decoy"]),
                   "semantic": sum(1 for q in questions if q.get("is_semantic"))},
        "metrics": metrics,
        "per_question": details,
    }


def write_report(report: dict, out_dir: Path) -> tuple[Path, Path]:
    """写 report.json + report.md 到 reports/<version>/，返回两条路径。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    jpath = out_dir / "report.json"
    mpath = out_dir / "report.md"
    jpath.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    m = report["metrics"]
    c = report["corpus"]
    lines = [
        f"# 评测报告 {report['version']}",
        "",
        f"- 生成时间：{report['generated_at']}",
        f"- 模式：`{report['mode']}`（本地规则计算，`llm_called={report['config']['llm_called']}`）",
        f"- 语料：{c['documents']} 份资料（{c['by_type']}） / {c['questions']} 条问题"
        f"（诱饵 {c['decoys']}、语义问法 {c['semantic']}）",
        f"- 参数：top_k={report['config']['top_k']}，拒答阈值={report['config']['refusal_threshold']}",
        "",
        "## 六项指标（0–100，百分比）",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
    ]
    for k, v in m.items():
        lines.append(f"| {k} | {v:.2f} |")
    lines += [
        "",
        "## 逐题明细",
        "",
        "| ID | 类型 | 判定 | 最高分 | 命中 | 召回 | MRR | 忠实度 | 卡片 |",
        "|---|---|---|---:|---|---:|---:|---:|---:|",
    ]
    for d in report["per_question"]:
        fmt = lambda v: "-" if v is None else f"{v:.2f}"
        lines.append(
            f"| {d['id']} | {d['kind']}{'/语义' if d['is_semantic'] else ''} | "
            f"{d['decision']}{'' if d['decision_correct'] else ' ✘'} | {d['max_score']:.3f} | "
            f"{'/'.join(d['hits']) or '-'} | {fmt(d['recall'])} | {fmt(d['mrr'])} | "
            f"{fmt(d['faithfulness'])} | {fmt(d['card_usability'])} |")
    mpath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return jpath, mpath
