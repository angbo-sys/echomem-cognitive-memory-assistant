from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
LOCAL_DEPS = ROOT / ".deps" / f"py{sys.version_info.major}{sys.version_info.minor}"
if LOCAL_DEPS.exists() and str(LOCAL_DEPS) not in sys.path:
    sys.path.append(str(LOCAL_DEPS))

from config.loader import load_config


MODULES = {
    "mem0": "mem0",
    "llama_cloud": "llama_cloud",
    "llama_index_core": "llama_index.core",
    "llama_index_ollama": "llama_index.llms.ollama",
    "llama_index_chroma": "llama_index.vector_stores.chroma",
    "cognee": "cognee",
    "chromadb": "chromadb",
}


def main() -> int:
    result: dict[str, Any] = {}
    modules_ok = True
    for name, module_path in MODULES.items():
        spec = importlib.util.find_spec(module_path)
        if spec is None:
            modules_ok = False
            result[name] = {"installed": False, "error": "module not found"}
            continue
        # Use find_spec only: importing frameworks like Cognee can run startup
        # migrations/logging and pollute this lightweight environment check.
        result[name] = {"installed": True}

    cfg = load_config()

    def _mask(value: str) -> str:
        s = (value or "").strip()
        if not s:
            return "<empty>"
        if len(s) <= 8:
            return f"{s[:2]}***{s[-1:]}"
        return f"{s[:4]}***{s[-4:]}"

    def _provider_status(provider: str, *, api_key: str, base_url: str, model: str) -> dict[str, Any]:
        provider_normalized = provider.strip().lower()
        requires_key = provider_normalized in {"mimo", "deepseek", "openai", "qwen"}
        key_ok = bool(str(api_key).strip()) or not requires_key
        url_ok = bool(str(base_url).strip())
        model_ok = bool(str(model).strip())
        return {
            "provider": provider_normalized,
            "model": model,
            "base_url": base_url,
            "api_key_masked": _mask(api_key),
            "requires_api_key": requires_key,
            "ready": bool(key_ok and url_ok and model_ok),
            "checks": {"api_key": key_ok, "base_url": url_ok, "model": model_ok},
        }

    provider_configs = {
        "mimo": {"api_key": cfg.mimo.api_key, "base_url": cfg.mimo.base_url},
        "deepseek": {"api_key": cfg.deepseek.api_key, "base_url": cfg.deepseek.base_url},
        "openai": {"api_key": cfg.openai.api_key, "base_url": cfg.openai.base_url},
        "qwen": {"api_key": cfg.qwen.api_key, "base_url": cfg.qwen.base_url},
        "ollama": {"api_key": "", "base_url": cfg.ollama.base_url},
    }
    llm_provider = cfg.llm.provider.strip().lower()
    llm_config = provider_configs.get(llm_provider, {"api_key": "", "base_url": ""})
    llm_status = _provider_status(
        llm_provider,
        api_key=str(llm_config.get("api_key", "")),
        base_url=str(llm_config.get("base_url", "")),
        model=cfg.llm.model,
    )

    memory_provider = cfg.memory_analysis.provider.strip().lower()
    memory_status = _provider_status(
        memory_provider,
        api_key=cfg.memory_analysis.api_key,
        base_url=cfg.memory_analysis.base_url,
        model=cfg.memory_analysis.model,
    )

    output = {
        "framework_modules": result,
        "config_connectivity": {
            "llm": llm_status,
            "memory_analysis": memory_status,
            "memory_frameworks": {
                "mem0": {
                    "enabled": cfg.memory_frameworks.enable_mem0,
                    "cloud_api_key_masked": _mask(cfg.memory_frameworks.mem0_api_key),
                    "cloud_ready": bool(cfg.memory_frameworks.enable_mem0 and cfg.memory_frameworks.mem0_api_key),
                },
                "llamacloud": {
                    "enabled": cfg.memory_frameworks.enable_llamaindex_memory,
                    "cloud_mode": cfg.memory_frameworks.llamaindex_cloud_mode,
                    "cloud_api_key_masked": _mask(cfg.memory_frameworks.llamaindex_api_key),
                    "cloud_ready": bool(
                        cfg.memory_frameworks.enable_llamaindex_memory
                        and cfg.memory_frameworks.llamaindex_cloud_mode
                        and cfg.memory_frameworks.llamaindex_api_key
                        and result.get("llama_cloud", {}).get("installed")
                    ),
                },
                "cognee": {
                    "enabled": cfg.memory_frameworks.enable_cognee,
                    "cloud_mode": cfg.memory_frameworks.cognee_cloud_mode,
                    "cloud_api_key_masked": _mask(cfg.memory_frameworks.cognee_api_key),
                    "cloud_base_url": cfg.memory_frameworks.cognee_base_url,
                    "dataset_name": cfg.memory_frameworks.cognee_dataset_name,
                    "cloud_ready": bool(
                        cfg.memory_frameworks.enable_cognee
                        and cfg.memory_frameworks.cognee_cloud_mode
                        and cfg.memory_frameworks.cognee_api_key
                        and cfg.memory_frameworks.cognee_base_url
                    ),
                },
            },
            "deepseek_defaults": {
                "model": cfg.deepseek.model,
                "base_url": cfg.deepseek.base_url,
                "api_key_masked": _mask(cfg.deepseek.api_key),
            },
            "llm_providers": {
                name: _provider_status(
                    name,
                    api_key=str(provider_cfg.get("api_key", "")),
                    base_url=str(provider_cfg.get("base_url", "")),
                    model=cfg.llm.model if name != "deepseek" else cfg.deepseek.model,
                )
                for name, provider_cfg in provider_configs.items()
            },
        },
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    config_ok = bool(llm_status["ready"] and memory_status["ready"])
    return 0 if (modules_ok and config_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
