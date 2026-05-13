from __future__ import annotations

import unittest
import tempfile

from agent import Orchestrator
from agent.tools import EmotionAnalyzer, MemorySearch
from memory import LongTermMemory, ShortTermMemory
from profile import ProfileManager


class FakeLLM:
    def generate(self, prompt: str, **kwargs):  # noqa: ANN001
        return "mocked response"


class FakeMemoryTool:
    def __init__(self) -> None:
        self.stored = None

    def run(self, **kwargs):  # noqa: ANN001
        return {
            "tool": "memory_search",
            "hits": [],
            "open_source_memory": {
                "framework_contributions": [
                    {
                        "framework": "mem0",
                        "role": "用户偏好/画像事实",
                        "signal_source": "fake",
                        "signal_count": 1,
                        "signals": ["偏好：简洁"],
                    }
                ]
            },
            "text": "",
        }

    def store_interaction(self, *, user_id: str, user_input: str, assistant_output: str):
        self.stored = {
            "user_id": user_id,
            "user_input": user_input,
            "assistant_output": assistant_output,
        }
        return {"mem0": {"stored": True, "role": "长期偏好/事实记忆"}}


class FakeProfile:
    def __init__(self) -> None:
        self.data: dict[str, dict[str, object]] = {}

    def get_profile(self, user_id: str) -> dict[str, object]:
        return dict(self.data.get(user_id, {}))

    def update_field(
        self,
        user_id: str,
        field: str,
        new_value: object,
        trigger: str,
        confidence: float,
    ) -> dict[str, object]:
        user_profile = self.data.setdefault(user_id, {})
        user_profile[field] = new_value
        return {"user_id": user_id, "profile": dict(user_profile), "trigger": trigger, "confidence": confidence}


class TestOrchestratorIntegration(unittest.TestCase):
    def test_run_returns_structured_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stm = ShortTermMemory(max_turns=3)
            profile = ProfileManager(db_path=f"{tmp}/profile.db")
            ltm = LongTermMemory(db_path=f"{tmp}/memory.db")
            ltm.add_memory(content="用户偏好：简洁", mtype="preference", importance=0.8, source="t")
            memory_tool = MemorySearch(ltm=ltm, top_k=3)
            orch = Orchestrator(
                stm=stm,
                profile=profile,
                emotion_tool=EmotionAnalyzer(),
                memory_tool=memory_tool,
                llm=FakeLLM(),
            )

            out = orch.run("请简洁回答", user_id="u_test")
            self.assertIn("response", out)
            self.assertEqual(out["response"], "mocked response")
            self.assertIn("retrieval", out)
            self.assertIn("top_hits=", out["prompt"])
            self.assertIn("profile_updates", out)
            self.assertIn("memory_evolution", out)

    def test_run_writes_turn_back_to_memory_frameworks(self) -> None:
        memory_tool = FakeMemoryTool()
        orch = Orchestrator(
            stm=ShortTermMemory(max_turns=3),
            profile=FakeProfile(),
            emotion_tool=EmotionAnalyzer(),
            memory_tool=memory_tool,
            llm=FakeLLM(),
        )

        out = orch.run("请简洁回答", user_id="u_test")

        self.assertEqual(memory_tool.stored["assistant_output"], "mocked response")
        self.assertTrue(out["framework_writes"]["mem0"]["stored"])
        self.assertTrue(out["retrieval"]["open_source_memory"]["framework_writes"]["mem0"]["stored"])
        self.assertIn("mem0 · 用户偏好/画像事实", out["prompt"])

    def test_internal_type_error_is_not_swallowed(self) -> None:
        def broken_component(**kwargs):  # noqa: ANN001
            raise TypeError("internal failure")

        with self.assertRaisesRegex(TypeError, "internal failure"):
            Orchestrator._safe_call(broken_component, query="q", user_id="u")

    def test_stm_writeback_and_profile_pipeline(self) -> None:
        stm = ShortTermMemory(max_turns=5)
        profile = FakeProfile()
        orch = Orchestrator(
            stm=stm,
            profile=profile,
            emotion_tool=EmotionAnalyzer(),
            memory_tool=None,
            llm=FakeLLM(),
        )

        out = orch.run("我的目标是考研英语，请简洁分步骤回答", user_id="u_test")
        recent = stm.get_recent()
        self.assertEqual(len(recent), 2)
        self.assertEqual(recent[0]["role"], "user")
        self.assertEqual(recent[1]["role"], "assistant")

        updates = out.get("profile_updates", [])
        self.assertTrue(any(u.get("field") == "learning_goal" and u.get("applied") for u in updates))
        self.assertTrue(any(u.get("field") == "preferred_style" and u.get("applied") for u in updates))

        saved_profile = profile.get_profile("u_test")
        # Regex now correctly stops at punctuation boundary
        self.assertEqual(saved_profile.get("learning_goal"), "考研英语")
        self.assertIn("preferred_style", saved_profile)

    def test_semantic_profile_pipeline_handles_natural_paraphrases(self) -> None:
        stm = ShortTermMemory(max_turns=5)
        profile = FakeProfile()
        orch = Orchestrator(
            stm=stm,
            profile=profile,
            emotion_tool=EmotionAnalyzer(),
            memory_tool=None,
            llm=FakeLLM(),
        )

        out = orch.run(
            "研究生是我接下来的方向，概率论总是卡住，讲题时请一步一步拆开讲",
            user_id="u_test",
        )

        updates = out.get("profile_updates", [])
        self.assertTrue(any(u.get("field") == "learning_goal" and u.get("applied") for u in updates))
        self.assertTrue(any(u.get("field") == "weak_subject" and u.get("applied") for u in updates))
        self.assertTrue(any(u.get("field") == "preferred_style" and u.get("applied") for u in updates))

        saved_profile = profile.get_profile("u_test")
        self.assertEqual(saved_profile.get("learning_goal"), "研究生")
        self.assertEqual(saved_profile.get("weak_subject"), "概率论")
        self.assertEqual(saved_profile.get("preferred_style"), "分步骤")

    def test_semantic_profile_pipeline_normalizes_level_and_focus(self) -> None:
        stm = ShortTermMemory(max_turns=5)
        profile = FakeProfile()
        orch = Orchestrator(
            stm=stm,
            profile=profile,
            emotion_tool=EmotionAnalyzer(),
            memory_tool=None,
            llm=FakeLLM(),
        )

        orch.run("我零基础，最近一直刷贝叶斯公式和条件概率", user_id="u_test")

        saved_profile = profile.get_profile("u_test")
        self.assertEqual(saved_profile.get("knowledge_level"), "入门")
        self.assertEqual(saved_profile.get("recent_focus"), "刷贝叶斯公式和条件概率")

    def test_memory_evolution_feedback_in_stm(self) -> None:
        """Applied profile updates should produce non-empty memory_evolution."""
        stm = ShortTermMemory(max_turns=5)
        profile = FakeProfile()
        orch = Orchestrator(
            stm=stm,
            profile=profile,
            emotion_tool=EmotionAnalyzer(),
            memory_tool=None,
            llm=FakeLLM(),
        )

        out = orch.run("我的目标是考研英语，请简洁分步骤回答", user_id="u_test")
        evolution = out.get("memory_evolution", [])
        applied = [e for e in evolution if e.get("applied")]
        self.assertGreater(len(applied), 0)

        # STM summary should contain evolution feedback
        summary = stm.get_summary()
        self.assertIsNotNone(summary)
        self.assertIn("画像更新", summary or "")

    def test_stm_summary_is_used_once_then_cleared_without_new_updates(self) -> None:
        stm = ShortTermMemory(max_turns=5)
        profile = FakeProfile()
        orch = Orchestrator(
            stm=stm,
            profile=profile,
            emotion_tool=EmotionAnalyzer(),
            memory_tool=None,
            llm=FakeLLM(),
        )

        orch.run("我的目标是考研英语，请简洁分步骤回答", user_id="u_test")
        self.assertIn("画像更新", stm.get_summary() or "")

        out = orch.run("普通问题", user_id="u_test")
        self.assertIn("画像更新", out["prompt"])
        self.assertIsNone(stm.get_summary())


if __name__ == "__main__":
    unittest.main()
