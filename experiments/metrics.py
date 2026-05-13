"""Basic evaluation metrics for baseline experiments.

All metric functions accept a list of records (dict).
Each record can include fields needed by each metric function.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Sequence

Record = Dict[str, Any]


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def recall_at_k(records: Sequence[Record], k: int = 5) -> float:
    """Compute Recall@K.

    Expected per record:
    - "relevant_ids": list[str] or list[int]
    - "retrieved_ids": ranked list[str] or list[int]

    Recall for a record = |relevant ∩ top_k_retrieved| / |relevant|.
    Final metric is mean over records with non-empty relevant set.
    """
    if k <= 0:
        return 0.0

    per_item: List[float] = []
    for r in records:
        relevant = set(r.get("relevant_ids") or [])
        if not relevant:
            continue
        retrieved_top_k = list(r.get("retrieved_ids") or [])[:k]
        hit = len(relevant.intersection(retrieved_top_k))
        per_item.append(_safe_div(hit, len(relevant)))

    return _safe_div(sum(per_item), len(per_item))


def preference_accuracy(records: Sequence[Record]) -> float:
    """Compute preference accuracy.

    Expected per record:
    - "pred_preference": predicted label/string
    - "gold_preference": gold label/string
    """
    total = 0
    correct = 0
    for r in records:
        if "gold_preference" not in r:
            continue
        total += 1
        if r.get("pred_preference") == r.get("gold_preference"):
            correct += 1
    return _safe_div(correct, total)


def persona_consistency(records: Sequence[Record]) -> float:
    """Compute persona consistency as feature overlap F1.

    Expected per record:
    - "pred_persona_traits": list[str]
    - "gold_persona_traits": list[str]

    Per-record score = F1(overlap).
    """
    scores: List[float] = []
    for r in records:
        gold = set(r.get("gold_persona_traits") or [])
        pred = set(r.get("pred_persona_traits") or [])
        if not gold and not pred:
            continue
        overlap = len(gold.intersection(pred))
        precision = _safe_div(overlap, len(pred))
        recall = _safe_div(overlap, len(gold))
        if precision + recall == 0:
            scores.append(0.0)
        else:
            scores.append(2 * precision * recall / (precision + recall))
    return _safe_div(sum(scores), len(scores))


def emotional_alignment(records: Sequence[Record]) -> float:
    """Compute emotional alignment as exact-match accuracy.

    Expected per record:
    - "pred_emotion": predicted emotion label
    - "gold_emotion": gold emotion label
    """
    total = 0
    correct = 0
    for r in records:
        if "gold_emotion" not in r:
            continue
        total += 1
        if r.get("pred_emotion") == r.get("gold_emotion"):
            correct += 1
    return _safe_div(correct, total)


def token_cost(records: Sequence[Record], unit_price_per_1k_tokens: float = 0.0) -> Dict[str, float]:
    """Compute token usage and optional estimated cost.

    Expected per record:
    - "prompt_tokens": int
    - "completion_tokens": int

    Returns:
    - total_prompt_tokens
    - total_completion_tokens
    - total_tokens
    - avg_tokens_per_sample
    - estimated_cost (if unit_price_per_1k_tokens > 0)
    """
    total_prompt = 0
    total_completion = 0

    for r in records:
        total_prompt += int(r.get("prompt_tokens") or 0)
        total_completion += int(r.get("completion_tokens") or 0)

    total_tokens = total_prompt + total_completion
    n = len(records)
    result = {
        "total_prompt_tokens": float(total_prompt),
        "total_completion_tokens": float(total_completion),
        "total_tokens": float(total_tokens),
        "avg_tokens_per_sample": _safe_div(float(total_tokens), float(n)),
    }
    if unit_price_per_1k_tokens > 0:
        result["estimated_cost"] = (total_tokens / 1000.0) * unit_price_per_1k_tokens
    return result


def response_coherence(records: Sequence[Record]) -> float:
    """A lightweight coherence proxy in [0, 1].

    Expected per record:
    - "response": generated text

    Heuristics:
    - non-empty response
    - sentence has terminal punctuation
    - low repeated-line ratio
    """
    scores: List[float] = []
    for r in records:
        text = (r.get("response") or "").strip()
        if not text:
            scores.append(0.0)
            continue

        score = 0.0

        # Has ending punctuation (rough completeness)
        if text.endswith((".", "!", "?", "。", "！", "？")):
            score += 0.4

        # Enough length to carry meaning
        if len(text) >= 20:
            score += 0.3

        # Penalize repeated lines/tokens lightly
        tokens = text.split()
        if tokens:
            unique_ratio = _safe_div(len(set(tokens)), len(tokens))
            score += 0.3 * min(1.0, unique_ratio)

        scores.append(min(1.0, score))

    return _safe_div(sum(scores), len(scores))


def aggregate_metrics(
    records: Sequence[Record],
    recall_k: int = 5,
    unit_price_per_1k_tokens: float = 0.0,
) -> Dict[str, Any]:
    """Compute all baseline metrics as one dict."""
    result: Dict[str, Any] = {
        "recall_at_k": recall_at_k(records, k=recall_k),
        "preference_accuracy": preference_accuracy(records),
        "persona_consistency": persona_consistency(records),
        "emotional_alignment": emotional_alignment(records),
        "response_coherence": response_coherence(records),
    }
    result.update(token_cost(records, unit_price_per_1k_tokens=unit_price_per_1k_tokens))
    return result
