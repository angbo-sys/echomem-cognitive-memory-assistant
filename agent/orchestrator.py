"""Lightweight orchestrator for wiring stm/profile/emotion/retrieval/llm."""

from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any, Dict, Optional


class Orchestrator:
    """First-pass orchestrator with duck-typed component calls.

    Expected components are optional and discovered by capability instead of type.
    """

    def __init__(
        self,
        *,
        stm: Any = None,
        profile: Any = None,
        emotion_tool: Any = None,
        memory_tool: Any = None,
        study_planner_tool: Any = None,
        review_generator_tool: Any = None,
        llm: Any = None,
        system_prompt_path: Optional[str] = None,
    ) -> None:
        self.stm = stm
        self.profile = profile
        self.emotion_tool = emotion_tool
        self.memory_tool = memory_tool
        self.study_planner_tool = study_planner_tool
        self.review_generator_tool = review_generator_tool
        self.llm = llm
        self.system_prompt_path = system_prompt_path or str(
            Path(__file__).with_name("prompts") / "system_prompt.txt"
        )

    def run(
        self,
        user_input: str,
        *,
        user_id: Optional[str] = None,
        task: str = "chat",
        extra_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run end-to-end inference flow.

        Returns structured data so upper layers can debug/instrument easily.
        """
        context = extra_context or {}

        profile_data = self._fetch_profile(user_id=user_id, context=context)
        stm_data = self._fetch_stm(user_input=user_input, user_id=user_id, context=context)
        emotion_data = self._run_tool(
            self.emotion_tool, text=user_input, user_id=user_id, context=context
        )
        retrieval_data = self._run_tool(
            self.memory_tool,
            query=user_input,
            user_id=user_id,
            context={"stm": stm_data, "user_id": user_id, **context},
        )

        prompt = self._render_prompt(
            user_input=user_input,
            profile=profile_data,
            emotion=emotion_data,
            memory=retrieval_data,
            stm=stm_data,
            context=context,
        )

        llm_output = self._call_llm(prompt=prompt, user_input=user_input, context=context)
        response_text = self._extract_text(llm_output)

        self._append_stm(role="user", content=user_input)
        self._append_stm(role="assistant", content=response_text)

        profile_updates = self._run_profile_update_pipeline(
            user_input=user_input,
            response_text=response_text,
            user_id=user_id,
            profile_data=profile_data,
            emotion_data=emotion_data,
        )

        # Build memory_evolution from applied profile updates and store in STM for feedback.
        memory_evolution: list[Dict[str, Any]] = []
        evolution_feedback_parts: list[str] = []
        for update in profile_updates:
            if not isinstance(update, dict):
                continue
            applied = bool(update.get("applied"))
            field = str(update.get("field", ""))
            old_v = update.get("old_value")
            new_v = update.get("new_value")
            entry: Dict[str, Any] = {
                "field": field,
                "old_value": old_v,
                "new_value": new_v,
                "applied": applied,
            }
            if applied:
                entry["trigger"] = str(update.get("trigger", ""))
                entry["confidence"] = update.get("confidence")
                evolution_feedback_parts.append(f"{field}: {old_v} → {new_v}")
            else:
                entry["reason"] = str(update.get("reason", ""))
            memory_evolution.append(entry)

        # Store evolution feedback in STM summary for cross-turn continuity.
        if evolution_feedback_parts and self.stm is not None:
            summary = "画像更新: " + "; ".join(evolution_feedback_parts)
            set_summary = getattr(self.stm, "set_summary", None)
            if callable(set_summary):
                self._safe_call(set_summary, text=summary)
        elif self.stm is not None:
            set_summary = getattr(self.stm, "set_summary", None)
            if callable(set_summary):
                self._safe_call(set_summary, text=None)

        tool_output: Optional[Dict[str, Any]] = None
        if task == "study_plan":
            tool_output = self._run_tool(
                self.study_planner_tool,
                user_input=user_input,
                llm_output=llm_output,
                user_id=user_id,
                context={**context, "profile_updates": profile_updates},
            )
        elif task == "review":
            tool_output = self._run_tool(
                self.review_generator_tool,
                user_input=user_input,
                llm_output=llm_output,
                user_id=user_id,
                context={**context, "profile_updates": profile_updates},
            )

        response_text = self._extract_text(tool_output) or response_text
        framework_writes = self._store_framework_interaction(
            user_id=user_id,
            user_input=user_input,
            response_text=response_text,
        )
        if framework_writes and isinstance(retrieval_data, dict):
            osm = retrieval_data.setdefault("open_source_memory", {})
            if isinstance(osm, dict):
                osm["framework_writes"] = framework_writes

        return {
            "task": task,
            "user_id": user_id,
            "input": user_input,
            "profile": profile_data,
            "stm": stm_data,
            "emotion": emotion_data,
            "retrieval": retrieval_data,
            "llm": llm_output,
            "tool_output": tool_output,
            "response": response_text,
            "profile_updates": profile_updates,
            "memory_evolution": memory_evolution,
            "framework_writes": framework_writes,
            "prompt": prompt,
        }

    def _store_framework_interaction(
        self,
        *,
        user_id: Optional[str],
        user_input: str,
        response_text: str,
    ) -> Dict[str, Any]:
        if self.memory_tool is None or not response_text:
            return {}
        store_method = getattr(self.memory_tool, "store_interaction", None)
        if not callable(store_method):
            return {}
        result = self._safe_call(
            store_method,
            user_id=user_id or "anonymous",
            user_input=user_input,
            assistant_output=response_text,
        )
        return result if isinstance(result, dict) else {}

    def _append_stm(self, *, role: str, content: str) -> None:
        if not content or self.stm is None:
            return
        add_method = getattr(self.stm, "add", None)
        if not callable(add_method):
            return
        self._safe_call(add_method, role=role, content=content)

    def _run_profile_update_pipeline(
        self,
        *,
        user_input: str,
        response_text: str,
        user_id: Optional[str],
        profile_data: Any,
        emotion_data: Any,
    ) -> list[Dict[str, Any]]:
        updates = self._extract_profile_candidates(
            user_input=user_input,
            response_text=response_text,
            emotion_data=emotion_data,
        )
        if not updates:
            return []

        current_profile = profile_data if isinstance(profile_data, dict) else {}
        deduped: list[Dict[str, Any]] = []
        seen_fields: set[str] = set()
        for item in updates:
            field = str(item.get("field", "")).strip()
            if not field or field in seen_fields:
                continue
            seen_fields.add(field)
            deduped.append(item)

        update_field = getattr(self.profile, "update_field", None) if self.profile is not None else None
        if not callable(update_field) or not user_id:
            for item in deduped:
                item["old_value"] = current_profile.get(item["field"])
                item["applied"] = False
                item["reason"] = "profile_update_unavailable"
            return deduped

        applied_updates: list[Dict[str, Any]] = []
        for item in deduped:
            field = item["field"]
            new_value = item["new_value"]
            old_value = current_profile.get(field)
            if old_value == new_value:
                item["old_value"] = old_value
                item["applied"] = False
                item["reason"] = "unchanged"
                applied_updates.append(item)
                continue

            try:
                self._safe_call(
                    update_field,
                    user_id=user_id,
                    field=field,
                    new_value=new_value,
                    trigger=item["trigger"],
                    confidence=float(item["confidence"]),
                )
                current_profile[field] = new_value
                item["old_value"] = old_value
                item["applied"] = True
            except Exception as exc:  # noqa: BLE001
                item["old_value"] = old_value
                item["applied"] = False
                item["reason"] = f"update_failed:{exc}"
            applied_updates.append(item)
        return applied_updates

    def _extract_profile_candidates(
        self,
        *,
        user_input: str,
        response_text: str,
        emotion_data: Any,
    ) -> list[Dict[str, Any]]:
        text = (user_input or "").strip()
        if not text:
            return []

        candidates: list[Dict[str, Any]] = []

        goal_match = re.search(r"(?:目标|想要|计划|准备)(?:是|为|:)?(.{2,40}?)(?:[，。；;,、！\n]|$)", text)
        if goal_match:
            self._append_profile_candidate(
                candidates,
                field="learning_goal",
                value=goal_match.group(1),
                trigger="rule:learning_goal",
                confidence=0.70,
            )

        style_match = re.search(r"(简洁|详细|分步骤|举例|直接一点|慢一点|快一点)", text)
        if style_match:
            self._append_profile_candidate(
                candidates,
                field="preferred_style",
                value=style_match.group(1),
                trigger="rule:preferred_style",
                confidence=0.72,
            )

        weak_match = re.search(r"(薄弱|不擅长|不会|困难)(?:的是|是|在)?(.{1,20}?)(?:[，。；;,、！\n]|$)", text)
        if weak_match:
            self._append_profile_candidate(
                candidates,
                field="weak_subject",
                value=weak_match.group(2),
                trigger="rule:weak_subject",
                confidence=0.68,
            )

        level_match = re.search(r"(初学|入门|中级|中等|高级|熟练)", text)
        if level_match:
            self._append_profile_candidate(
                candidates,
                field="knowledge_level",
                value=level_match.group(1),
                trigger="rule:knowledge_level",
                confidence=0.66,
            )

        focus_match = re.search(r"(最近|这周|今天)(?:在|主要|一直)?(.{2,30}?)(?:[，。；;,、！\n]|$)", text)
        if focus_match:
            self._append_profile_candidate(
                candidates,
                field="recent_focus",
                value=focus_match.group(2),
                trigger="rule:recent_focus",
                confidence=0.62,
            )

        candidates.extend(self._extract_semantic_profile_candidates(text))

        if isinstance(emotion_data, dict) and emotion_data.get("label"):
            candidates.append(
                {
                    "field": "emotion_state",
                    "new_value": str(emotion_data.get("label")),
                    "trigger": "emotion_analyzer",
                    "confidence": float(emotion_data.get("confidence", 0.6) or 0.6),
                }
            )

        if response_text and ("分步骤" in response_text or "步骤" in response_text):
            candidates.append(
                {
                    "field": "preferred_style",
                    "new_value": "分步骤",
                    "trigger": "assistant_response_signal",
                    "confidence": 0.55,
                }
            )

        return candidates

    @classmethod
    def _extract_semantic_profile_candidates(cls, text: str) -> list[Dict[str, Any]]:
        """Capture common profile paraphrases that are not fixed keyword forms."""
        candidates: list[Dict[str, Any]] = []
        semantic_patterns: list[tuple[str, str, str, float]] = [
            (
                "learning_goal",
                r"([^，。；;,、！\n]{2,40}?)(?:是|会是|就是)?我(?:接下来|未来|之后|当前|现在)?(?:的)?(?:方向|目标|重点|主线)(?:[，。；;,、！\n]|$)",
                "semantic:learning_goal_direction",
                0.74,
            ),
            (
                "learning_goal",
                r"我(?:接下来|未来|之后|当前|现在)?(?:的)?(?:方向|目标|重点|主线)(?:是|放在|转向)([^，。；;,、！\n]{2,40}?)(?:[，。；;,、！\n]|$)",
                "semantic:learning_goal_focus",
                0.74,
            ),
            (
                "weak_subject",
                r"([^，。；;,、！\n]{1,24}?)(?:一直|总是|还是|有点|比较)?(?:卡住|拖后腿|搞不懂|学不明白|吃力)(?:[，。；;,、！\n]|$)",
                "semantic:weak_subject_blocked",
                0.72,
            ),
            (
                "weak_subject",
                r"我(?:在|对)?([^，。；;,、！\n]{1,24}?)(?:上)?(?:卡住|吃力|容易错|跟不上)(?:[，。；;,、！\n]|$)",
                "semantic:weak_subject_difficulty",
                0.72,
            ),
            (
                "recent_focus",
                r"(?:最近|这阵子|这两天|目前|当前)(?:主要|一直|都在|在)?([^，。；;,、！\n]{2,30}?)(?:[，。；;,、！\n]|$)",
                "semantic:recent_focus",
                0.65,
            ),
        ]
        for field, pattern, trigger, confidence in semantic_patterns:
            match = re.search(pattern, text)
            if match:
                cls._append_profile_candidate(
                    candidates,
                    field=field,
                    value=match.group(1),
                    trigger=trigger,
                    confidence=confidence,
                )

        style_aliases = [
            (r"一步一步|拆开讲|按步骤|分层讲", "分步骤", 0.76),
            (r"少废话|别太啰嗦|短一点|压缩一点", "简洁", 0.74),
            (r"多举例|带例子|结合例子", "举例", 0.74),
            (r"讲细一点|展开讲|讲透一点", "详细", 0.72),
        ]
        for pattern, value, confidence in style_aliases:
            if re.search(pattern, text):
                cls._append_profile_candidate(
                    candidates,
                    field="preferred_style",
                    value=value,
                    trigger="semantic:preferred_style_alias",
                    confidence=confidence,
                )
                break

        level_aliases = [
            (r"零基础|完全没基础|刚开始学|刚入门", "入门", 0.72),
            (r"基础一般|半懂不懂|只会一点", "初学", 0.68),
            (r"有一定基础|基础还可以", "中级", 0.68),
            (r"比较熟|很熟|熟练掌握", "熟练", 0.70),
        ]
        for pattern, value, confidence in level_aliases:
            if re.search(pattern, text):
                cls._append_profile_candidate(
                    candidates,
                    field="knowledge_level",
                    value=value,
                    trigger="semantic:knowledge_level_alias",
                    confidence=confidence,
                )
                break
        return candidates

    @classmethod
    def _append_profile_candidate(
        cls,
        candidates: list[Dict[str, Any]],
        *,
        field: str,
        value: Any,
        trigger: str,
        confidence: float,
    ) -> None:
        normalized = cls._normalize_profile_value(value)
        if not normalized:
            return
        candidates.append(
            {
                "field": field,
                "new_value": normalized,
                "trigger": trigger,
                "confidence": confidence,
            }
        )

    @staticmethod
    def _normalize_profile_value(value: Any) -> str:
        text = str(value or "").strip()
        text = re.sub(r"^[：:，,。；;\s]*(?:是|为|在|的|我|我的|主要|一直|最近|目前|当前)+", "", text)
        text = re.sub(r"(?:这件事|这个点|这块|方面|部分)$", "", text)
        text = text.strip(" ：:，。；;,.、！!？?\n\t")
        text = re.sub(r"\s+", " ", text)
        if len(text) > 40:
            text = text[:40].rstrip()
        if len(text) < 1 or text in {"我", "我的", "一下", "一点"}:
            return ""
        if not re.search(r"[\w\u4e00-\u9fff]", text):
            return ""
        return text

    def _fetch_profile(self, *, user_id: Optional[str], context: Dict[str, Any]) -> Any:
        if self.profile is None:
            return None
        for method_name in ("get_profile", "load_profile", "fetch", "get"):
            method = getattr(self.profile, method_name, None)
            if callable(method):
                return self._safe_call(method, user_id=user_id, context=context)
        return None

    def _fetch_stm(self, *, user_input: str, user_id: Optional[str], context: Dict[str, Any]) -> Any:
        if self.stm is None:
            return None
        for method_name in ("recall", "search", "get_recent", "run"):
            method = getattr(self.stm, method_name, None)
            if callable(method):
                data = self._safe_call(
                    method,
                    query=user_input,
                    text=user_input,
                    user_input=user_input,
                    user_id=user_id,
                    context=context,
                )
                get_summary = getattr(self.stm, "get_summary", None)
                summary = get_summary() if callable(get_summary) else None
                if summary:
                    return {"recent": data, "summary": summary}
                return data
        return None

    def _run_tool(self, tool: Any, **kwargs: Any) -> Any:
        if tool is None:
            return None
        run = getattr(tool, "run", None)
        if callable(run):
            return self._safe_call(run, **kwargs)
        return None

    def _call_llm(self, *, prompt: str, user_input: str, context: Dict[str, Any]) -> Any:
        if self.llm is None:
            return {"text": "", "reason": "no llm configured"}

        candidates = ("generate", "respond", "complete", "chat", "invoke", "run")
        for method_name in candidates:
            method = getattr(self.llm, method_name, None)
            if not callable(method):
                continue
            return self._safe_call(
                method,
                prompt=prompt,
                user_input=user_input,
                input=user_input,
                messages=[{"role": "user", "content": user_input}],
                context=context,
                max_completion_tokens=int(context.get("max_completion_tokens", 512))
                if isinstance(context, dict)
                else 512,
                max_tokens=int(context.get("max_completion_tokens", 512))
                if isinstance(context, dict)
                else 512,
            )
        return {"text": "", "reason": "llm method not found"}

    def _render_prompt(
        self,
        *,
        user_input: str,
        profile: Any,
        emotion: Any,
        memory: Any,
        stm: Any,
        context: Dict[str, Any],
    ) -> str:
        template = self._load_system_prompt()
        # Extract open-source memory framework signals for LLM context.
        osm = {}
        knowledge_analysis = ""
        if isinstance(memory, dict):
            osm_raw = memory.get("open_source_memory")
            if isinstance(osm_raw, dict):
                osm = osm_raw
                mimo = osm.get("mimo_analysis")
                if isinstance(mimo, dict) and mimo.get("enabled") and mimo.get("summary"):
                    knowledge_analysis = mimo["summary"]
        # Format framework signals into a digestible text block.
        open_source_signals = self._format_osm_signals(osm)

        mapping = {
            "profile": self._to_text(profile),
            "emotion": self._to_text(emotion),
            "retrieval": self._retrieval_digest(memory),
            "stm": self._to_text(stm),
            "context": self._to_text(context),
            "user_input": user_input,
            "open_source_signals": open_source_signals,
            "knowledge_analysis": knowledge_analysis,
        }
        mapping = self._apply_prompt_section_budget(template, mapping, context=context)
        rendered = template
        for key, value in mapping.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", value)
        return self._apply_prompt_budget(rendered, context=context)

    @classmethod
    def _apply_prompt_section_budget(
        cls,
        template: str,
        mapping: Dict[str, str],
        *,
        context: Dict[str, Any],
    ) -> Dict[str, str]:
        """Trim prompt sections by priority before the final whole-prompt guardrail."""
        if not isinstance(context, dict):
            return mapping
        raw_budget = context.get("max_prompt_chars")
        if raw_budget is None and context.get("max_prompt_tokens") is not None:
            try:
                raw_budget = int(context["max_prompt_tokens"]) * 4
            except (TypeError, ValueError):
                raw_budget = None
        try:
            max_chars = int(raw_budget) if raw_budget is not None else 0
        except (TypeError, ValueError):
            return mapping
        if max_chars <= 0:
            return mapping

        rendered_length = len(template)
        for key, value in mapping.items():
            rendered_length += len(value) - len(f"{{{{{key}}}}}")
        if rendered_length <= max_chars:
            return mapping

        fixed_template = template
        for key in mapping:
            fixed_template = fixed_template.replace(f"{{{{{key}}}}}", "")
        protected = {
            "user_input": mapping.get("user_input", ""),
            "profile": mapping.get("profile", ""),
            "emotion": mapping.get("emotion", ""),
        }
        protected_len = len(fixed_template) + sum(len(v) for v in protected.values())
        available = max(160, max_chars - protected_len - 80)
        section_weights = [
            ("stm", 0.20, 360),
            ("retrieval", 0.24, 420),
            ("open_source_signals", 0.22, 420),
            ("knowledge_analysis", 0.18, 320),
            ("context", 0.10, 220),
        ]
        trimmed = dict(mapping)
        for key, weight, minimum in section_weights:
            if key not in trimmed:
                continue
            limit = max(minimum, int(available * weight))
            trimmed[key] = cls._trim_prompt_section(trimmed[key], limit=limit, label=key)
        return trimmed

    @staticmethod
    def _trim_prompt_section(text: str, *, limit: int, label: str) -> str:
        if len(text) <= limit:
            return text
        marker = f"\n...[{label} 已按区块预算裁剪]...\n"
        if limit <= len(marker) + 40:
            return text[: max(0, limit - len(marker))] + marker.strip()
        keep_start = max(20, int((limit - len(marker)) * 0.62))
        keep_end = max(20, limit - len(marker) - keep_start)
        return text[:keep_start].rstrip() + marker + text[-keep_end:].lstrip()

    @staticmethod
    def _apply_prompt_budget(prompt: str, *, context: Dict[str, Any]) -> str:
        """Trim oversized prompt context while preserving the latest user input tail."""
        if not isinstance(context, dict):
            return prompt
        raw_budget = context.get("max_prompt_chars")
        if raw_budget is None and context.get("max_prompt_tokens") is not None:
            try:
                raw_budget = int(context["max_prompt_tokens"]) * 4
            except (TypeError, ValueError):
                raw_budget = None
        if raw_budget is None:
            return prompt
        try:
            max_chars = int(raw_budget)
        except (TypeError, ValueError):
            return prompt
        if max_chars <= 0 or len(prompt) <= max_chars:
            return prompt

        marker = "\n...[已按输入预算裁剪中间上下文]...\n"
        if max_chars <= len(marker) + 40:
            return prompt[-max_chars:]
        keep_start = max(20, (max_chars - len(marker)) // 2)
        keep_end = max_chars - len(marker) - keep_start
        if keep_end < 20:
            keep_end = 20
            keep_start = max_chars - len(marker) - keep_end
        return prompt[:keep_start] + marker + prompt[-keep_end:]

    @staticmethod
    def _format_osm_signals(osm: dict) -> str:
        """Format open-source memory framework signals into readable text."""
        parts: list[str] = []
        contributions = osm.get("framework_contributions")
        if isinstance(contributions, list):
            for item in contributions[:3]:
                if not isinstance(item, dict):
                    continue
                signals = item.get("signals") if isinstance(item.get("signals"), list) else []
                preview = "; ".join(str(x)[:80] for x in signals[:3]) or "无命中"
                parts.append(
                    f"[{item.get('framework')} · {item.get('role')}]: "
                    f"{preview} (source={item.get('signal_source', '')}, count={item.get('signal_count', 0)})"
                )
        for key, label in [
            ("mem0", "Mem0(偏好/事实)"),
            ("llamaindex_memory", "LlamaIndex(文档命中)"),
            ("cognee", "Cognee(关联概念)"),
        ]:
            details = osm.get(key, {})
            if isinstance(details, dict):
                # Extract meaningful content based on framework.
                facts = details.get("facts") if isinstance(details.get("facts"), list) else []
                snippets = details.get("context_snippets") if isinstance(details.get("context_snippets"), list) else []
                doc_hits = details.get("doc_hits") if isinstance(details.get("doc_hits"), list) else []
                concepts = details.get("related_concepts") if isinstance(details.get("related_concepts"), list) else []
                combined = facts or snippets or doc_hits or concepts
                if combined and not contributions:
                    previews = [str(c)[:80] for c in combined[:3]]
                    parts.append(f"[{label}]: {'; '.join(previews)}")
        if not parts:
            parts.append("(无框架信号)")
        scenario = osm.get("scenario_routing", {}).get("scenario", "general") if isinstance(osm.get("scenario_routing"), dict) else "general"
        parts.insert(0, f"[场景路由]: {scenario}")
        return "\n".join(parts)

    def _load_system_prompt(self) -> str:
        path = Path(self.system_prompt_path)
        if not path.exists():
            return "User input: {{user_input}}"
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _safe_call(func: Any, **kwargs: Any) -> Any:
        try:
            sig = inspect.signature(func)
        except (TypeError, ValueError):
            return func(**kwargs)

        params = sig.parameters.values()
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params):
            return func(**kwargs)

        accepted = {
            p.name
            for p in params
            if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
        }
        filtered_kwargs = {k: v for k, v in kwargs.items() if k in accepted}
        return func(**filtered_kwargs)

    @staticmethod
    def _extract_text(payload: Any) -> str:
        if payload is None:
            return ""
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            for key in ("response", "text", "content", "output"):
                value = payload.get(key)
                if isinstance(value, str):
                    return value
        return str(payload)

    @staticmethod
    def _to_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return str(value)

    @staticmethod
    def _retrieval_digest(value: Any) -> str:
        if not isinstance(value, dict):
            return Orchestrator._to_text(value)
        hits = value.get("hits") if isinstance(value.get("hits"), list) else []
        top_hits: list[str] = []
        for hit in hits[:5]:
            if not isinstance(hit, dict):
                continue
            content = str(hit.get("content", "")).strip()
            if content:
                top_hits.append(content[:180])

        osm = value.get("open_source_memory") if isinstance(value.get("open_source_memory"), dict) else {}
        routing = osm.get("scenario_routing") if isinstance(osm.get("scenario_routing"), dict) else {}
        scenario = str(routing.get("scenario", "general"))
        return (
            f"backend={value.get('backend', 'unknown')}; "
            f"scenario={scenario}; "
            f"top_hits={top_hits}; "
            f"summary={value.get('text', '')[:300]}"
        )
