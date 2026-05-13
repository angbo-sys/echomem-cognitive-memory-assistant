from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class EvolutionDecision:
    conflict: bool
    old_status: str
    old_importance_multiplier: float
    reason: str


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def is_conflict(old_value: Any, new_value: Any) -> bool:
    """
    Rule-based conflict check:
    values are considered conflicting when both are non-empty and unequal after normalization.
    """
    old_norm = _normalize_value(old_value)
    new_norm = _normalize_value(new_value)
    if not old_norm or not new_norm:
        return False
    return old_norm != new_norm


def decay_importance(importance: float, multiplier: float = 0.3, floor: float = 0.0) -> float:
    decayed = float(importance) * float(multiplier)
    return max(float(floor), decayed)


def build_evolution_decision(old_value: Any, new_value: Any) -> EvolutionDecision:
    if is_conflict(old_value=old_value, new_value=new_value):
        return EvolutionDecision(
            conflict=True,
            old_status="deprecated",
            old_importance_multiplier=0.3,
            reason="value_conflict",
        )
    return EvolutionDecision(
        conflict=False,
        old_status="active",
        old_importance_multiplier=1.0,
        reason="no_conflict",
    )
