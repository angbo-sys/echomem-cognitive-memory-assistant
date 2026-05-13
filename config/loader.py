"""Unified configuration loader for EchoMem.

Sources:
1) process environment overrides
2) .env local secrets and runtime overrides
3) config/settings.toml defaults

Secret policy:
- Runtime code reads credentials only from the AppConfig object returned here.
- Resolution order is process env > .env > settings.toml for local compatibility.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib


@dataclass(frozen=True)
class LLMConfig:
    provider: str = "mimo"
    model: str = "mimo-v2.5-pro"
    timeout: float = 30.0
    temperature: float = 1.0
    top_p: float = 0.95


@dataclass(frozen=True)
class MiMoConfig:
    api_key: str = ""
    base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    use_api_key_header: bool = False


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"


@dataclass(frozen=True)
class OpenAIConfig:
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"


@dataclass(frozen=True)
class QwenConfig:
    api_key: str = ""
    base_url: str = "https://dashscope.aliyuncs.com/api/v1"


@dataclass(frozen=True)
class OllamaConfig:
    base_url: str = "http://localhost:11434"


@dataclass(frozen=True)
class RetrievalConfig:
    backend: str = "chroma"
    candidate_k: int = 30
    top_k: int = 5
    decay_lambda: float = 0.05


@dataclass(frozen=True)
class MemoryFrameworkConfig:
    enable_mem0: bool = True
    enable_llamaindex_memory: bool = True
    enable_cognee: bool = True
    llamaindex_token_limit: int = 30000
    llamaindex_cloud_mode: bool = True
    cognee_cloud_mode: bool = True
    mem0_api_key: str = ""
    llamaindex_api_key: str = ""
    cognee_api_key: str = ""
    cognee_base_url: str = ""
    cognee_dataset_name: str = "echomem"


@dataclass(frozen=True)
class MemoryAnalysisConfig:
    provider: str = "mimo"
    model: str = "mimo-v2.5-pro"
    api_key: str = ""
    base_url: str = "https://token-plan-cn.xiaomimimo.com/v1"
    timeout: float = 20.0
    use_api_key_header: bool = False


@dataclass(frozen=True)
class AppConfig:
    llm: LLMConfig
    mimo: MiMoConfig
    deepseek: DeepSeekConfig
    openai: OpenAIConfig
    qwen: QwenConfig
    ollama: OllamaConfig
    retrieval: RetrievalConfig
    memory_frameworks: MemoryFrameworkConfig
    memory_analysis: MemoryAnalysisConfig


def _parse_env_file(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}
    parsed: dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        parsed[key] = value
    return parsed


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def load_config(
    *,
    config_path: str | Path = "config/settings.toml",
    env_path: str | Path = ".env",
) -> AppConfig:
    config_file = Path(config_path)
    env_file = Path(env_path)

    if not config_file.exists():
        raise RuntimeError(f"Config file not found: {config_file}")

    raw = tomllib.loads(config_file.read_text(encoding="utf-8"))
    env_data = _parse_env_file(env_file)

    # Read-only env resolution: process env > .env > settings.toml
    def _get(name: str, default: Any) -> Any:
        if name in os.environ:
            return os.environ[name]
        if name in env_data:
            return env_data[name]
        return default

    llm_raw = raw.get("llm", {})
    mimo_raw = raw.get("mimo", {})
    deepseek_raw = raw.get("deepseek", {})
    openai_raw = raw.get("openai", {})
    qwen_raw = raw.get("qwen", {})
    ollama_raw = raw.get("ollama", {})
    retrieval_raw = raw.get("retrieval", {})
    memory_raw = raw.get("memory_frameworks", {})
    memory_analysis_raw = raw.get("memory_analysis", {})

    llm = LLMConfig(
        provider=str(_get("LLM_PROVIDER", llm_raw.get("provider", "mimo"))),
        model=str(_get("LLM_MODEL", llm_raw.get("model", "mimo-v2.5-pro"))),
        timeout=float(_get("LLM_TIMEOUT", llm_raw.get("timeout", 30.0))),
        temperature=float(_get("LLM_TEMPERATURE", llm_raw.get("temperature", 1.0))),
        top_p=float(_get("LLM_TOP_P", llm_raw.get("top_p", 0.95))),
    )
    mimo = MiMoConfig(
        api_key=str(_get("MIMO_API_KEY", mimo_raw.get("api_key", ""))),
        base_url=str(_get("MIMO_BASE_URL", mimo_raw.get("base_url", "https://token-plan-cn.xiaomimimo.com/v1"))),
        use_api_key_header=_bool(
            _get("MIMO_USE_API_KEY_HEADER", mimo_raw.get("use_api_key_header", False))
        ),
    )
    deepseek = DeepSeekConfig(
        api_key=str(_get("DEEPSEEK_API_KEY", deepseek_raw.get("api_key", ""))),
        base_url=str(
            _get(
                "DEEPSEEK_BASE_URL",
                deepseek_raw.get(
                    "base_url",
                    memory_analysis_raw.get("base_url", "https://api.deepseek.com"),
                ),
            )
        ),
        model=str(
            _get(
                "DEEPSEEK_MODEL",
                deepseek_raw.get("model", memory_analysis_raw.get("model", "deepseek-v4-flash")),
            )
        ),
    )
    openai = OpenAIConfig(
        api_key=str(_get("OPENAI_API_KEY", openai_raw.get("api_key", ""))),
        base_url=str(_get("OPENAI_BASE_URL", openai_raw.get("base_url", "https://api.openai.com/v1"))),
    )
    qwen = QwenConfig(
        api_key=str(_get("QWEN_API_KEY", qwen_raw.get("api_key", ""))),
        base_url=str(_get("QWEN_BASE_URL", qwen_raw.get("base_url", "https://dashscope.aliyuncs.com/api/v1"))),
    )
    ollama = OllamaConfig(
        base_url=str(_get("OLLAMA_BASE_URL", ollama_raw.get("base_url", "http://localhost:11434"))),
    )
    retrieval = RetrievalConfig(
        backend=str(_get("RETRIEVAL_BACKEND", retrieval_raw.get("backend", "chroma"))),
        candidate_k=int(_get("RETRIEVAL_CANDIDATE_K", retrieval_raw.get("candidate_k", 30))),
        top_k=int(_get("RETRIEVAL_TOP_K", retrieval_raw.get("top_k", 5))),
        decay_lambda=float(
            _get("RETRIEVAL_DECAY_LAMBDA", retrieval_raw.get("decay_lambda", 0.05))
        ),
    )
    memory_frameworks = MemoryFrameworkConfig(
        enable_mem0=_bool(_get("MEMORY_ENABLE_MEM0", memory_raw.get("enable_mem0", True)), True),
        enable_llamaindex_memory=_bool(
            _get("MEMORY_ENABLE_LLAMAINDEX_MEMORY", memory_raw.get("enable_llamaindex_memory", True)),
            True,
        ),
        enable_cognee=_bool(_get("MEMORY_ENABLE_COGNEE", memory_raw.get("enable_cognee", True)), True),
        llamaindex_token_limit=int(
            _get("LLAMAINDEX_TOKEN_LIMIT", memory_raw.get("llamaindex_token_limit", 30000))
        ),
        llamaindex_cloud_mode=_bool(
            _get("LLAMAINDEX_CLOUD_MODE", memory_raw.get("llamaindex_cloud_mode", True)), True
        ),
        cognee_cloud_mode=_bool(
            _get("COGNEE_CLOUD_MODE", memory_raw.get("cognee_cloud_mode", True)), True
        ),
        mem0_api_key=str(_get("MEM0_API_KEY", memory_raw.get("mem0_api_key", ""))),
        llamaindex_api_key=str(_get("LLAMA_CLOUD_API_KEY", memory_raw.get("llamaindex_api_key", ""))),
        cognee_api_key=str(_get("COGNEE_API_KEY", memory_raw.get("cognee_api_key", ""))),
        cognee_base_url=str(_get("COGNEE_BASE_URL", memory_raw.get("cognee_base_url", ""))),
        cognee_dataset_name=str(_get("COGNEE_DATASET_NAME", memory_raw.get("cognee_dataset_name", "echomem"))),
    )
    memory_analysis_provider = str(
        _get("MEMORY_ANALYSIS_PROVIDER", memory_analysis_raw.get("provider", "mimo"))
    ).strip().lower()
    if memory_analysis_provider == "deepseek":
        default_model = deepseek.model
        default_base_url = deepseek.base_url
        default_api_key = deepseek.api_key
    else:
        default_model = llm.model
        default_base_url = mimo.base_url
        default_api_key = mimo.api_key
    memory_analysis = MemoryAnalysisConfig(
        provider=memory_analysis_provider,
        model=str(_get("MEMORY_ANALYSIS_MODEL", memory_analysis_raw.get("model", default_model))),
        api_key=default_api_key,
        base_url=str(
            _get(
                "MEMORY_ANALYSIS_BASE_URL",
                memory_analysis_raw.get("base_url", default_base_url),
            )
        ),
        timeout=float(
            _get(
                "MIMO_ANALYSIS_TIMEOUT",
                _get(
                    "MEMORY_ANALYSIS_TIMEOUT",
                    memory_analysis_raw.get("timeout", llm.timeout),
                ),
            )
        ),
        use_api_key_header=_bool(
            _get(
                "MEMORY_ANALYSIS_USE_API_KEY_HEADER",
                memory_analysis_raw.get("use_api_key_header", mimo.use_api_key_header),
            ),
            False,
        ),
    )
    return AppConfig(
        llm=llm,
        mimo=mimo,
        deepseek=deepseek,
        openai=openai,
        qwen=qwen,
        ollama=ollama,
        retrieval=retrieval,
        memory_frameworks=memory_frameworks,
        memory_analysis=memory_analysis,
    )
