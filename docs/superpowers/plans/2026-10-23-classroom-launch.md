# 本机启动 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 `python -m scaffolding.classroom` 在本机启动课堂；缺密钥或端口不对时先退出，通过后用标准库把模型请求发给 DeepSeek。

**Architecture:** `post_json` 放在 `model_generator.py`，紧挨现有的 `deepseek_complete`。`classroom.main` 先查密钥再查端口，然后 `production_classroom(post=post_json)` 并调用现有的 `serve`。测试替换打开函数、`production_classroom` 和 `serve`。

**Tech Stack:** Python 3.14，pytest 9，标准库。实现从 `origin/main` 的 `116b1eb` 建工作区。本地的 `origin/main` 若仍停在 `c199ab2`，先 `git fetch origin`。规格在本地 `master` 的 `6647e7e`，文件是 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-23-classroom-launch-design.md`。工作区里若没有这份规格，从该文件原样复制，不要改写。测试命令是 `.\.venv\Scripts\python.exe -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。不要提交本计划。

## Global Constraints

- 监听地址仍是 `127.0.0.1`。决策、支架、提炼、出题和文字生成的构造不变。教师页单独的监听不变。
- 测试不调用真正的监听，不打开浏览器，也不访问网络。测试直接调用 `main` 和 `post_json`，不启动子进程。
- 密钥没有设置、是空字符串，或去掉两端空白后是空的：向标准错误写出 `没有配置 DEEPSEEK_API_KEY`，返回 `1`。即使端口同时不正确，也只写这一句。不创建课堂，也不监听。
- 参数不是零个或一个，去掉两端空白后含有非十进制数字，或数值不在 `1` 到 `65535`：向标准错误写出 `端口不正确`，返回 `1`。带正负号、小数点或下划线都算不正确。`0800` 是端口 `800`。
- 两项都通过之后，向标准输出写出 `http://127.0.0.1:` 加上实际端口，并立即刷新。不写参数时端口是 `8000`。
- `post_json` 用标准库发送 UTF-8 JSON，使用调用方给的地址和请求头，超时 60 秒。正文不是 JSON 时第二个值是 `None`。HTTP 错误状态交回，不再抛出。连接失败和超时继续抛出。
- 页面不新增失败句。教师生成失败仍是「生成失败，没有创建任务」。学生端失败仍留在当前页。

## File Map

- Modify: `src/scaffolding/model_generator.py` — `post_json`。
- Modify: `src/scaffolding/classroom.py` — `main`，以及 `python -m scaffolding.classroom`。
- Create: `tests/test_post_json.py`、`tests/test_classroom_launch.py`。
- Copy if missing: `docs/superpowers/specs/2026-10-23-classroom-launch-design.md`。

---

### Task 1: 用标准库发送 JSON

**Files:**
- Modify: `src/scaffolding/model_generator.py`
- Create: `tests/test_post_json.py`

**Interfaces:**
- Consumes: 无。
- Produces: `post_json(url, headers, payload, *, opener=urllib.request.urlopen) -> tuple`。第一个值是状态码。第二个值是 JSON 解析结果；正文不是 JSON 时是 `None`。`opener` 的调用形式是 `opener(request, timeout=60)`。`request` 是 `urllib.request.Request`，方法是 POST，正文是 payload 的 UTF-8 JSON。

- [ ] **Step 1: 写失败测试**

Create `tests/test_post_json.py`：

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_post_json.py -v`

Expected: FAIL，`post_json` 还不存在。

- [ ] **Step 3: 实现发送函数**

在 `src/scaffolding/model_generator.py` 已有的 `import json` 和 `import os` 后面加上：

```python
import urllib.error
import urllib.request
```

在 `deepseek_complete` 后面加上：

```python
def post_json(url, headers, payload, *, opener=urllib.request.urlopen):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    try:
        response = opener(request, timeout=60)
    except urllib.error.HTTPError as error:
        response = error
    try:
        raw = response.read()
    finally:
        close = getattr(response, "close", None)
        if close is not None:
            close()
    status = response.status if hasattr(response, "status") else response.code
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        parsed = None
    return status, parsed
```

- [ ] **Step 4: 运行测试，确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_post_json.py -v`

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add src/scaffolding/model_generator.py tests/test_post_json.py
git commit -m "feat: send DeepSeek requests with the standard library"
```

---

### Task 2: 启动本机课堂

**Files:**
- Modify: `src/scaffolding/classroom.py`
- Create: `tests/test_classroom_launch.py`
- Copy if missing: `docs/superpowers/specs/2026-10-23-classroom-launch-design.md`

**Interfaces:**
- Consumes: `post_json(url, headers, payload, *, opener=urllib.request.urlopen)`。现有的 `production_classroom(*, post, api_key=None)` 和 `serve(room, port)`。
- Produces: `main(argv: list[str] | None = None) -> int`。`argv` 是 `None` 时读取 `sys.argv[1:]`。测试必须传入列表，不要在 pytest 里调用无参的 `main()`，否则会读到 pytest 自己的参数。返回 `1` 表示启动失败。替身 `serve` 返回后，`main` 返回 `0`。

- [ ] **Step 1: 复制规格，并写失败测试**

工作区没有 `docs/superpowers/specs/2026-10-23-classroom-launch-design.md` 时，从 `F:\work\zpd_MAS\docs\superpowers\specs\2026-10-23-classroom-launch-design.md` 原样复制，不要改写。

Create `tests/test_classroom_launch.py`：

```python
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
```

- [ ] **Step 2: 运行测试，确认失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_classroom_launch.py -v`

Expected: FAIL，`main` 还不存在。

- [ ] **Step 3: 实现启动入口**

`src/scaffolding/classroom.py` 增加 `import sys`。把

```python
from scaffolding.model_generator import ModelQuestionGenerator, deepseek_complete
```

改成

```python
from scaffolding.model_generator import ModelQuestionGenerator, deepseek_complete, post_json
```

在文件末尾、`serve` 之后加上：

```python
def _port(argv: list[str]) -> int | None:
    if len(argv) == 0:
        return 8000
    if len(argv) != 1:
        return None
    text = argv[0].strip()
    if len(text) == 0 or not text.isascii() or not text.isdigit():
        return None
    value = int(text)
    if value < 1 or value > 65535:
        return None
    return value


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:]) if argv is None else argv
    key = os.environ.get("DEEPSEEK_API_KEY")
    if key is None or key.strip() == "":
        print("没有配置 DEEPSEEK_API_KEY", file=sys.stderr)
        return 1
    port = _port(args)
    if port is None:
        print("端口不正确", file=sys.stderr)
        return 1
    print("http://127.0.0.1:" + str(port), flush=True)
    room = production_classroom(post=post_json)
    serve(room, port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

不要改 `serve` 的绑定地址，不要改 `production_classroom` 里决策、支架、提炼、出题和文字生成的构造，不要改 `teacher_page.serve`。

- [ ] **Step 4: 运行测试，确认通过**

Run: `.\.venv\Scripts\python.exe -m pytest`

Expected: PASS

- [ ] **Step 5: 提交**

```powershell
git add src/scaffolding/classroom.py tests/test_classroom_launch.py docs/superpowers/specs/2026-10-23-classroom-launch-design.md
git commit -m "feat: start the classroom on this machine"
```

规格只在工作区原先没有它时才加入提交。不要提交本计划。
