"""MiMo adapter using OpenAI-compatible chat completions API."""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any
from urllib import error, request

from .base import BaseLLM


def build_mimo_system_prompt(now: datetime | None = None) -> str:
    """Build the recommended Chinese system prompt for MiMo."""
    dt = now or datetime.now()
    weekday = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][dt.weekday()]
    date_str = dt.strftime("%Y-%m-%d")
    return (
        f"你是MiMo（中文名称也是MiMo），是小米公司研发的AI智能助手。"
        f"今天的日期：{date_str} {weekday}，你的知识截止日期是2024年12月。"
    )


class MiMoAdapter(BaseLLM):
    """Adapter for Xiaomi MiMo OpenAI-compatible endpoint."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = "https://token-plan-cn.xiaomimimo.com/v1",
        model: str | None = "mimo-v2.5-pro",
        timeout: float = 30.0,
        temperature: float = 1.0,
        top_p: float = 0.95,
        use_api_key_header: bool = False,
        max_retries: int = 1,
        retry_backoff_sec: float = 0.6,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url, model=model, timeout=timeout)
        self.temperature = temperature
        self.top_p = top_p
        self.use_api_key_header = use_api_key_header
        self.max_retries = max(0, int(max_retries))
        self.retry_backoff_sec = max(0.0, float(retry_backoff_sec))

    def generate(self, prompt: str, **kwargs: Any) -> str:
        if not prompt.strip():
            raise ValueError("prompt must not be empty")
        if not self.api_key:
            raise RuntimeError("MiMoAdapter requires `api_key`.")
        if not self.base_url:
            raise RuntimeError("MiMoAdapter requires `base_url`.")
        if not self.model:
            raise RuntimeError("MiMoAdapter requires `model`.")

        system_prompt = kwargs.pop("system_prompt", build_mimo_system_prompt())
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": kwargs.pop("temperature", self.temperature),
            "top_p": kwargs.pop("top_p", self.top_p),
            "max_completion_tokens": kwargs.pop("max_completion_tokens", 1024),
        }
        payload.update(kwargs)

        headers = {"Content-Type": "application/json"}
        if self.use_api_key_header:
            headers["api-key"] = self.api_key
        else:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = request.Request(
            url=f"{self.base_url.rstrip('/')}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
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
                raise RuntimeError(f"MiMo API HTTPError {exc.code}: {details}") from exc
            except error.URLError as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_sec * (attempt + 1))
                    continue
                raise RuntimeError(f"MiMo API connection error: {exc.reason}") from exc
        else:
            if last_exc is not None:
                raise RuntimeError(f"MiMo API connection error: {last_exc}") from last_exc
            raise RuntimeError("MiMo API request failed without response.")

        data = json.loads(body)
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"MiMo API returned no choices: {data}")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise RuntimeError(f"MiMo API returned invalid content: {data}")
        return content
