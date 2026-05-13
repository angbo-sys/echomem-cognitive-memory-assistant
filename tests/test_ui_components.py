from __future__ import annotations

import unittest

from ui.components import (
    render_capability_map,
    render_memory_composition,
    render_memory_framework_lab,
    render_observation_header,
    render_profile_constellation,
)


class FakeStreamlit:
    def __init__(self) -> None:
        self.markdowns: list[tuple[str, bool]] = []

    def markdown(self, body: str, unsafe_allow_html: bool = False) -> None:
        self.markdowns.append((body, unsafe_allow_html))


class TestMemoryFrameworkLab(unittest.TestCase):
    def test_renders_framework_lanes_and_escapes_signals(self) -> None:
        fake = FakeStreamlit()
        render_memory_framework_lab(
            fake,
            {
                "scenario_routing": {"scenario": "preference"},
                "query_expansion": ["简洁回答"],
                "framework_contributions": [
                    {
                        "framework": "mem0",
                        "role": "用户偏好/画像事实",
                        "signal_source": "mem0_semantic_search",
                        "signal_count": 2,
                        "signals": ["偏好：分步骤", "<script>alert(1)</script>"],
                    },
                    {
                        "framework": "llamaindex_memory",
                        "role": "文档/会话知识命中",
                        "signal_source": "llamaindex_memory_buffer",
                        "signal_count": 1,
                        "signals": ["文档：贝叶斯公式"],
                    },
                    {
                        "framework": "cognee",
                        "role": "知识图谱关联概念",
                        "signal_source": "cognee_cloud_graph",
                        "signal_count": 1,
                        "signals": ["条件概率 -> 贝叶斯"],
                    },
                ],
                "framework_writes": {
                    "mem0": {"stored": True},
                    "llamaindex_memory": {"stored": True},
                    "cognee": {"stored": False},
                },
            },
        )

        self.assertEqual(len(fake.markdowns), 1)
        html, unsafe = fake.markdowns[0]
        self.assertTrue(unsafe)
        self.assertIn("三条记忆通道正在协同", html)
        self.assertIn("Mem0", html)
        self.assertIn("LlamaIndex", html)
        self.assertIn("Cognee", html)
        self.assertIn("已写回", html)
        self.assertIn("待写回", html)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert(1)</script>", html)


class TestObservationHeader(unittest.TestCase):
    def test_renders_page_header_with_escaped_chips(self) -> None:
        fake = FakeStreamlit()
        render_observation_header(
            fake,
            eyebrow="Overview",
            title="总览",
            subtitle="快速判断系统状态",
            chips=["检索", "<b>危险</b>"],
        )

        self.assertEqual(len(fake.markdowns), 1)
        html, unsafe = fake.markdowns[0]
        self.assertTrue(unsafe)
        self.assertIn("总览", html)
        self.assertIn("快速判断系统状态", html)
        self.assertIn("&lt;b&gt;危险&lt;/b&gt;", html)
        self.assertNotIn("<b>危险</b>", html)


class TestVisualObservationBlocks(unittest.TestCase):
    def test_memory_composition_escapes_type_labels(self) -> None:
        fake = FakeStreamlit()
        render_memory_composition(
            fake,
            [{"type": "<memory>", "status": "active", "count": 3, "avg_importance": 0.8}],
        )

        html, unsafe = fake.markdowns[0]
        self.assertTrue(unsafe)
        self.assertIn("总记忆", html)
        self.assertIn("&lt;memory&gt;", html)
        self.assertNotIn("<memory>", html)

    def test_profile_constellation_escapes_values(self) -> None:
        fake = FakeStreamlit()
        render_profile_constellation(fake, [("learning_goal", "<script>bad</script>")])

        html, unsafe = fake.markdowns[0]
        self.assertTrue(unsafe)
        self.assertIn("Profile", html)
        self.assertIn("&lt;script&gt;bad&lt;/script&gt;", html)
        self.assertNotIn("<script>bad</script>", html)

    def test_capability_map_renders_active_and_idle_nodes(self) -> None:
        fake = FakeStreamlit()
        render_capability_map(fake, {"stm": 1, "ltm": 0, "profile": 2, "evolution": 0, "emotion": 1, "tool": 0})

        html, unsafe = fake.markdowns[0]
        self.assertTrue(unsafe)
        self.assertIn("capability-node active", html)
        self.assertIn("capability-node idle", html)
        self.assertIn("短期上下文", html)


if __name__ == "__main__":
    unittest.main()
