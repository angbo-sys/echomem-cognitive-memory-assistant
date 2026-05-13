from __future__ import annotations

import tempfile
import time
import unittest

from agent.tools import MemorySearch
from config.factory import build_memory_search_from_config
from config.loader import (
    AppConfig,
    DeepSeekConfig,
    LLMConfig,
    MemoryAnalysisConfig,
    MemoryFrameworkConfig,
    MiMoConfig,
    OllamaConfig,
    OpenAIConfig,
    QwenConfig,
    RetrievalConfig,
)
from memory import LongTermMemory
from memory.retrieval import lexical_similarity
from memory.open_source_memory import MimoKnowledgeAnalyzer


class SlowAnalysisLLM:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, prompt: str, **kwargs):  # noqa: ANN001
        self.calls += 1
        time.sleep(0.05)
        return "cached knowledge summary"


class TestMemorySearch(unittest.TestCase):
    def test_search_returns_ranked_hits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = f"{tmp}/memory.db"
            ltm = LongTermMemory(db_path=db)
            ltm.add_memory(content="用户偏好：回答简洁", mtype="preference", importance=0.9, source="t")
            ltm.add_memory(content="用户准备考试", mtype="goal", importance=0.8, source="t")
            tool = MemorySearch(ltm=ltm, top_k=2)

            out = tool.run(query="简洁回答")
            self.assertIn("hits", out)
            self.assertGreaterEqual(len(out["hits"]), 1)
            self.assertIn("decayed_score", out["hits"][0])

    def test_chinese_similarity_handles_semantic_overlap_without_spaces(self) -> None:
        related = lexical_similarity("条件概率", "概率论知识：贝叶斯公式用于条件概率推断")
        unrelated = lexical_similarity("条件概率", "用户偏好：回答简洁，避免术语堆叠")

        self.assertGreater(related, 0.0)
        self.assertGreater(related, unrelated)

    def test_chroma_backend_retrieves_and_filters_by_user_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = f"{tmp}/memory.db"
            ltm = LongTermMemory(db_path=db)
            ltm.add_memory(
                content="概率论知识：贝叶斯公式用于条件概率推断",
                mtype="knowledge",
                importance=0.9,
                source="t",
                user_id="u1",
            )
            ltm.add_memory(
                content="英语复习：每天背单词",
                mtype="knowledge",
                importance=0.9,
                source="t",
                user_id="u2",
            )
            tool = MemorySearch(
                ltm=ltm,
                top_k=3,
                retrieval_backend="chroma",
                vector_persist_path=f"{tmp}/chroma",
            )
            if not tool.vector_store.available:
                self.skipTest("chromadb is not available in this environment")

            out = tool.run(query="条件概率", context={"user_id": "u1"})
            self.assertEqual(out["backend"], "vector")
            self.assertTrue(out["hits"])
            self.assertTrue(all(hit.get("user_id") == "u1" for hit in out["hits"]))

    def test_search_respects_type_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = f"{tmp}/memory.db"
            ltm = LongTermMemory(db_path=db)
            ltm.add_memory(content="用户偏好：回答简洁", mtype="preference", importance=0.9, source="t")
            ltm.add_memory(content="用户目标：准备考试", mtype="goal", importance=0.8, source="t")
            tool = MemorySearch(ltm=ltm, top_k=5)

            out = tool.run(query="用户", context={"mtype_filter": "goal"})
            self.assertTrue(all(hit.get("type") == "goal" for hit in out["hits"]))
            self.assertIn("open_source_memory", out)
            self.assertIn("mem0", out["open_source_memory"])
            self.assertIn("llamaindex_memory", out["open_source_memory"])
            self.assertIn("cognee", out["open_source_memory"])
            self.assertIn("mimo_analysis", out["open_source_memory"])
            self.assertIn("scenario_routing", out["open_source_memory"])
            mimo = out["open_source_memory"].get("mimo_analysis", {})
            self.assertFalse(mimo.get("enabled", True))

    def test_search_skips_invalid_timestamp_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = f"{tmp}/memory.db"
            ltm = LongTermMemory(db_path=db)
            ltm.add_memory(content="有效记忆", mtype="fact", importance=0.9, source="t")
            ltm.add_memory(content="无效时间戳记忆", mtype="fact", importance=0.7, source="t", ts="not-a-time")
            tool = MemorySearch(ltm=ltm, top_k=5)

            out = tool.run(query="记忆")
            contents = [hit.get("content") for hit in out["hits"]]
            self.assertIn("有效记忆", contents)
            self.assertNotIn("无效时间戳记忆", contents)

    def test_scenario_routing_prefers_mem0_for_preference_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db = f"{tmp}/memory.db"
            ltm = LongTermMemory(db_path=db)
            ltm.add_memory(content="用户偏好：回答简洁，避免术语堆叠", mtype="preference", importance=0.9, source="t")
            ltm.add_memory(content="用户在准备机器学习考试", mtype="goal", importance=0.8, source="t")
            tool = MemorySearch(ltm=ltm, top_k=3)

            out = tool.run(query="请按我的偏好风格回答", context={"user_id": "demo_user"})
            routing = out["open_source_memory"].get("scenario_routing", {})
            self.assertEqual(routing.get("scenario"), "preference_alignment")
            self.assertEqual(routing.get("framework_priority", [None])[0], "mem0")

    def test_memory_search_compatible_with_injected_memory_analysis_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg = AppConfig(
                llm=LLMConfig(),
                mimo=MiMoConfig(),
                deepseek=DeepSeekConfig(),
                openai=OpenAIConfig(),
                qwen=QwenConfig(),
                ollama=OllamaConfig(),
                retrieval=RetrievalConfig(top_k=3),
                memory_frameworks=MemoryFrameworkConfig(),
                memory_analysis=MemoryAnalysisConfig(
                    provider="deepseek",
                    model="deepseek-chat",
                    api_key="",
                    base_url="https://api.deepseek.com/v1",
                    timeout=15.0,
                ),
            )
            tool = build_memory_search_from_config(cfg)
            tool.ltm = LongTermMemory(db_path=f"{tmp}/memory.db")
            tool.ltm.add_memory(content="用户喜欢按步骤解释", mtype="preference", importance=0.8, source="t")
            out = tool.run(query="按我的偏好来")
            self.assertIn("open_source_memory", out)
            mimo = out["open_source_memory"].get("mimo_analysis", {})
            self.assertFalse(mimo.get("enabled", True))

    def test_mimo_analysis_times_out_then_uses_background_cache(self) -> None:
        analyzer = MimoKnowledgeAnalyzer(api_key="test-key", timeout=1.0)
        analyzer._llm = SlowAnalysisLLM()
        analyzer.enabled = True
        analyzer._wait_timeout = 0.01
        graph = {"nodes": ["数学"], "edges": [], "mermaid": "graph TD"}

        first = analyzer.analyze("总结知识体系", graph, enabled=True)
        self.assertEqual(first.get("reason"), "timeout_degraded")
        self.assertEqual(first.get("summary"), "")

        time.sleep(0.08)
        second = analyzer.analyze("总结知识体系", graph, enabled=True)
        self.assertEqual(second.get("summary"), "cached knowledge summary")
        self.assertTrue(second.get("cache_hit"))


if __name__ == "__main__":
    unittest.main()
