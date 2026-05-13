"""Factory helpers to build runtime components from unified config."""

from __future__ import annotations

from typing import Any

from agent.tools import MemorySearch
from llm import DeepSeekAdapter, MiMoAdapter, OllamaAdapter, OpenAIAdapter, QwenAdapter
from memory import OpenSourceMemoryHub

from .loader import AppConfig


_PROVIDER_CAPABILITIES: dict[str, dict[str, str | bool]] = {
    "mimo": {"implemented": True, "label": "MiMoAdapter", "reason": ""},
    "deepseek": {"implemented": True, "label": "DeepSeekAdapter", "reason": ""},
    "openai": {
        "implemented": True,
        "label": "OpenAIAdapter",
        "reason": "",
    },
    "qwen": {
        "implemented": True,
        "label": "QwenAdapter",
        "reason": "",
    },
    "ollama": {
        "implemented": True,
        "label": "OllamaAdapter",
        "reason": "",
    },
}


def get_provider_capability(provider: str) -> dict[str, str | bool]:
    normalized = provider.lower().strip()
    if normalized in _PROVIDER_CAPABILITIES:
        return dict(_PROVIDER_CAPABILITIES[normalized])
    return {
        "implemented": False,
        "label": normalized or "<empty>",
        "reason": "Provider is not supported by current factory.",
    }


class ResilientLLM:
    """Primary/backup LLM wrapper for graceful runtime fallback."""

    def __init__(self, primary: Any, backup: Any | None = None) -> None:
        self.primary = primary
        self.backup = backup

    @staticmethod
    def _is_retryable_runtime_error(exc: Exception) -> bool:
        text = str(exc).lower()
        signals = (
            "connection error",
            "timeout",
            "timed out",
            "httperror 429",
            "httperror 500",
            "httperror 502",
            "httperror 503",
            "httperror 504",
            "temporarily unavailable",
        )
        return any(s in text for s in signals)

    def generate(self, prompt: str, **kwargs: Any) -> str:
        try:
            return self.primary.generate(prompt, **kwargs)
        except Exception as primary_exc:  # noqa: BLE001
            if self.backup is None or not self._is_retryable_runtime_error(primary_exc):
                raise
            try:
                return self.backup.generate(prompt, **kwargs)
            except Exception as backup_exc:  # noqa: BLE001
                raise RuntimeError(
                    f"Primary LLM failed ({primary_exc}); backup LLM also failed ({backup_exc})."
                ) from backup_exc


def build_llm_from_config(cfg: AppConfig):
    provider = cfg.llm.provider.lower().strip()
    capability = get_provider_capability(provider)
    if not bool(capability["implemented"]):
        available = ", ".join(
            name for name, meta in _PROVIDER_CAPABILITIES.items() if bool(meta["implemented"])
        )
        reason = str(capability.get("reason") or "Provider is not implemented.")
        raise RuntimeError(
            f"llm.provider='{cfg.llm.provider}' is not fully implemented. {reason} "
            f"Use one of fully implemented providers: {available}."
        )

    if provider == "mimo":
        primary = MiMoAdapter(
            api_key=cfg.mimo.api_key,
            base_url=cfg.mimo.base_url,
            model=cfg.llm.model,
            timeout=cfg.llm.timeout,
            temperature=cfg.llm.temperature,
            top_p=cfg.llm.top_p,
            use_api_key_header=cfg.mimo.use_api_key_header,
        )
        backup = None
        if cfg.memory_analysis.provider.lower().strip() == "deepseek":
            ds_key = str(cfg.memory_analysis.api_key).strip()
            if ds_key:
                backup = DeepSeekAdapter(
                    api_key=ds_key,
                    base_url=cfg.memory_analysis.base_url,
                    model=cfg.memory_analysis.model,
                    timeout=min(cfg.llm.timeout, cfg.memory_analysis.timeout),
                )
        return ResilientLLM(primary=primary, backup=backup)
    if provider == "deepseek":
        return DeepSeekAdapter(
            api_key=cfg.deepseek.api_key,
            base_url=cfg.deepseek.base_url,
            model=cfg.llm.model,
            timeout=cfg.llm.timeout,
        )
    if provider == "openai":
        return OpenAIAdapter(
            api_key=cfg.openai.api_key,
            base_url=cfg.openai.base_url,
            model=cfg.llm.model,
            timeout=cfg.llm.timeout,
        )
    if provider == "qwen":
        return QwenAdapter(
            api_key=cfg.qwen.api_key,
            base_url=cfg.qwen.base_url,
            model=cfg.llm.model,
            timeout=cfg.llm.timeout,
        )
    if provider == "ollama":
        return OllamaAdapter(
            base_url=cfg.ollama.base_url,
            model=cfg.llm.model,
            timeout=cfg.llm.timeout,
        )
    raise ValueError(f"Unsupported llm.provider: {cfg.llm.provider}")


def build_memory_search_from_config(cfg: AppConfig) -> MemorySearch:
    memory_hub = OpenSourceMemoryHub(
        enable_mem0=cfg.memory_frameworks.enable_mem0,
        enable_llamaindex_memory=cfg.memory_frameworks.enable_llamaindex_memory,
        enable_cognee=cfg.memory_frameworks.enable_cognee,
        mem0_api_key=cfg.memory_frameworks.mem0_api_key,
        mem0_llm_api_key=cfg.deepseek.api_key,
        mem0_llm_base_url=cfg.deepseek.base_url,
        mem0_llm_model=cfg.deepseek.model,
        llamaindex_token_limit=cfg.memory_frameworks.llamaindex_token_limit,
        llamaindex_cloud_mode=cfg.memory_frameworks.llamaindex_cloud_mode,
        llamaindex_api_key=cfg.memory_frameworks.llamaindex_api_key,
        cognee_cloud_mode=cfg.memory_frameworks.cognee_cloud_mode,
        cognee_api_key=cfg.memory_frameworks.cognee_api_key,
        cognee_base_url=cfg.memory_frameworks.cognee_base_url,
        cognee_dataset_name=cfg.memory_frameworks.cognee_dataset_name,
        analysis_provider=cfg.memory_analysis.provider,
        analysis_model=cfg.memory_analysis.model,
        analysis_api_key=cfg.memory_analysis.api_key,
        analysis_base_url=cfg.memory_analysis.base_url,
        analysis_timeout=cfg.memory_analysis.timeout,
        analysis_use_api_key_header=cfg.memory_analysis.use_api_key_header,
    )
    return MemorySearch(
        db_path="memory.db",
        candidate_k=cfg.retrieval.candidate_k,
        top_k=cfg.retrieval.top_k,
        decay_lambda=cfg.retrieval.decay_lambda,
        retrieval_backend=cfg.retrieval.backend,
        open_source_memory_hub=memory_hub,
    )
