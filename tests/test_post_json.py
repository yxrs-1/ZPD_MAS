import io
import json
import urllib.error

import pytest

from scaffolding.model_generator import post_json


class _Body:
    def __init__(self, status, raw: bytes):
        self.status = status
        self._raw = raw
        self.closed = False

    def read(self):
        return self._raw

    def close(self):
        self.closed = True


def test_post_json_sends_utf8_json_and_parses_the_reply():
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["data"] = request.data
        seen["timeout"] = timeout
        seen["authorization"] = request.get_header("Authorization")
        seen["method"] = request.get_method()
        return _Body(200, b'{"ok": true}')

    status, body = post_json(
        "https://api.deepseek.com/chat/completions",
        {"Authorization": "Bearer secret", "Content-Type": "application/json"},
        {"ok": True},
        opener=opener,
    )

    assert status == 200
    assert body == {"ok": True}
    assert seen["url"] == "https://api.deepseek.com/chat/completions"
    assert seen["data"] == json.dumps({"ok": True}).encode("utf-8")
    assert seen["timeout"] == 60
    assert seen["authorization"] == "Bearer secret"
    assert seen["method"] == "POST"


def test_post_json_returns_none_when_the_body_is_not_json():
    def opener(request, timeout):
        return _Body(200, b"nope")

    assert post_json("https://example.test", {}, {"ok": True}, opener=opener) == (200, None)


def test_post_json_returns_an_http_error_status():
    def opener(request, timeout):
        return _Body(503, b'{"error": "busy"}')

    status, body = post_json("https://example.test", {}, {"ok": True}, opener=opener)

    assert status == 503
    assert body == {"error": "busy"}


def test_post_json_turns_urllib_http_error_into_a_status():
    def opener(request, timeout):
        raise urllib.error.HTTPError(
            "https://example.test", 401, "no", {}, io.BytesIO(b"nope")
        )

    assert post_json("https://example.test", {}, {"ok": True}, opener=opener) == (401, None)


def test_post_json_lets_connection_errors_escape():
    def opener(request, timeout):
        raise TimeoutError("timed out")

    with pytest.raises(TimeoutError):
        post_json("https://example.test", {}, {"ok": True}, opener=opener)
