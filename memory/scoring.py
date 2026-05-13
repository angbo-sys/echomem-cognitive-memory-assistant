from __future__ import annotations

import math


def decayed_score(similarity: float, importance: float, t_days: float, decay_lambda: float = 0.05) -> float:
    """
    Score = Similarity * Importance * exp(-lambda * t_days)
    """
    if t_days < 0:
        t_days = 0.0
    if decay_lambda < 0:
        raise ValueError("decay_lambda must be >= 0")
    return float(similarity) * float(importance) * math.exp(-decay_lambda * float(t_days))

