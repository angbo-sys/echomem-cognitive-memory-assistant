from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .scoring import decayed_score


_STOPWORDS = frozenset({
    "用户", "偏好", "目标", "学习", "回答", "喜欢", "需要", "the", "and", "user",
    "一个", "可以", "这个", "那个", "什么", "怎么", "如何", "请", "帮", "我",
})


def _ngram_tokenize(text: str, min_n: int = 2, max_n: int = 4) -> List[str]:
    normalized = re.sub(r"[^\w一-鿿]+", " ", text.lower())
    tokens: List[str] = []
    for word in normalized.split():
        if len(word) >= 2:
            tokens.append(word)
        if re.fullmatch(r"[一-鿿]+", word) and len(word) > 1:
            for size in range(min_n, min(max_n, len(word)) + 1):
                for idx in range(len(word) - size + 1):
                    tokens.append(word[idx : idx + size])
    return [token for token in tokens if token not in _STOPWORDS]


def _bm25_like_score(query_tokens: List[str], doc_tokens: List[str]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    counts = Counter(doc_tokens)
    doc_len = max(len(doc_tokens), 1)
    avg_doc_len = doc_len
    score = 0.0
    k1 = 1.5
    b = 0.75
    for token in query_tokens:
        tf = counts.get(token, 0)
        if tf <= 0:
            continue
        idf = math.log(1.0 + 1.0 / (tf + 0.5))
        denom = tf + k1 * (1 - b + b * doc_len / avg_doc_len)
        score += idf * (tf * (k1 + 1)) / denom
    return score


def lexical_similarity(query: str, content: str) -> float:
    """
    Chinese-friendly lexical similarity using N-grams plus a BM25-like signal.
    """
    query_tokens = _ngram_tokenize(query)
    doc_tokens = _ngram_tokenize(content)
    if not query_tokens or not doc_tokens:
        return 0.0
    query_set = set(query_tokens)
    doc_set = set(doc_tokens)
    jaccard = len(query_set & doc_set) / len(query_set | doc_set)
    bm25 = _bm25_like_score(query_tokens, doc_tokens)
    return min(1.0, (0.45 * jaccard) + (0.55 * (bm25 / (bm25 + 3.0))))


def _age_days(ts_iso: str, now: Optional[datetime] = None) -> float:
    now = now or datetime.now(timezone.utc)
    dt = datetime.fromisoformat(ts_iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt.astimezone(timezone.utc)
    return max(delta.total_seconds() / 86400.0, 0.0)


def rerank_top_k(
    query: str,
    candidates: Iterable[Dict[str, Any]],
    top_k: int = 5,
    decay_lambda: float = 0.05,
) -> List[Dict[str, Any]]:
    """
    Re-rank candidate memories and output similarity/importance/decayed_score.
    """
    if top_k <= 0:
        return []

    scored: List[Dict[str, Any]] = []
    for item in candidates:
        content = str(item.get("content", ""))
        importance = float(item.get("importance", 1.0))
        ts = item.get("ts")
        if not ts:
            continue
        try:
            t_days = _age_days(str(ts))
        except (TypeError, ValueError):
            continue
        similarity = lexical_similarity(query, content)
        score = decayed_score(similarity=similarity, importance=importance, t_days=t_days, decay_lambda=decay_lambda)

        merged = dict(item)
        merged["similarity"] = similarity
        merged["importance"] = importance
        merged["decayed_score"] = score
        scored.append(merged)

    scored.sort(key=lambda x: x["decayed_score"], reverse=True)
    return scored[:top_k]
