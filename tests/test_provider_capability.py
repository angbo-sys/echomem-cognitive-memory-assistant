from __future__ import annotations

import unittest

from config.factory import ResilientLLM, build_llm_from_config, get_provider_capability
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
from llm import DeepSeekAdapter


def _cfg(provider: str) -> AppConfig:
    return AppConfig(
        llm=LLMConfig(provider=provider, model="demo-model", timeout=10.0, temperature=1.0, top_p=0.9),
        mimo=MiMoConfig(api_key="k", base_url="https://token-plan-cn.xiaomimimo.com/v1", use_api_key_header=False),
        deepseek=DeepSeekConfig(api_key="dsk", base_url="https://api.deepseek.com/v1", model="deepseek-chat"),
        openai=OpenAIConfig(api_key="openai", base_url="https://openai.example.com/v1"),
        qwen=QwenConfig(api_key="qwen", base_url="https://qwen.example.com/api/v1"),
        ollama=OllamaConfig(base_url="http://ollama.example.com"),
        retrieval=RetrievalConfig(),
        memory_frameworks=MemoryFrameworkConfig(),
        memory_analysis=MemoryAnalysisConfig(),
    )


class TestProviderCapability(unittest.TestCase):
    def test_capability_for_mimo_is_implemented(self) -> None:
        meta = get_provider_capability("mimo")
        self.assertTrue(meta["implemented"])

    def test_capability_for_all_providers_are_implemented(self) -> None:
        for provider in ("openai", "qwen", "ollama"):
            meta = get_provider_capability(provider)
            self.assertTrue(meta["implemented"], f"{provider} should be implemented")

    def test_factory_builds_all_implemented_providers(self) -> None:
        from llm import OpenAIAdapter, QwenAdapter, OllamaAdapter

        self.assertIsInstance(build_llm_from_config(_cfg("openai")), OpenAIAdapter)
        self.assertIsInstance(build_llm_from_config(_cfg("qwen")), QwenAdapter)
        self.assertIsInstance(build_llm_from_config(_cfg("ollama")), OllamaAdapter)

    def test_factory_uses_unified_provider_config(self) -> None:
        openai = build_llm_from_config(_cfg("openai"))
        qwen = build_llm_from_config(_cfg("qwen"))
        ollama = build_llm_from_config(_cfg("ollama"))

        self.assertEqual(openai.api_key, "openai")
        self.assertEqual(openai.base_url, "https://openai.example.com/v1")
        self.assertEqual(qwen.api_key, "qwen")
        self.assertEqual(qwen.base_url, "https://qwen.example.com/api/v1")
        self.assertEqual(ollama.base_url, "http://ollama.example.com")

    def test_factory_builds_mimo_and_deepseek(self) -> None:
        self.assertIsInstance(build_llm_from_config(_cfg("mimo")), ResilientLLM)
        self.assertIsInstance(build_llm_from_config(_cfg("deepseek")), DeepSeekAdapter)


if __name__ == "__main__":
    unittest.main()
