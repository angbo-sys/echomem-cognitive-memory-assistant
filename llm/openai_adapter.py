"""OpenAI adapter using OpenAI-compatible chat completions API."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib import error, request

from .base import BaseLLM


class OpenAIAdapter(BaseLLM):
    """Adapter for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = "https://api.openai.com/v1",
        model: str | None = "gpt-4o-mini",
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
            raise RuntimeError("OpenAIAdapter requires `api_key`.")
        if not self.base_url:
            raise RuntimeError("OpenAIAdapter requires `base_url`.")
        if not self.model:
            raise RuntimeError("OpenAIAdapter requires `model`.")

        system_prompt = kwargs.pop("system_prompt", "")
        messages = kwargs.pop("messages", None)
        if messages is None:
            messages = []
            if isinstance(system_prompt, str) and system_prompt.strip():
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.pop("temperature", 0.7),
            "top_p": kwargs.pop("top_p", 1.0),
            "max_tokens": kwargs.pop("max_tokens", 1024),
        }
        payload.update(kwargs)

        req = request.Request(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
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
                raise RuntimeError(f"OpenAI API HTTPError {exc.code}: {details}") from exc
            except error.URLError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_sec * (attempt + 1))
                    continue
                raise RuntimeError(f"OpenAI API connection error: {exc.reason}") from exc
        else:
            if last_exc is not None:
                raise RuntimeError(f"OpenAI API connection error: {last_exc}") from last_exc
            raise RuntimeError("OpenAI API request failed without response.")

        data = json.loads(body)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"OpenAI API returned no choices: {data}")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError(f"OpenAI API returned invalid content: {data}")
        return content

