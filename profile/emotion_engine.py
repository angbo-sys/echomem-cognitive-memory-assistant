from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


EmotionLabel = str
EmotionClassifier = Callable[[str], EmotionLabel]


@dataclass(frozen=True)
class EmotionResult:
    label: EmotionLabel
    confidence: float
    source: str


class EmotionEngine:
    """Emotion classification with rule-based keywords and pluggable LLM hook."""

    _SUPPORTED_LABELS: set[EmotionLabel] = {
        "positive",
        "neutral",
        "anxious",
        "frustrated",
        "confident",
        "confused",
        "tired",
        "discouraged",
        "curious",
    }

    _KEYWORDS: dict[EmotionLabel, set[str]] = {
        "anxious": {
            "worry",
            "worried",
            "anxious",
            "nervous",
            "panic",
            "afraid",
            "uneasy",
            "concerned",
            "stress",
            "stressed",
            "焦虑",
            "担心",
            "紧张",
            "害怕",
            "不安",
            "心慌",
            "忐忑",
            "惶恐",
        },
        "frustrated": {
            "frustrated",
            "annoyed",
            "angry",
            "mad",
            "irritated",
            "upset",
            "tired of",
            "fed up",
            "失败",
            "烦",
            "生气",
            "崩溃",
            "愤怒",
            "恼火",
            "受不了",
            "无语",
        },
        "confident": {
            "confident",
            "certain",
            "sure",
            "prepared",
            "ready",
            "can do",
            "handled",
            "没问题",
            "有把握",
            "稳",
            "有信心",
            "确信",
            "肯定",
            "拿手",
        },
        "positive": {
            "happy",
            "great",
            "good",
            "excited",
            "glad",
            "awesome",
            "wonderful",
            "love",
            "开心",
            "高兴",
            "满意",
            "期待",
            "棒",
            "赞",
            "喜欢",
            "享受",
            "美好",
        },
        "confused": {
            "confused",
            "unclear",
            "lost",
            "puzzled",
            "困惑",
            "不懂",
            "不明白",
            "不理解",
            "糊涂",
            "迷茫",
            "费解",
            "搞不懂",
            "晕",
        },
        "tired": {
            "tired",
            "exhausted",
            "drained",
            "累",
            "疲惫",
            "疲劳",
            "没精力",
            "困",
            "无力",
            "精疲力尽",
            "乏",
            "没劲",
        },
        "discouraged": {
            "discouraged",
            "hopeless",
            "demotivated",
            "放弃",
            "没信心",
            "灰心",
            "失望",
            "沮丧",
            "气馁",
            "泄气",
            "绝望",
            "低落",
        },
        "curious": {
            "curious",
            "interested",
            "fascinated",
            "好奇",
            "想了解",
            "想知道",
            "感兴趣",
            "探索",
            "求知",
            "新鲜",
            "有趣",
        },
    }

    def __init__(self, llm_classifier: EmotionClassifier | None = None) -> None:
        self._llm_classifier = llm_classifier

    def classify(self, text: str, prefer_llm: bool = False) -> EmotionResult:
        if not isinstance(text, str) or not text.strip():
            return EmotionResult(label="neutral", confidence=0.5, source="rule")

        if prefer_llm and self._llm_classifier is not None:
            llm_label = self._llm_classifier(text)
            self._validate_label(llm_label, source="llm")
            return EmotionResult(label=llm_label, confidence=0.85, source="llm")

        rule_result = self._classify_by_rules(text)
        if rule_result is not None:
            return rule_result

        if self._llm_classifier is not None:
            llm_label = self._llm_classifier(text)
            self._validate_label(llm_label, source="llm")
            return EmotionResult(label=llm_label, confidence=0.75, source="llm")

        return EmotionResult(label="neutral", confidence=0.5, source="rule")

    def set_llm_classifier(self, classifier: EmotionClassifier | None) -> None:
        self._llm_classifier = classifier

    def _classify_by_rules(self, text: str) -> EmotionResult | None:
        normalized = text.lower()
        scores: dict[EmotionLabel, int] = {label: 0 for label in self._KEYWORDS}

        for label, keywords in self._KEYWORDS.items():
            for keyword in keywords:
                if keyword in normalized:
                    scores[label] += 1

        best_label = max(scores, key=scores.get)
        best_score = scores[best_label]
        if best_score <= 0:
            return None

        confidence = min(0.6 + best_score * 0.1, 0.95)
        return EmotionResult(label=best_label, confidence=confidence, source="rule")

    def _validate_label(self, label: EmotionLabel, source: str) -> None:
        if label not in self._SUPPORTED_LABELS:
            raise ValueError(
                f"Unsupported emotion label from {source}: '{label}'. "
                f"Expected one of: {sorted(self._SUPPORTED_LABELS)}"
            )
