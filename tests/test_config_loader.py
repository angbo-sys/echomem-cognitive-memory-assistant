from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

import config.factory as factory
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
    load_config,
)


class TestConfigLoader(unittest.TestCase):
    def test_api_keys_resolve_through_unified_config_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cfg = base / "settings.toml"
            envf = base / ".env"
            cfg.write_text(
                textwrap.dedent(
                    """
                    [llm]
                    provider = "mimo"
                    model = "mimo-v2.5-pro"
                    timeout = 30.0
                    temperature = 1.0
                    top_p = 0.95

                    [mimo]
                    api_key = "mimo_from_toml"
                    base_url = "https://token-plan-cn.xiaomimimo.com/v1"
                    use_api_key_header = false

                    [deepseek]
                    api_key = "deepseek_from_toml"
                    base_url = "https://api.deepseek.com"
                    model = "deepseek-v4-flash"

                    [openai]
                    api_key = "openai_from_toml"
                    base_url = "https://openai.toml/v1"

                    [qwen]
                    api_key = "qwen_from_toml"
                    base_url = "https://qwen.toml/api/v1"

                    [ollama]
                    base_url = "http://ollama.toml"

                    [memory_analysis]
                    provider = "deepseek"
                    model = "deepseek-v4-flash"
                    timeout = 21.0
                    """
                ).strip(),
                encoding="utf-8",
            )
            envf.write_text(
                "MIMO_API_KEY=mimo_from_env_file\n"
                "DEEPSEEK_API_KEY=deepseek_from_env_file\n"
                "OPENAI_API_KEY=openai_from_env_file\n"
                "QWEN_API_KEY=qwen_from_env_file\n"
                "OLLAMA_BASE_URL=http://ollama.env\n"
                "MEMORY_ANALYSIS_PROVIDER=deepseek\n",
                encoding="utf-8",
            )

            loaded = load_config(config_path=cfg, env_path=envf)
            self.assertEqual(loaded.mimo.api_key, "mimo_from_env_file")
            self.assertEqual(loaded.deepseek.api_key, "deepseek_from_env_file")
            self.assertEqual(loaded.openai.api_key, "openai_from_env_file")
            self.assertEqual(loaded.openai.base_url, "https://openai.toml/v1")
            self.assertEqual(loaded.qwen.api_key, "qwen_from_env_file")
            self.assertEqual(loaded.ollama.base_url, "http://ollama.env")
            self.assertEqual(loaded.memory_analysis.provider, "deepseek")
            self.assertEqual(loaded.memory_analysis.model, "deepseek-v4-flash")
            self.assertEqual(loaded.memory_analysis.api_key, "deepseek_from_env_file")
            self.assertTrue(loaded.memory_frameworks.enable_mem0)
            self.assertTrue(loaded.memory_frameworks.enable_llamaindex_memory)
            self.assertTrue(loaded.memory_frameworks.enable_cognee)
            self.assertEqual(loaded.retrieval.backend, "chroma")

    def test_memory_analysis_uses_provider_key_without_local_api_key_field(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cfg = base / "settings.toml"
            cfg.write_text(
                textwrap.dedent(
                    """
                    [llm]
                    provider = "mimo"
                    model = "mimo-v2.5-pro"

                    [mimo]
                    api_key = "mimo_toml_key"
                    base_url = "https://token-plan-cn.xiaomimimo.com/v1"

                    [deepseek]
                    api_key = "deepseek_toml_key"
                    base_url = "https://api.deepseek.com"
                    model = "deepseek-v4-flash"

                    [memory_analysis]
                    provider = "deepseek"
                    """
                ).strip(),
                encoding="utf-8",
            )
            loaded = load_config(config_path=cfg, env_path=base / ".env")
            self.assertEqual(loaded.deepseek.api_key, "deepseek_toml_key")
            self.assertEqual(loaded.memory_analysis.api_key, "deepseek_toml_key")
            self.assertEqual(loaded.memory_analysis.base_url, "https://api.deepseek.com")

    def test_memory_frameworks_cloud_mode_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cfg = base / "settings.toml"
            cfg.write_text(
                textwrap.dedent(
                    """
                    [llm]
                    provider = "mimo"
                    model = "mimo-v2.5-pro"

                    [mimo]
                    api_key = "k"
                    base_url = "https://example.com"

                    [deepseek]
                    api_key = "k"
                    base_url = "https://example.com"
                    model = "m"

                    [memory_frameworks]
                    enable_mem0 = true
                    enable_llamaindex_memory = true
                    enable_cognee = true
                    llamaindex_token_limit = 5000
                    llamaindex_cloud_mode = true
                    cognee_cloud_mode = true
                    """
                ).strip(),
                encoding="utf-8",
            )
            loaded = load_config(config_path=cfg, env_path=base / ".env")
            self.assertEqual(loaded.memory_frameworks.llamaindex_token_limit, 5000)
            self.assertTrue(loaded.memory_frameworks.llamaindex_cloud_mode)
            self.assertTrue(loaded.memory_frameworks.cognee_cloud_mode)

    def test_memory_framework_api_keys_are_read_from_env_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cfg = base / "settings.toml"
            envf = base / ".env"
            cfg.write_text(
                textwrap.dedent(
                    """
                    [llm]
                    provider = "mimo"
                    model = "mimo-v2.5-pro"

                    [mimo]
                    api_key = "k"
                    base_url = "https://example.com"

                    [deepseek]
                    api_key = "k"
                    base_url = "https://example.com"
                    model = "m"

                    [memory_frameworks]
                    enable_mem0 = true
                    enable_llamaindex_memory = true
                    enable_cognee = true
                    """
                ).strip(),
                encoding="utf-8",
            )
            envf.write_text(
                "\n".join(
                    [
                        "MEM0_API_KEY=mem0-from-env-file",
                        "LLAMA_CLOUD_API_KEY=llama-from-env-file",
                        "COGNEE_API_KEY=cognee-from-env-file",
                        "COGNEE_BASE_URL=https://cognee.example.com",
                        "COGNEE_DATASET_NAME=unit-dataset",
                    ]
                ),
                encoding="utf-8",
            )

            loaded = load_config(config_path=cfg, env_path=envf)

            self.assertTrue(loaded.memory_frameworks.llamaindex_cloud_mode)
            self.assertTrue(loaded.memory_frameworks.cognee_cloud_mode)
            self.assertEqual(loaded.memory_frameworks.mem0_api_key, "mem0-from-env-file")
            self.assertEqual(loaded.memory_frameworks.llamaindex_api_key, "llama-from-env-file")
            self.assertEqual(loaded.memory_frameworks.cognee_api_key, "cognee-from-env-file")
            self.assertEqual(loaded.memory_frameworks.cognee_base_url, "https://cognee.example.com")
            self.assertEqual(loaded.memory_frameworks.cognee_dataset_name, "unit-dataset")

    def test_factory_passes_loaded_memory_framework_api_keys(self) -> None:
        captured = {}
        original_hub = factory.OpenSourceMemoryHub

        class FakeHub:
            def __init__(self, **kwargs):  # noqa: ANN001
                captured.update(kwargs)

        try:
            factory.OpenSourceMemoryHub = FakeHub
            cfg = AppConfig(
                llm=LLMConfig(),
                mimo=MiMoConfig(api_key="mimo"),
                deepseek=DeepSeekConfig(api_key="deepseek", model="deepseek-v4-flash"),
                openai=OpenAIConfig(api_key="openai"),
                qwen=QwenConfig(api_key="qwen"),
                ollama=OllamaConfig(),
                retrieval=RetrievalConfig(),
                memory_frameworks=MemoryFrameworkConfig(
                    mem0_api_key="mem0-key",
                    llamaindex_api_key="llama-key",
                    cognee_api_key="cognee-key",
                    cognee_base_url="https://cognee.example.com",
                    cognee_dataset_name="factory-dataset",
                    llamaindex_cloud_mode=True,
                    cognee_cloud_mode=True,
                ),
                memory_analysis=MemoryAnalysisConfig(api_key="analysis"),
            )
            factory.build_memory_search_from_config(cfg)
        finally:
            factory.OpenSourceMemoryHub = original_hub

        self.assertEqual(captured["mem0_api_key"], "mem0-key")
        self.assertEqual(captured["llamaindex_api_key"], "llama-key")
        self.assertEqual(captured["cognee_api_key"], "cognee-key")
        self.assertEqual(captured["cognee_base_url"], "https://cognee.example.com")
        self.assertEqual(captured["cognee_dataset_name"], "factory-dataset")


if __name__ == "__main__":
    unittest.main()
