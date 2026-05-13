"""Qwen adapter using DashScope text-generation API."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib import error, request

from .base import BaseLLM


class QwenAdapter(BaseLLM):
    """Adapter for Qwen (DashScope) text-generation API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = "https://dashscope.aliyuncs.com/api/v1",
        model: str | None = "qwen-turbo",
        timeout: float = 30.0,
        max_retries: int = 1,
        retry_backoff_sec: float = 0.6,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, model=model, timeout=timeout)
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_sec = max(0.0, float(retry_backoff_sec))

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if not self.api_key:
            raise RuntimeError("QwenAdapter requires `api_key`.")
        if not self.base_url:
            raise RuntimeError("QwenAdapter requires `base_url`.")
        if not self.model:
            raise RuntimeError("QwenAdapter requires `model`.")

        system_prompt = kwargs.pop("system_prompt", "")
        parameters = kwargs.pop("parameters", None)
        if parameters is None:
            parameters = dict(kwargs)
            # Default to message result format for consistent response structure
            parameters.setdefault("result_format", "message")

        input_data: dict[str, Any] = {}
        if isinstance(system_prompt, str) and system_prompt.strip():
            input_data["messages"] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            input_data["messages"] = [{"role": "user", "content": prompt}]

        payload = {
            "model": self.model,
            "input": input_data,
            "parameters": parameters,
        }

        req = request.Request(
            url=f"{self.base_url.rstrip('/')}/services/aigc/text-generation/generation",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
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
                raise RuntimeError(f"Qwen API HTTPError {exc.code}: {details}") from exc
            except error.URLError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_sec * (attempt + 1))
                    continue
                raise RuntimeError(f"Qwen API connection error: {exc.reason}") from exc
        else:
            if last_exc is not None:
                raise RuntimeError(f"Qwen API connection error: {last_exc}") from last_exc
            raise RuntimeError("Qwen API request failed without response.")

        data = json.loads(body)
        output = data.get("output") or {}

        # Handle message format (result_format=message)
        choices = output.get("choices")
        if isinstance(choices, list) and choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content

        # Handle text format (result_format=text, default)
        text = output.get("text")
        if isinstance(text, str) and text.strip():
            return text

        raise RuntimeError(f"Qwen API returned unexpected response: {data}")

