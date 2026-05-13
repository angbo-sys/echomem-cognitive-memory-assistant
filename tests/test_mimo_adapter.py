from __future__ import annotations

import io
import unittest
from unittest.mock import patch
from urllib import error

from llm.mimo_adapter import MiMoAdapter


class _FakeHTTPResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


class TestMiMoAdapter(unittest.TestCase):
    def _adapter(self) -> MiMoAdapter:
        return MiMoAdapter(api_key="k", base_url="https://token-plan-cn.xiaomimimo.com/v1", model="mimo-v2.5-pro")

    def test_generate_success(self) -> None:
        adapter = self._adapter()
        body = '{"choices":[{"message":{"content":"ok"}}]}'
        with patch("llm.mimo_adapter.request.urlopen", return_value=_FakeHTTPResponse(body)):
            out = adapter.generate("hello")
        self.assertEqual(out, "ok")

    def test_generate_http_error(self) -> None:
        adapter = self._adapter()
        req = error.HTTPError(
            url="https://token-plan-cn.xiaomimimo.com/v1/chat/completions",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"bad key"}'),
        )
        with patch("llm.mimo_adapter.request.urlopen", side_effect=req):
            with self.assertRaisesRegex(RuntimeError, "MiMo API HTTPError 401"):
                adapter.generate("hello")

    def test_generate_url_error(self) -> None:
        adapter = self._adapter()
        with patch("llm.mimo_adapter.request.urlopen", side_effect=error.URLError("network down")):
            with self.assertRaisesRegex(RuntimeError, "MiMo API connection error"):
                adapter.generate("hello")

    def test_generate_no_choices(self) -> None:
        adapter = self._adapter()
        body = '{"choices":[]}'
        with patch("llm.mimo_adapter.request.urlopen", return_value=_FakeHTTPResponse(body)):
            with self.assertRaisesRegex(RuntimeError, "returned no choices"):
                adapter.generate("hello")

    def test_generate_invalid_content(self) -> None:
        adapter = self._adapter()
        body = '{"choices":[{"message":{"content":123}}]}'
        with patch("llm.mimo_adapter.request.urlopen", return_value=_FakeHTTPResponse(body)):
            with self.assertRaisesRegex(RuntimeError, "invalid content"):
                adapter.generate("hello")


if __name__ == "__main__":
    unittest.main()
