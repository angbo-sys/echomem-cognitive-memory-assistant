"""Run baseline evaluation for A/B/C/Proposed over JSONL data."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from agent import Orchestrator
from agent.tools import EmotionAnalyzer, MemorySearch
from memory import LongTermMemory, ShortTermMemory

try:
    from .metrics import aggregate_metrics
except ImportError:
    from metrics import aggregate_metrics

Record = Dict[str, Any]


# -----------------------------
# Baseline execution placeholders
# -----------------------------


class _DeterministicEvalLLM:
    def generate(self, prompt: str, **kwargs: Any) -> str:
        if "焦虑" in prompt or "怕" in prompt or "anxious" in prompt:
            return "我会先稳住节奏，再给你一个可执行的下一步建议。"
        if "计划" in prompt or "目标" in prompt:
            return "下面按目标拆成几个小步骤，优先处理最关键的任务。"
        return "我会结合已检索到的记忆，给出简洁且可执行的建议。"


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _infer_preference(query: str, hits: List[Dict[str, Any]]) -> str:
    joined = " ".join([query, *(str(h.get("content", "")) for h in hits)]).lower()
    if any(token in joined for token in ("简洁", "concise", "直接")):
        return "concise"
    if any(token in joined for token in ("步骤", "计划", "practical", "可执行")):
        return "practical"
    return "balanced"


def _infer_alignment_label(query: str, emotion_label: str) -> str:
    text = query.lower()
    if emotion_label in {"anxious", "frustrated", "discouraged", "confused", "tired"}:
        return "supportive"
    if any(token in text for token in ("计划", "plan", "复习", "学习")):
        return "practical"
    return "balanced"


def _infer_persona_traits(preference: str, alignment: str) -> List[str]:
    traits = ["helpful"]
    if preference in {"concise", "practical", "balanced"}:
        traits.append(preference)
    if alignment == "supportive":
        traits.append("empathetic")
    return list(dict.fromkeys(traits))

def baseline_a(record: Record) -> Record:
    """Baseline A: keyword retrieval rule."""
    out = dict(record)
    memory_bank = record.get("memory_bank") or []
    query = (record.get("query") or "").lower()

    scored = []
    for mem in memory_bank:
        text = str(mem.get("text", ""))
        score = sum(1 for tok in query.split() if tok and tok in text.lower())
        scored.append((score, mem.get("id")))
    scored.sort(reverse=True)

    out["retrieved_ids"] = [m_id for _, m_id in scored if m_id is not None]
    out["response"] = "I understand your request and will help with the most relevant memories."
    out["pred_preference"] = "neutral"
    out["pred_emotion"] = "neutral"
    out["pred_persona_traits"] = ["helpful"]
    out["prompt_tokens"] = 80
    out["completion_tokens"] = 30
    return out


def baseline_b(record: Record) -> Record:
    """Baseline B: recency-first retrieval rule."""
    out = dict(record)
    memory_bank = record.get("memory_bank") or []

    sorted_mem = sorted(memory_bank, key=lambda x: x.get("timestamp", ""), reverse=True)
    out["retrieved_ids"] = [m.get("id") for m in sorted_mem if m.get("id") is not None]
    out["response"] = "Based on your latest context, here is a concise and practical suggestion."
    out["pred_preference"] = "practical"
    out["pred_emotion"] = "calm"
    out["pred_persona_traits"] = ["concise", "practical"]
    out["prompt_tokens"] = 95
    out["completion_tokens"] = 35
    return out


def baseline_c(record: Record) -> Record:
    """Baseline C: hybrid simple scoring."""
    out = dict(record)
    memory_bank = record.get("memory_bank") or []
    query = (record.get("query") or "").lower()

    scored = []
    for mem in memory_bank:
        text = str(mem.get("text", ""))
        ts = mem.get("timestamp", "")
        kw = sum(1 for tok in query.split() if tok and tok in text.lower())
        recency_bonus = 1 if ts else 0
        scored.append((kw + recency_bonus, mem.get("id")))
    scored.sort(reverse=True)

    out["retrieved_ids"] = [m_id for _, m_id in scored if m_id is not None]
    out["response"] = "I combined relevant and recent details to keep this answer consistent."
    out["pred_preference"] = "balanced"
    out["pred_emotion"] = "supportive"
    out["pred_persona_traits"] = ["helpful", "balanced"]
    out["prompt_tokens"] = 110
    out["completion_tokens"] = 45
    return out


def proposed(record: Record) -> Record:
    """Proposed: run the local EchoMem retrieval/emotion/orchestration path."""
    out = dict(record)
    query = str(record.get("query") or "")
    memory_bank = record.get("memory_bank") or []
    user_id = str(record.get("user_id") or "eval_user")

    with tempfile.TemporaryDirectory() as tmp:
        ltm = LongTermMemory(db_path=f"{tmp}/memory.db")
        for mem in memory_bank:
            if not isinstance(mem, dict):
                continue
            text = str(mem.get("text") or mem.get("content") or "").strip()
            if not text:
                continue
            ltm.add_memory(
                content=text,
                mtype=str(mem.get("type") or "fact"),
                importance=float(mem.get("importance") or 0.8),
                source="eval",
                ts=mem.get("timestamp"),
                memory_id=str(mem.get("id")) if mem.get("id") is not None else None,
                user_id=user_id,
            )
        memory_tool = MemorySearch(ltm=ltm, top_k=int(record.get("top_k") or 5))
        emotion_tool = EmotionAnalyzer()
        orch = Orchestrator(
            stm=ShortTermMemory(max_turns=4),
            profile=None,
            emotion_tool=emotion_tool,
            memory_tool=memory_tool,
            llm=_DeterministicEvalLLM(),
        )
        result = orch.run(
            query,
            user_id=user_id,
            extra_context={"enable_mimo_analysis": False, "max_completion_tokens": 160},
        )

    retrieval = result.get("retrieval", {}) if isinstance(result, dict) else {}
    hits = retrieval.get("hits", []) if isinstance(retrieval, dict) and isinstance(retrieval.get("hits"), list) else []
    emotion = result.get("emotion", {}) if isinstance(result, dict) and isinstance(result.get("emotion"), dict) else {}
    response = str(result.get("response", "")) if isinstance(result, dict) else ""
    prompt = str(result.get("prompt", "")) if isinstance(result, dict) else ""
    preference = _infer_preference(query, hits)
    alignment = _infer_alignment_label(query, str(emotion.get("label") or "neutral"))

    out["retrieved_ids"] = [h.get("id") for h in hits if isinstance(h, dict) and h.get("id") is not None]
    out["response"] = response
    out["pred_preference"] = preference
    out["pred_emotion"] = alignment
    out["pred_persona_traits"] = _infer_persona_traits(preference, alignment)
    out["prompt_tokens"] = _estimate_tokens(prompt)
    out["completion_tokens"] = _estimate_tokens(response)
    return out


BASELINES: Dict[str, Callable[[Record], Record]] = {
    "A": baseline_a,
    "B": baseline_b,
    "C": baseline_c,
    "Proposed": proposed,
}


# -----------------------------
# I/O and evaluation
# -----------------------------

def read_jsonl(path: Path) -> List[Record]:
    rows: List[Record] = []
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            s = line.strip()
            if not s:
                continue
            try:
                rows.append(json.loads(s))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at line {idx}: {e}") from e
    return rows


def run_one(name: str, fn: Callable[[Record], Record], rows: List[Record], recall_k: int, price_per_1k: float) -> Dict[str, Any]:
    processed = [fn(r) for r in rows]
    metrics = aggregate_metrics(processed, recall_k=recall_k, unit_price_per_1k_tokens=price_per_1k)
    metrics["baseline"] = name
    metrics["num_samples"] = len(processed)
    return metrics


def print_metrics_table(results: List[Dict[str, Any]]) -> None:
    headers = [
        "baseline",
        "num_samples",
        "recall_at_k",
        "preference_accuracy",
        "persona_consistency",
        "emotional_alignment",
        "response_coherence",
        "total_tokens",
        "avg_tokens_per_sample",
    ]

    def fmt(v: Any) -> str:
        if isinstance(v, float):
            return f"{v:.4f}"
        return str(v)

    widths = {h: max(len(h), *(len(fmt(r.get(h, ""))) for r in results)) for h in headers}

    head = " | ".join(h.ljust(widths[h]) for h in headers)
    sep = "-+-".join("-" * widths[h] for h in headers)
    print(head)
    print(sep)
    for r in results:
        print(" | ".join(fmt(r.get(h, "")).ljust(widths[h]) for h in headers))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run baseline experiments over a JSONL file.")
    p.add_argument("--data", type=Path, required=True, help="Path to JSONL evaluation data.")
    p.add_argument(
        "--baselines",
        nargs="+",
        default=["A", "B", "C", "Proposed"],
        help="Baselines to run. Options: A B C Proposed",
    )
    p.add_argument("--recall-k", type=int, default=5, help="K used in Recall@K.")
    p.add_argument("--price-per-1k", type=float, default=0.0, help="Optional token price per 1k tokens.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.data)

    selected = []
    for name in args.baselines:
        if name not in BASELINES:
            raise ValueError(f"Unknown baseline '{name}'. Valid: {', '.join(BASELINES.keys())}")
        selected.append(name)

    results = [run_one(name, BASELINES[name], rows, recall_k=args.recall_k, price_per_1k=args.price_per_1k) for name in selected]
    print_metrics_table(results)


if __name__ == "__main__":
    main()
