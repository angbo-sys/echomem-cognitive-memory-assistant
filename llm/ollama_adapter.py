"""Ollama adapter using Ollama generate API."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib import error, request

from .base import BaseLLM


class OllamaAdapter(BaseLLM):
    """Adapter for Ollama generate API (local inference)."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = "http://localhost:11434",
        model: str | None = "llama3",
        timeout: float = 120.0,
        max_retries: int = 1,
        retry_backoff_sec: float = 0.6,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, model=model, timeout=timeout)
        # Ollama does not require an API key; ignore if provided
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_sec = max(0.0, float(retry_backoff_sec))

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if not self.base_url:
            raise RuntimeError("OllamaAdapter requires `base_url`.")
        if not self.model:
            raise RuntimeError("OllamaAdapter requires `model`.")

        system_prompt = kwargs.pop("system_prompt", "")
        options = kwargs.pop("options", None)
        if options is None:
            options = dict(kwargs)
            options.setdefault("temperature", 0.7)
            options.setdefault("top_p", 0.9)

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if isinstance(system_prompt, str) and system_prompt.strip():
            payload["system"] = system_prompt

        req = request.Request(
            url=f"{self.base_url.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                with request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8")
                break
            except error.HTTPError as exc:
                details = exc.read().decode("utf-8", errors="replace")
                if exc.code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    time.sleep(self.retry_backoff_sec * (attempt + 1))
                    continue
                raise RuntimeError(f"Ollama API HTTPError {exc.code}: {details}") from exc
            except error.URLError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_sec * (attempt + 1))
                    continue
                raise RuntimeError(f"Ollama API connection error: {exc.reason}") from exc
        else:
            if last_exc is not None:
                raise RuntimeError(f"Ollama API connection error: {last_exc}") from last_exc
            raise RuntimeError("Ollama API request failed without response.")

        data = json.loads(body)
        response_text = data.get("response")
        if not isinstance(response_text, str):
            raise RuntimeError(f"Ollama API returned unexpected response: {data}")
        return response_text

