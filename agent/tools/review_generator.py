"""Minimal review generator tool."""

from __future__ import annotations

from typing import Any, Dict, Optional


class ReviewGenerator:
    """Create a short review-style output."""

    def run(
        self,
        user_input: str = "",
        llm_output: Any = None,
        context: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        context = context or {}

        # Extract profile data from context
        weak_subject = context.get("weak_subject", "")
        emotion_state = context.get("emotion_state", "")

        # Parse LLM output — could be a dict (tool result) or plain string
        llm_text = ""
        llm_questions: list[str] = []
        if llm_output is not None:
            if isinstance(llm_output, dict):
                llm_text = str(llm_output.get("text", llm_output.get("content", "")))
                raw = llm_output.get("questions") or []
                llm_questions = [str(q) for q in raw if q]
            else:
                llm_text = str(llm_output)

        # Build review sections
        sections: list[str] = []
        if weak_subject:
            sections.append(f"Focus on weak subject: {weak_subject}")
        if emotion_state:
            sections.append(f"Emotional state: {emotion_state}")
        if llm_questions:
            sections.append("Review questions: " + "; ".join(llm_questions[:3]))
        if llm_text:
            sections.append(f"Reference: {llm_text[:500]}")

        summary = "\n".join(sections) if sections else llm_text

        return {
            "tool": "review_generator",
            "input": user_input,
            "weak_subject": weak_subject,
            "emotion_state": emotion_state,
            "sections": sections,
            "text": f"Review for: {user_input}\n{summary}" if user_input else summary,
        }
