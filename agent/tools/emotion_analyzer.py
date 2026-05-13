"""Emotion analyzer tool aligned with project emotion taxonomy."""

from __future__ import annotations

from typing import Any, Dict

from profile import EmotionEngine


_LLM_EMOTION_PROMPT = """You are an emotion classifier. Analyze the user's message and return exactly one emotion label from the following list:

{labels}

Rules:
- Return ONLY the label, no additional text or punctuation.
- Base your analysis on the tone, word choice, and context of the message.
- If the message is neutral or mixed, return "neutral".
- For Chinese text, pay attention to emotional cues in both the characters and phrasing.

Message: {text}

Label:"""


class EmotionAnalyzer:
    """Emotion analyzer returning project-defined labels."""

    def __init__(
        self, engine: EmotionEngine | None = None, llm: Any = None
    ) -> None:
        self.engine = engine or EmotionEngine()
        if llm is not None:
            labels = sorted(EmotionEngine._SUPPORTED_LABELS)
            classifier = lambda text: llm.generate(
                _LLM_EMOTION_PROMPT.format(labels=labels, text=text)
            )
            self.engine.set_llm_classifier(classifier)
            self._llm_available = True
        else:
            self._llm_available = False

    def run(self, text: str = "", **_: Any) -> Dict[str, Any]:
        result = self.engine.classify(text or "neutral", prefer_llm=self._llm_available)
        return {
            "tool": "emotion_analyzer",
            "label": result.label,
            "confidence": result.confidence,
            "source": result.source,
            "text": result.label,
        }
