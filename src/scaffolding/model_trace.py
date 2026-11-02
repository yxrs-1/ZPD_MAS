import os
from contextlib import contextmanager
from contextvars import ContextVar


_FIELDS = ("支架类型", "支架正文", "生成目标", "生成题目")
_pending: ContextVar[dict | None] = ContextVar("model_trace_pending", default=None)
_sender = None
_client = None
_client_key = None


def install_trace_sender(sender) -> None:
    global _sender
    _sender = sender


def inside_model_call() -> bool:
    return _pending.get() is not None


@contextmanager
def tracing_model_call(name: str, **metadata):
    bag = {
        "name": name,
        "metadata": {key: value for key, value in metadata.items() if key in _FIELDS},
        "messages": None,
        "output": None,
    }
    token = _pending.set(bag)
    try:
        yield bag["metadata"]
    finally:
        _pending.reset(token)
        if bag["output"] is not None:
            _emit(bag["name"], bag["messages"], bag["output"], bag["metadata"])


def capture_model_call(messages, output: str) -> None:
    if _pending.get() is None:
        with tracing_model_call("模型调用"):
            _stash(messages, output)
        return
    _stash(messages, output)


def remember_model_result(messages, output: str) -> None:
    bag = _pending.get()
    if bag is None or bag["output"] is not None:
        return
    _stash(messages, output)


def format_objectives(items) -> str:
    return "\n\n".join("维度：" + item.dimension + "\n表述：" + item.statement for item in items)


def format_questions(questions) -> str:
    lines = []
    for question in questions:
        kind = _question_kind(question)
        if kind is None:
            continue
        lines.append(kind + "：" + question.prompt)
    return "\n".join(lines)


def fill_text_task(metadata: dict, reply: str) -> None:
    import json

    try:
        body = json.loads(reply.strip())
    except json.JSONDecodeError:
        return
    if not isinstance(body, dict):
        return
    objectives = body.get("目标")
    if isinstance(objectives, list):
        lines = []
        for item in objectives:
            if (
                isinstance(item, dict)
                and type(item.get("维度")) is str
                and type(item.get("表述")) is str
            ):
                lines.append("维度：" + item["维度"] + "\n表述：" + item["表述"])
        if lines:
            metadata["生成目标"] = "\n\n".join(lines)
    questions = body.get("题目")
    if not isinstance(questions, dict):
        return
    lines = []
    for kind in ("单选", "多选", "判断", "综合"):
        items = questions.get(kind)
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, dict) and type(item.get("题目")) is str:
                lines.append(kind + "：" + item["题目"])
    if lines:
        metadata["生成题目"] = "\n".join(lines)


def _question_kind(question) -> str | None:
    from scaffolding.records import ChoiceQuestion, OpenQuestion, TrueFalseQuestion

    if isinstance(question, ChoiceQuestion):
        return question.selection.value
    if isinstance(question, TrueFalseQuestion):
        return "判断"
    if isinstance(question, OpenQuestion):
        return "综合"
    return None


def _stash(messages, output: str) -> None:
    bag = _pending.get()
    if bag is None:
        return
    bag["messages"] = [dict(message) for message in messages]
    bag["output"] = output


def _emit(name: str, messages, output: str, metadata: dict) -> None:
    sender = _sender if _sender is not None else _configured_sender()
    if sender is None:
        return
    payload = {
        "name": name,
        "model": "deepseek-flash",
        "input": messages,
        "output": output,
        "metadata": {key: metadata[key] for key in _FIELDS if key in metadata},
    }
    try:
        sender(payload)
    except Exception:
        return


def _configured_sender():
    public = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
    secret = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
    if not public or not secret:
        return None
    return _langfuse_sender


def _langfuse_sender(payload: dict) -> None:
    client = _langfuse_client()
    observation = client.start_observation(
        name=payload["name"],
        as_type="generation",
        model=payload["model"],
        input=payload["input"],
        output=payload["output"],
        metadata=payload["metadata"] or None,
    )
    observation.end()
    client.flush()


def _langfuse_client():
    global _client, _client_key
    from langfuse import Langfuse

    public = os.environ["LANGFUSE_PUBLIC_KEY"].strip()
    secret = os.environ["LANGFUSE_SECRET_KEY"].strip()
    base_url = os.environ.get("LANGFUSE_BASE_URL", "").strip()
    host = os.environ.get("LANGFUSE_HOST", "").strip()
    key = (public, secret, base_url, host)
    if _client is not None and _client_key == key:
        return _client
    kwargs = {"public_key": public, "secret_key": secret}
    if base_url:
        kwargs["base_url"] = base_url
    elif host:
        kwargs["host"] = host
    _client = Langfuse(**kwargs)
    _client_key = key
    return _client
