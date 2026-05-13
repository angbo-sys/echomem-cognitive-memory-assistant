from __future__ import annotations

import unittest

from memory.open_source_memory import (
    CogneeAdapter,
    CogneeCloudAdapter,
    LlamaCloudAdapter,
    LlamaIndexMemoryAdapter,
    Mem0Adapter,
    OpenSourceMemoryHub,
)


class TestOpenSourceMemorySignals(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            {
                "user_id": "u1",
                "content": "用户偏好：回答简洁，喜欢分步骤说明",
                "type": "preference",
            },
            {
                "user_id": "u1",
                "content": "用户目标：准备机器学习考试，重点复习概率论",
                "type": "goal",
            },
            {
                "user_id": "u1",
                "content": "概率论知识：贝叶斯公式用于条件概率推断",
                "type": "knowledge",
            },
        ]

    def test_mem0_signal_extracts_profile_facts(self) -> None:
        out = Mem0Adapter().get_user_facts("u1", self.rows, "按我的偏好回答")

        self.assertIn(out.details["signal_source"], ("mem0_local_profile_index", "mem0_enhanced_fallback", "mem0_semantic_search"))
        self.assertTrue(out.details["preferences"])
        self.assertIn("facts", out.details)

    def test_llamaindex_signal_has_memory_specific_fields(self) -> None:
        out = LlamaIndexMemoryAdapter().retrieve("解释概率论", self.rows)

        self.assertIn("signal_source", out.details)
        self.assertIn("doc_hits", out.details)
        self.assertIn("memory_items", out.details)

    def test_cognee_signal_builds_concept_graph(self) -> None:
        out = CogneeAdapter().related_concepts("概率论 贝叶斯", self.rows)

        self.assertIn("signal_source", out.details)
        self.assertIn("related_concepts", out.details)
        self.assertIn("concept_edges", out.details)

    def test_hub_reports_framework_status_and_distinct_sources(self) -> None:
        hub = OpenSourceMemoryHub()
        out = hub.collect_hints(
            user_id="u1",
            query="解释概率论和贝叶斯公式",
            stm_text="user: 继续讲概率论\nassistant: 先看贝叶斯公式",
            ltm_rows=self.rows,
            enable_mimo_analysis=False,
        )

        status = out.get("framework_status", {})
        self.assertEqual(
            set(status),
            {"mem0", "llamaindex_memory", "cognee"},
        )
        sources = {item.get("signal_source") for item in status.values()}
        self.assertGreaterEqual(len(sources), 3)
        self.assertIn("query_expansion", out)

    def test_query_expansion_nonempty_with_relevant_memories(self) -> None:
        """query_expansion should produce non-empty results when memories match."""
        hub = OpenSourceMemoryHub()
        out = hub.collect_hints(
            user_id="u1",
            query="我数学不好，概率论薄弱",
            stm_text="",
            ltm_rows=self.rows,
            enable_mimo_analysis=False,
        )
        expansion = out.get("query_expansion", [])
        self.assertIsInstance(expansion, list)
        self.assertGreater(len(expansion), 0, "query_expansion should be non-empty with matching memories")

    def test_all_three_frameworks_return_valuable_distinct_content(self) -> None:
        hub = OpenSourceMemoryHub()
        rows = self.rows + [
            {
                "user_id": "u1",
                "content": '{"field": "preferred_style", "user_id": "u1", "value": "详细举例"}',
                "type": "profile_field",
            }
        ]
        out = hub.collect_hints(
            user_id="u1",
            query="按我的偏好详细解释概率论和贝叶斯关系",
            stm_text="user: 继续讲概率论",
            ltm_rows=rows,
            enable_mimo_analysis=False,
        )

        contributions = out.get("framework_contributions", [])
        by_framework = {item.get("framework"): item for item in contributions}
        self.assertEqual(set(by_framework), {"mem0", "llamaindex_memory", "cognee"})
        for name in ("mem0", "llamaindex_memory", "cognee"):
            item = by_framework[name]
            self.assertEqual(item.get("signal_quality"), "valuable", name)
            self.assertTrue(item.get("used_in_query_expansion"), name)
            self.assertGreater(item.get("signal_count", 0), 0, name)
            self.assertTrue(item.get("signals"), name)
            self.assertTrue(item.get("value_summary"), name)

        mem0_text = " ".join(by_framework["mem0"]["signals"])
        llama_text = " ".join(by_framework["llamaindex_memory"]["signals"])
        cognee_text = " ".join(by_framework["cognee"]["signals"])
        self.assertTrue("偏好" in mem0_text or "preferred_style" in mem0_text)
        self.assertIn("概率论", llama_text)
        self.assertTrue("贝叶斯" in cognee_text or "条件概率" in cognee_text)
        self.assertGreaterEqual(len(out.get("query_expansion", [])), 3)


class TestLlamaCloudAdapter(unittest.TestCase):
    def test_unavailable_without_api_key(self) -> None:
        adapter = LlamaCloudAdapter(api_key="")
        self.assertFalse(adapter.available)
        self.assertIsNone(adapter.parse_document("test.pdf"))
        self.assertIsNone(adapter.extract_structured("test.pdf", {}))

    def test_unavailable_with_invalid_key(self) -> None:
        adapter = LlamaCloudAdapter(api_key="invalid-key-12345")
        # Without llama_cloud installed or with bad key, should be unavailable
        # If llama_cloud is installed, it will be available but API calls will fail gracefully
        if adapter.available:
            result = adapter.parse_document("nonexistent.pdf")
            self.assertIsNone(result)

    def test_parse_text_uses_llamaparse_markdown(self) -> None:
        adapter = LlamaCloudAdapter(api_key="")
        adapter.available = True

        class FakePage:
            markdown = "parsed text"

        class FakeMarkdown:
            pages = [FakePage()]

        class FakeParsing:
            def __init__(self) -> None:
                self.kwargs = None

            def parse(self, **kwargs):  # noqa: ANN001
                self.kwargs = kwargs

                class Result:
                    markdown = FakeMarkdown()

                return Result()

        class FakeClient:
            def __init__(self) -> None:
                self.parsing = FakeParsing()

        fake = FakeClient()
        adapter._client = fake

        self.assertEqual(adapter.parse_text("hello"), "parsed text")
        self.assertEqual(fake.parsing.kwargs["tier"], "cost_effective")
        self.assertEqual(fake.parsing.kwargs["expand"], ["markdown"])


class TestCogneeCloudAdapter(unittest.TestCase):
    def test_unavailable_without_config(self) -> None:
        adapter = CogneeCloudAdapter(api_key="", base_url="")
        self.assertFalse(adapter.available)
        self.assertFalse(adapter.add_knowledge(["test"]))
        self.assertEqual(adapter.search_graph("test"), [])

    def test_unavailable_without_base_url(self) -> None:
        adapter = CogneeCloudAdapter(api_key="test-key", base_url="")
        self.assertFalse(adapter.available)

    def test_available_with_config(self) -> None:
        adapter = CogneeCloudAdapter(api_key="test-key", base_url="https://example.com")
        self.assertTrue(adapter.available)

    def test_cloud_adapter_uses_current_cognee_api_schema(self) -> None:
        calls = []

        class FakeCloud(CogneeCloudAdapter):
            def _request(self, method, path, **kwargs):  # noqa: ANN001
                calls.append((method, path, kwargs.get("json")))
                if path == "/api/v1/search":
                    return [{"search_result": "graph context"}]
                return {"ok": True}

        adapter = FakeCloud(api_key="test-key", base_url="https://example.com", dataset_name="unit_ds")

        self.assertTrue(adapter.add_knowledge(["alpha", "beta"]))
        self.assertEqual(adapter.search_graph("alpha"), ["graph context"])
        self.assertEqual(calls[0], (
            "POST",
            "/api/v1/add_text",
            {"textData": ["alpha", "beta"], "datasetName": "unit_ds"},
        ))
        self.assertEqual(calls[1], (
            "POST",
            "/api/v1/cognify",
            {"datasets": ["unit_ds"], "runInBackground": False},
        ))
        self.assertEqual(calls[2], (
            "POST",
            "/api/v1/search",
            {"query": "alpha", "datasets": ["unit_ds"], "topK": 5, "onlyContext": True},
        ))


class TestLlamaIndexMemoryAdapterEnhanced(unittest.TestCase):
    def test_add_conversation(self) -> None:
        adapter = LlamaIndexMemoryAdapter(token_limit=10000)
        if adapter.available:
            result = adapter.add_conversation("用户消息", "助手回复")
            self.assertIsInstance(result, bool)

    def test_token_limit_configurable(self) -> None:
        adapter = LlamaIndexMemoryAdapter(token_limit=5000)
        self.assertTrue(adapter.available)


class TestCogneeAdapterWithCloud(unittest.TestCase):
    def test_cloud_adapter_integration(self) -> None:
        cloud = CogneeCloudAdapter(api_key="test", base_url="https://example.com")
        adapter = CogneeAdapter(cloud_adapter=cloud, enable_local=False)
        self.assertTrue(adapter.available)
        self.assertIs(adapter._cloud, cloud)
        self.assertIsNone(adapter._cognee)


class FakeCogneeModule:
    def __init__(self) -> None:
        self.added: list[str] = []
        self.cognified = False

    async def add(self, text: str) -> None:
        self.added.append(text)

    async def cognify(self) -> None:
        self.cognified = True

    async def search(self, query: str):  # noqa: ANN001
        return [f"graph hit: {query}", "贝叶斯网络"]


class FakeMem0:
    def __init__(self) -> None:
        self.stored: list[tuple[str, str]] = []

    def get_user_facts(self, user_id, ltm_rows, query):  # noqa: ANN001
        return type(
            "Hint",
            (),
            {
                "available": True,
                "details": {
                    "available": True,
                    "signal_source": "fake_mem0",
                    "facts": ["偏好：简洁"],
                    "preferences": ["偏好：简洁"],
                    "goals": [],
                },
            },
        )()

    def store(self, content, user_id, metadata=None):  # noqa: ANN001
        self.stored.append((user_id, content))
        return True


class FakeLlamaIndex:
    def __init__(self) -> None:
        self.turns: list[tuple[str, str]] = []
        self.rows_seen = []

    def retrieve(self, query, ltm_rows):  # noqa: ANN001
        self.rows_seen = list(ltm_rows)
        return type(
            "Hint",
            (),
            {
                "available": True,
                "details": {
                    "available": True,
                    "signal_source": "fake_llamaindex",
                    "doc_hits": ["文档：贝叶斯公式"],
                    "memory_items": ["文档：贝叶斯公式"],
                },
            },
        )()

    def add_conversation(self, user_input, assistant_output):  # noqa: ANN001
        self.turns.append((user_input, assistant_output))
        return True


class FakeCogneeAdapter:
    def __init__(self) -> None:
        self.added: list[list[str]] = []

    def related_concepts(self, query, ltm_rows):  # noqa: ANN001
        return type(
            "Hint",
            (),
            {
                "available": True,
                "details": {
                    "available": True,
                    "signal_source": "fake_cognee",
                    "related_concepts": ["条件概率", "贝叶斯网络"],
                    "concept_edges": [],
                },
            },
        )()

    async def add_knowledge(self, texts):  # noqa: ANN001
        self.added.append(list(texts))
        return True

    def _run_async_blocking(self, coro):  # noqa: ANN001
        import asyncio

        return asyncio.run(coro)


class TestCogneeAdapterLocalGraph(unittest.TestCase):
    def test_related_concepts_uses_local_async_graph_search(self) -> None:
        fake = FakeCogneeModule()
        adapter = CogneeAdapter()
        adapter._cognee = fake
        adapter.available = True

        rows = [
            {"content": "概率论知识：贝叶斯公式用于条件概率推断", "type": "knowledge"},
        ]
        out = adapter.related_concepts("条件概率", rows)

        self.assertTrue(fake.cognified)
        self.assertTrue(out.details["local_graph_search_used"])
        self.assertEqual(out.details["signal_source"], "cognee_local_graph_search")
        self.assertIn("贝叶斯网络", out.details["related_concepts"])


class TestOpenSourceMemoryHubFullIntegration(unittest.TestCase):
    def test_collect_hints_reports_distinct_framework_contributions(self) -> None:
        hub = OpenSourceMemoryHub(enable_mem0=False, enable_llamaindex_memory=False, enable_cognee=False)
        hub.mem0 = FakeMem0()
        hub.llamaindex = FakeLlamaIndex()
        hub.cognee = FakeCogneeAdapter()

        out = hub.collect_hints(
            user_id="u1",
            query="解释条件概率",
            stm_text="",
            ltm_rows=[{"user_id": "u1", "content": "贝叶斯公式用于条件概率", "type": "knowledge"}],
            enable_mimo_analysis=False,
        )

        contributions = out.get("framework_contributions", [])
        self.assertEqual([c.get("framework") for c in contributions], ["mem0", "llamaindex_memory", "cognee"])
        self.assertEqual(contributions[0].get("role"), "用户偏好/画像事实")
        self.assertEqual(contributions[1].get("role"), "文档/会话知识命中")
        self.assertEqual(contributions[2].get("role"), "知识图谱关联概念")
        self.assertTrue(all(c.get("used_in_query_expansion") for c in contributions))
        self.assertTrue(all(c.get("signal_quality") == "valuable" for c in contributions))
        self.assertIn("偏好：简洁", out.get("query_expansion", []))
        self.assertIn("文档：贝叶斯公式", out.get("query_expansion", []))
        self.assertIn("条件概率", out.get("query_expansion", []))

    def test_store_interaction_writes_to_all_frameworks(self) -> None:
        hub = OpenSourceMemoryHub(enable_mem0=False, enable_llamaindex_memory=False, enable_cognee=False)
        hub.mem0 = FakeMem0()
        hub.llamaindex = FakeLlamaIndex()
        hub.cognee = FakeCogneeAdapter()

        writes = hub.store_interaction(user_id="u1", user_input="问题", assistant_output="回答")

        self.assertTrue(writes["mem0"]["stored"])
        self.assertTrue(writes["llamaindex_memory"]["stored"])
        self.assertTrue(writes["cognee"]["stored"])

    def test_llamacloud_parse_augments_llamaindex_context_when_available(self) -> None:
        class FakeLlamaCloud:
            available = True

            def __init__(self) -> None:
                self.calls = []

            def parse_text(self, text, filename="document.txt"):  # noqa: ANN001
                self.calls.append((text, filename))
                return "LlamaCloud 解析结果：贝叶斯公式用于条件概率推断"

        hub = OpenSourceMemoryHub(enable_mem0=False, enable_llamaindex_memory=False, enable_cognee=False)
        hub.mem0 = FakeMem0()
        hub.llamaindex = FakeLlamaIndex()
        hub.cognee = FakeCogneeAdapter()
        hub.llama_cloud = FakeLlamaCloud()

        out = hub.collect_hints(
            user_id="u1",
            query="解释贝叶斯",
            stm_text="",
            ltm_rows=[{"user_id": "u1", "content": "概率论知识：贝叶斯公式用于条件概率推断", "type": "knowledge"}],
            enable_mimo_analysis=False,
        )

        self.assertTrue(hub.llama_cloud.calls)
        self.assertTrue(out["llamacloud_parse"]["cloud_api_used"])
        self.assertEqual(out["llamacloud_parse"]["signal_source"], "llamacloud_parse")
        self.assertEqual(hub.llamaindex.rows_seen[0]["type"], "llamacloud_parsed_memory")
        self.assertIn("LlamaCloud 解析结果", hub.llamaindex.rows_seen[0]["content"])


class TestOpenSourceMemoryHubWithCloudConfig(unittest.TestCase):
    def test_hub_accepts_cloud_params(self) -> None:
        hub = OpenSourceMemoryHub(
            enable_mem0=False,
            enable_llamaindex_memory=True,
            enable_cognee=True,
            llamaindex_token_limit=5000,
            cognee_cloud_mode=False,
        )
        self.assertIsNotNone(hub.llamaindex)
        self.assertIsNotNone(hub.cognee)


if __name__ == "__main__":
    unittest.main()
