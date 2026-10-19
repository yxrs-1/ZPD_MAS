import pytest

from scaffolding.generation import Rejected
from scaffolding.model_generator import DEEPSEEK_URL, deepseek_complete


class RecordingPost:
    def __init__(self, status: int = 200, response: object | None = None, error: Exception | None = None) -> None:
        self.status = status
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, url, headers, payload):
        self.calls.append((url, headers, payload))
        if self.error is not None:
            raise self.error
        return self.status, self.response


def _response(content: object = "{\"单选\":[]}") -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_a_successful_request_returns_only_the_content(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "from-env")
    messages = ({"role": "system", "content": "规则"}, {"role": "user", "content": "数量"})
    post = RecordingPost(response=_response("正文"))

    assert deepseek_complete(messages, post=post, api_key="secret") == "正文"

    url, headers, payload = post.calls[0]
    assert url == DEEPSEEK_URL
    assert headers["Authorization"] == "Bearer secret"
    assert headers["Content-Type"] == "application/json"
    assert payload == {
        "model": "deepseek-flash",
        "messages": [{"role": "system", "content": "规则"}, {"role": "user", "content": "数量"}],
        "stream": False,
        "thinking": {"type": "disabled"},
    }
    assert "reasoning_effort" not in payload
    env_post = RecordingPost(response=_response("环境"))
    assert deepseek_complete(messages, post=env_post) == "环境"
    assert env_post.calls[0][1]["Authorization"] == "Bearer from-env"


def test_a_missing_key_does_not_send(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    post = RecordingPost()

    with pytest.raises(Rejected):
        deepseek_complete((), post=post)
    with pytest.raises(Rejected):
        deepseek_complete((), post=post, api_key="  ")

    assert post.calls == []


def test_a_failed_request_is_rejected_once():
    messages = ({"role": "user", "content": "数量"},)
    for post in (
        RecordingPost(status=500, response=_response("错误")),
        RecordingPost(response={"choices": []}),
        RecordingPost(response={"choices": [{"message": {"content": None}}]}),
        RecordingPost(error=RuntimeError("down")),
    ):
        with pytest.raises(Rejected):
            deepseek_complete(messages, post=post, api_key="secret")
        assert len(post.calls) == 1
