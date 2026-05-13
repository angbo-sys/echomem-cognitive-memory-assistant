"""Minimal study planner tool."""

from __future__ import annotations

from typing import Any, Dict, Optional


class StudyPlanner:
    """Generate a lightweight study plan skeleton."""

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
        learning_goal = context.get("learning_goal", user_input)

        # Parse LLM output — could be a dict (tool result) or plain string
        llm_text = ""
        llm_suggestions: list[str] = []
        if llm_output is not None:
            if isinstance(llm_output, dict):
                llm_text = str(llm_output.get("text", llm_output.get("content", "")))
                raw = llm_output.get("suggestions") or llm_output.get("plan") or []
                llm_suggestions = [str(s) for s in raw if s]
            else:
                llm_text = str(llm_output)

        # Build plan steps
        plan: list[str] = []
        if learning_goal:
            plan.append(f"Primary goal: {learning_goal}")
        if weak_subject:
            plan.append(f"Weak subject focus: {weak_subject}")
        if llm_suggestions:
            plan.extend(llm_suggestions[:5])
        else:
            plan.extend([
                "Clarify target and constraints",
                "Break topic into 3–5 milestones",
                "Assign daily/weekly tasks",
                "Schedule review checkpoints",
            ])

        # Build text description
        parts = [f"Study plan for: {user_input or learning_goal or 'general study'}"]
        if weak_subject:
            parts.append(f"Weak subject identified: {weak_subject}")
        if llm_text:
            parts.append(f"LLM guidance: {llm_text[:500]}")

        return {
            "tool": "study_planner",
            "input": user_input,
            "plan": plan,
            "weak_subject": weak_subject,
            "learning_goal": learning_goal,
            "text": "\n".join(parts),
        }
