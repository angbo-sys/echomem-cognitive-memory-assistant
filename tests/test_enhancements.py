"""Test coverage for the enhancement batch covering emotion, study/review, evolution, and prompt injection."""

from __future__ import annotations

import tempfile
import unittest
from typing import Any, Dict

from agent.tools import EmotionAnalyzer, ReviewGenerator, StudyPlanner
from memory import ShortTermMemory
from profile import EmotionEngine


# ── Emotion Classification ──────────────────────────────────────────────────


class TestEmotionEngineEnhancements(unittest.TestCase):
    """Test new labels, empty-string handling, and expanded keyword coverage."""

    def setUp(self) -> None:
        self.engine = EmotionEngine()

    def test_empty_string_returns_neutral(self) -> None:
        """Empty string should return neutral, not raise ValueError."""
        result = self.engine.classify("")
        self.assertEqual(result.label, "neutral")
        self.assertEqual(result.source, "rule")

    def test_whitespace_string_returns_neutral(self) -> None:
        result = self.engine.classify("   ")
        self.assertEqual(result.label, "neutral")

    def test_new_label_confused_keyword(self) -> None:
        result = self.engine.classify("我完全不懂这个问题")
        self.assertEqual(result.label, "confused")
        self.assertGreater(result.confidence, 0.5)

    def test_new_label_tired_keyword(self) -> None:
        result = self.engine.classify("今天太累了，没精力学习")
        self.assertEqual(result.label, "tired")

    def test_new_label_discouraged_keyword(self) -> None:
        result = self.engine.classify("我有点想放弃了，好失望")
        self.assertEqual(result.label, "discouraged")

    def test_new_label_curious_keyword(self) -> None:
        result = self.engine.classify("我很好奇这个原理是什么")
        self.assertEqual(result.label, "curious")

    def test_english_confused(self) -> None:
        result = self.engine.classify("I'm confused by this concept")
        self.assertEqual(result.label, "confused")

    def test_anxious_expanded_keywords(self) -> None:
        result = self.engine.classify("心里好忐忑，不安")
        self.assertEqual(result.label, "anxious")

    def test_positive_expanded_keywords(self) -> None:
        result = self.engine.classify("太棒了，真的很赞")
        self.assertEqual(result.label, "positive")

    def test_frustrated_expanded_keywords(self) -> None:
        result = self.engine.classify("真是受不了，太无语了")
        self.assertEqual(result.label, "frustrated")

    def test_confidence_bound(self) -> None:
        """Confidence should not exceed 0.95."""
        text = "confused confused confused confused confused " * 5
        result = self.engine.classify(text)
        self.assertLessEqual(result.confidence, 0.95)

    def test_all_labels_accessible(self) -> None:
        labels = {
            "positive", "neutral", "anxious", "frustrated",
            "confident", "confused", "tired", "discouraged", "curious",
        }
        self.assertEqual(self.engine._SUPPORTED_LABELS, labels)


class TestEmotionAnalyzerWithLLM(unittest.TestCase):
    """Test that EmotionAnalyzer accepts and wires LLM classifier."""

    def test_llm_parameter_accepted(self) -> None:
        """LLM parameter should not raise error."""
        analyzer = EmotionAnalyzer(llm=None)
        result = analyzer.run("test")
        self.assertIn("label", result)

    def test_no_llm_fallback_to_rule(self) -> None:
        analyzer = EmotionAnalyzer()
        result = analyzer.run("I am confused")
        self.assertEqual(result["label"], "confused")
        self.assertEqual(result["source"], "rule")


# ── Study Planner ───────────────────────────────────────────────────────────


class TestStudyPlannerEnhancements(unittest.TestCase):
    """Test that StudyPlanner accepts and uses context/input/llm_output."""

    def setUp(self) -> None:
        self.planner = StudyPlanner()

    def test_basic_study_plan_with_input(self) -> None:
        result = self.planner.run(user_input="准备考研")
        self.assertEqual(result["tool"], "study_planner")
        self.assertIn("plan", result)
        self.assertIn("input", result)

    def test_study_plan_with_profile_context(self) -> None:
        result = self.planner.run(
            user_input="学数学",
            context={"weak_subject": "微积分", "learning_goal": "考研数学140"},
        )
        self.assertIn("weak_subject", result)
        self.assertEqual(result.get("weak_subject"), "微积分")
        self.assertEqual(result.get("learning_goal"), "考研数学140")
        # Plan should reference weak subject
        plan_text = "\n".join(result.get("plan", []))
        self.assertIn("微积分", plan_text)

    def test_study_plan_with_llm_output_string(self) -> None:
        result = self.planner.run(
            user_input="学Python",
            llm_output="建议先学基础语法，然后做项目练习",
        )
        self.assertIn("LLM guidance", result.get("text", ""))

    def test_study_plan_with_llm_output_dict(self) -> None:
        result = self.planner.run(
            user_input="学英语",
            llm_output={"text": "每日背单词30个", "suggestions": ["听力", "阅读", "写作"]},
        )
        plan = result.get("plan", [])
        self.assertTrue(any("听力" in str(s) for s in plan))

    def test_study_plan_backward_compatible(self) -> None:
        """Should work with no context (empty call)."""
        result = self.planner.run()
        self.assertIn("plan", result)

    def test_study_plan_extra_kwargs_accepted(self) -> None:
        """Should accept **kwargs without error."""
        result = self.planner.run(user_input="test", unused_arg="value")
        self.assertIn("plan", result)


# ── Review Generator ────────────────────────────────────────────────────────


class TestReviewGeneratorEnhancements(unittest.TestCase):
    """Test that ReviewGenerator accepts and uses context/input/llm_output."""

    def setUp(self) -> None:
        self.generator = ReviewGenerator()

    def test_basic_review_with_input(self) -> None:
        result = self.generator.run(user_input="复习微积分")
        self.assertEqual(result["tool"], "review_generator")
        self.assertIn("sections", result)

    def test_review_with_profile_context(self) -> None:
        result = self.generator.run(
            user_input="复习",
            context={"weak_subject": "导数", "emotion_state": "anxious"},
        )
        self.assertEqual(result.get("weak_subject"), "导数")
        self.assertEqual(result.get("emotion_state"), "anxious")
        sections_text = " ".join(result.get("sections", []))
        self.assertIn("导数", sections_text)
        self.assertIn("anxious", sections_text)

    def test_review_with_llm_output_dict(self) -> None:
        result = self.generator.run(
            user_input="复习化学",
            llm_output={"text": "重点复习元素周期表", "questions": ["什么是氧化还原反应?"]},
        )
        sections = result.get("sections", [])
        self.assertTrue(any("氧化还原" in str(s) for s in sections))

    def test_review_backward_compatible(self) -> None:
        result = self.generator.run()
        self.assertIn("sections", result)

    def test_review_extra_kwargs(self) -> None:
        result = self.generator.run(user_input="test", unused=True)
        self.assertIn("sections", result)


# ── ShortTermMemory Enhancement (Summary) ───────────────────────────────────


class TestShortTermMemorySummary(unittest.TestCase):
    """Test that STM's set_summary/get_summary works for evolution feedback."""

    def test_set_and_get_summary(self) -> None:
        stm = ShortTermMemory(max_turns=3)
        stm.set_summary("画像更新: learning_goal: 数学 → 英语")
        self.assertEqual(stm.get_summary(), "画像更新: learning_goal: 数学 → 英语")

    def test_set_summary_none(self) -> None:
        stm = ShortTermMemory(max_turns=3)
        stm.set_summary(None)
        self.assertIsNone(stm.get_summary())

    def test_set_summary_empty(self) -> None:
        stm = ShortTermMemory(max_turns=3)
        stm.set_summary("")
        self.assertEqual(stm.get_summary(), "")

    def test_sqlite_backed_stm_restores_messages_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = f"{tmp}/stm.db"
            stm = ShortTermMemory(max_turns=3, db_path=db_path, user_id="u1", session_id="s1")
            stm.add("user", "第一条")
            stm.add("assistant", "第二条")
            stm.set_summary("画像更新: goal A → B")

            restored = ShortTermMemory(max_turns=3, db_path=db_path, user_id="u1", session_id="s1")
            recent = restored.get_recent()
            self.assertEqual([item["content"] for item in recent], ["第一条", "第二条"])
            self.assertEqual(restored.get_summary(), "画像更新: goal A → B")

    def test_sqlite_backed_stm_is_scoped_and_trimmed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = f"{tmp}/stm.db"
            u1 = ShortTermMemory(max_turns=2, db_path=db_path, user_id="u1", session_id="s1")
            u1.add("user", "u1-1")
            u1.add("assistant", "u1-2")
            u1.add("user", "u1-3")
            ShortTermMemory(max_turns=2, db_path=db_path, user_id="u2", session_id="s1").add("user", "u2-1")

            restored = ShortTermMemory(max_turns=2, db_path=db_path, user_id="u1", session_id="s1")
            self.assertEqual([item["content"] for item in restored.get_recent()], ["u1-2", "u1-3"])

            other = ShortTermMemory(max_turns=2, db_path=db_path, user_id="u2", session_id="s1")
            self.assertEqual([item["content"] for item in other.get_recent()], ["u2-1"])

    def test_sqlite_backed_stm_clear_removes_persisted_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = f"{tmp}/stm.db"
            stm = ShortTermMemory(max_turns=3, db_path=db_path, user_id="u1", session_id="s1")
            stm.add("user", "hello")
            stm.set_summary("summary")
            stm.clear()

            restored = ShortTermMemory(max_turns=3, db_path=db_path, user_id="u1", session_id="s1")
            self.assertEqual(restored.get_recent(), [])
            self.assertIsNone(restored.get_summary())

    def test_sqlite_backed_stm_sessions_are_scoped_by_session_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = f"{tmp}/stm.db"
            s1 = ShortTermMemory(max_turns=5, db_path=db_path, user_id="u1", session_id="s1")
            s2 = ShortTermMemory(max_turns=5, db_path=db_path, user_id="u1", session_id="s2")
            s1.add("user", "第一会话的问题")
            s2.add("user", "第二会话的问题")
            s1.clear()

            self.assertEqual(
                ShortTermMemory(max_turns=5, db_path=db_path, user_id="u1", session_id="s1").get_recent(),
                [],
            )
            self.assertEqual(
                [item["content"] for item in ShortTermMemory(max_turns=5, db_path=db_path, user_id="u1", session_id="s2").get_recent()],
                ["第二会话的问题"],
            )

    def test_sqlite_backed_stm_lists_sessions_with_titles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = f"{tmp}/stm.db"
            ShortTermMemory(max_turns=5, db_path=db_path, user_id="u1", session_id="s1").add(
                "user", "请帮我复习条件概率和贝叶斯公式"
            )
            ShortTermMemory(max_turns=5, db_path=db_path, user_id="u1", session_id="s2").add(
                "user", "整理英语阅读技巧"
            )

            sessions = ShortTermMemory(max_turns=5, db_path=db_path, user_id="u1", session_id="s2").list_sessions()

            self.assertEqual({item["session_id"] for item in sessions}, {"s1", "s2"})
            by_id = {item["session_id"]: item for item in sessions}
            self.assertEqual(by_id["s1"]["message_count"], 1)
            self.assertIn("条件概率", by_id["s1"]["title"])


# ── Orchestrator Prompt Injection ───────────────────────────────────────────


class TestFormatOSMSignals(unittest.TestCase):
    """Test _format_osm_signals static method logic."""

    def test_empty_osm_returns_fallback(self) -> None:
        from agent.orchestrator import Orchestrator

        result = Orchestrator._format_osm_signals({})
        self.assertIn("无框架信号", result)

    def test_osm_with_mem0_facts(self) -> None:
        from agent.orchestrator import Orchestrator

        osm = {
            "mem0": {"facts": ["偏好简洁风格", "喜欢举例说明"]},
            "scenario_routing": {"scenario": "preference_alignment"},
        }
        result = Orchestrator._format_osm_signals(osm)
        self.assertIn("场景路由", result)
        self.assertIn("Mem0", result)

    def test_osm_with_cognee_concepts(self) -> None:
        from agent.orchestrator import Orchestrator

        osm = {"cognee": {"related_concepts": ["微积分", "导数", "极限"]}}
        result = Orchestrator._format_osm_signals(osm)
        self.assertIn("Cognee", result)


class TestRetrievalDigestContainsScenario(unittest.TestCase):
    """Test that _retrieval_digest includes scenario routing."""

    def test_digest_includes_scenario(self) -> None:
        from agent.orchestrator import Orchestrator

        data = {
            "backend": "sql_fallback",
            "open_source_memory": {
                "scenario_routing": {"scenario": "knowledge_qa"},
            },
            "text": "test summary",
        }
        result = Orchestrator._retrieval_digest(data)
        self.assertIn("knowledge_qa", result)


class TestPromptBudget(unittest.TestCase):
    def test_apply_prompt_budget_keeps_prompt_under_limit(self) -> None:
        from agent.orchestrator import Orchestrator

        prompt = "A" * 300 + "\nUSER_INPUT: 请回答最后的问题"
        result = Orchestrator._apply_prompt_budget(prompt, context={"max_prompt_chars": 120})
        self.assertLessEqual(len(result), 120)
        self.assertIn("已按输入预算裁剪", result)
        self.assertIn("请回答最后的问题", result)

    def test_apply_prompt_budget_uses_token_budget_estimate(self) -> None:
        from agent.orchestrator import Orchestrator

        prompt = "B" * 200
        result = Orchestrator._apply_prompt_budget(prompt, context={"max_prompt_tokens": 20})
        self.assertLessEqual(len(result), 80)

    def test_section_budget_preserves_profile_and_user_input(self) -> None:
        from agent.orchestrator import Orchestrator

        template = "P={{profile}}\nSTM={{stm}}\nR={{retrieval}}\nO={{open_source_signals}}\nU={{user_input}}"
        mapping = {
            "profile": "learning_goal: 考研数学",
            "stm": "S" * 1000,
            "retrieval": "R" * 1000,
            "open_source_signals": "O" * 1000,
            "knowledge_analysis": "",
            "context": "",
            "emotion": "neutral",
            "user_input": "请回答最后的问题",
        }

        trimmed = Orchestrator._apply_prompt_section_budget(template, mapping, context={"max_prompt_chars": 900})

        self.assertEqual(trimmed["profile"], "learning_goal: 考研数学")
        self.assertEqual(trimmed["user_input"], "请回答最后的问题")
        self.assertIn("已按区块预算裁剪", trimmed["stm"])
        self.assertIn("已按区块预算裁剪", trimmed["retrieval"])


if __name__ == "__main__":
    unittest.main()
