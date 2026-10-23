import pytest

from scaffolding.classroom import main
from scaffolding.model_generator import post_json


def _block(monkeypatch):
    seen = {}

    def build(*, post, api_key=None):
        seen["post"] = post
        seen["api_key"] = api_key
        return "room"

    def listen(room, port):
        seen["room"] = room
        seen["port"] = port

    monkeypatch.setattr("scaffolding.classroom.production_classroom", build)
    monkeypatch.setattr("scaffolding.classroom.serve", listen)
    return seen


def test_a_missing_key_does_not_listen(monkeypatch, capsys):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    seen = _block(monkeypatch)

    assert main([]) == 1
    assert seen == {}
    captured = capsys.readouterr()
    assert captured.err.strip() == "没有配置 DEEPSEEK_API_KEY"
    assert captured.out == ""


def test_an_empty_key_does_not_listen(monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    seen = _block(monkeypatch)

    assert main([]) == 1
    assert seen == {}
    assert capsys.readouterr().err.strip() == "没有配置 DEEPSEEK_API_KEY"


def test_a_whitespace_key_does_not_listen(monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "  ")
    seen = _block(monkeypatch)

    assert main([]) == 1
    assert seen == {}
    assert capsys.readouterr().err.strip() == "没有配置 DEEPSEEK_API_KEY"


def test_a_bad_port_is_hidden_when_the_key_is_missing(monkeypatch, capsys):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    seen = _block(monkeypatch)

    assert main(["abc"]) == 1
    assert seen == {}
    assert capsys.readouterr().err.strip() == "没有配置 DEEPSEEK_API_KEY"


def test_the_default_port_is_8000(monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    seen = _block(monkeypatch)

    assert main([]) == 0
    assert seen["post"] is post_json
    assert seen["api_key"] is None
    assert seen["room"] == "room"
    assert seen["port"] == 8000
    captured = capsys.readouterr()
    assert captured.out == "http://127.0.0.1:8000\n"
    assert captured.err == ""


def test_a_chosen_port_is_used(monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    seen = _block(monkeypatch)

    assert main(["8765"]) == 0
    assert seen["port"] == 8765
    assert capsys.readouterr().out == "http://127.0.0.1:8765\n"


def test_a_leading_zero_port_uses_its_value(monkeypatch, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    seen = _block(monkeypatch)

    assert main(["  0800  "]) == 0
    assert seen["port"] == 800
    assert capsys.readouterr().out == "http://127.0.0.1:800\n"


@pytest.mark.parametrize(
    "argv",
    [[""], [" "], ["+8000"], ["8000.0"], ["8_000"], ["0"], ["65536"], ["abc"], ["8000", "1"]],
)
def test_a_bad_port_does_not_listen(monkeypatch, capsys, argv):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "secret")
    seen = _block(monkeypatch)

    assert main(argv) == 1
    assert seen == {}
    captured = capsys.readouterr()
    assert captured.err.strip() == "端口不正确"
    assert captured.out == ""
