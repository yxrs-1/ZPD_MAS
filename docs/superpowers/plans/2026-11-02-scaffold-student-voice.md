# Scaffold Student Voice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 支架文字用「你」直接对学生说；写成教师口吻时只重写一次。

**Architecture:** 改 `model_scaffold.py` 的系统消息和有图时的第一句。`produce` 在解析成功后检查「文字」。命中教师口吻时清空流式进度，用原来的两条消息加一条用户消息再调用一次，并交回第二次的草稿。`remember_model_result` 保持原样，只留下第一次返回的字符串。

**Tech Stack:** Python，pytest，标准库。规格是 `docs/superpowers/specs/2026-11-02-scaffold-student-voice-design.md`。测试命令是 `python -m pytest`。PowerShell 下不要使用 `&&` 或 bash heredoc；提交用 `git commit -m "message"`。不要改 git config，不要 push。

## Global Constraints

- 学生提问后，支架智能体仍按已经选定的类型交回「文字」和「源码」。
- 本计划只改文字的读者，以及文字写成教师口吻时的一次重写。
- 六类支架的选择、源码格式、示例、本地渲染、微格动画和学生页都不改。
- 2026-10-19 的模型支架智能体规格仍有效。其中「完成函数只调用一次，不重试」只在口吻重写处放宽。解析失败、完成函数抛出的异常、空字符串，仍不重试。
- 文字的读者是正在做这道题的学生。两三句，用「你」直接对这个人说，不引用题干原句，不写出参考答案。
- 有图时，第一句是「先看下面这张图。」
- 文字里不出现这些字样：学生、教师、引导、让学生、请学生、学情。
- 检查只看解析成功之后的「文字」，按子串匹配上面六个字样。源码里出现这些字样不触发重写。
- 空字符串和只有空白的文字不匹配，交回方式与现在相同。
- 第二次的文字无论是否仍命中，都放进草稿并交回，不再调用。追踪元数据「支架正文」记这份最终文字。
- 第一次正文解析失败时抛出现有的 `Rejected`，不进行第二次调用。第一次完成函数抛出的异常原样传出，也不进行第二次调用。
- 第二次解析失败或第二次完成函数抛出异常时，同样按现有规则传出；第一稿丢弃。会话不改，因此学生仍留下上一次的支架。
- 测试不访问网络。
- 不修改 `src/scaffolding/model_generator.py`、`model_trace.py`、`model_decision.py`、`session.py`、`figures.py`、`scaffold_figures.py`，也不修改前端。

## File Map

- Modify: `src/scaffolding/model_scaffold.py` — 系统消息、有图时的第一句、口吻判断、重写一次、重写前清空流式进度。
- Modify: `tests/test_model_scaffold_prompt.py` — 锁定新的系统消息和第一句。
- Modify: `tests/test_model_scaffold_agent.py` — 锁定调用次数、重写消息、空白、源码、失败和流式清空。
- Modify: `tests/test_model_trace.py` — 锁定重写后的「支架正文」仍是最终文字，追踪输出仍是第一份字符串。

---

### Task 1: Student-facing prompt

**Files:**
- Modify: `src/scaffolding/model_scaffold.py:106-112`
- Modify: `src/scaffolding/model_scaffold.py:148`
- Test: `tests/test_model_scaffold_prompt.py:32-40`
- Test: `tests/test_model_scaffold_prompt.py:91`
- Test: `tests/test_model_scaffold_prompt.py:109`

**Interfaces:**
- Consumes: 现有的 `build_messages(scaffold_type, question, questions, answers, passages=(), example_source="") -> tuple[dict[str, str], dict[str, str]]`。
- Produces: 系统消息增加读者和禁语两行。有图时的那一行变为「文字的第一句是：先看下面这张图。」`build_messages` 的参数和返回的两条消息不变。

- [ ] **Step 1: Write the failing test**

在 `tests/test_model_scaffold_prompt.py` 的 `test_the_prompt_lists_the_task_and_this_question` 里，把系统消息断言换成：

```python
    assert system == {
        "role": "system",
        "content": (
            "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
            "顶层只有「文字」和「源码」。两个值都是字符串，可以是空字符串。\n"
            "不要写 HTML，不要写文件名。\n"
            "文字写两三句，不要引用题干原句。\n"
            "读者是正在做这道题的学生。用「你」直接对这个人说。\n"
            "文字里不出现：学生、教师、引导、让学生、请学生、学情。\n"
            "支架的文字和源码不要写出参考答案，也不要写出学情。"
        ),
    }
```

同一测试里，把用户消息中的这一行：

```python
            "文字的第一句让学生看这张图。\n"
```

换成：

```python
            "文字的第一句是：先看下面这张图。\n"
```

在 `test_an_empty_selection_trace_is_a_blank_line` 里，把 `endswith` 的期望字符串中的 `文字的第一句让学生看这张图。` 换成 `文字的第一句是：先看下面这张图。`。其余题目块不要改。

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_model_scaffold_prompt.py -v`

Expected: FAIL。断言差异里，实际系统消息还没有「读者是正在做这道题的学生」，实际图注仍是「文字的第一句让学生看这张图。」

- [ ] **Step 3: Write minimal implementation**

把 `src/scaffolding/model_scaffold.py` 的 `_SYSTEM` 换成：

```python
_SYSTEM = (
    "只回一份 JSON 对象，不要代码块，不要其他文字。\n"
    "顶层只有「文字」和「源码」。两个值都是字符串，可以是空字符串。\n"
    "不要写 HTML，不要写文件名。\n"
    "文字写两三句，不要引用题干原句。\n"
    "读者是正在做这道题的学生。用「你」直接对这个人说。\n"
    "文字里不出现：学生、教师、引导、让学生、请学生、学情。\n"
    "支架的文字和源码不要写出参考答案，也不要写出学情。"
)
```

把 `_figure_note` 里有图时的这一行：

```python
    note = "素材：" + kind + "\n" + _FORMAT[kind] + "\n文字的第一句让学生看这张图。\n"
```

换成：

```python
    note = "素材：" + kind + "\n" + _FORMAT[kind] + "\n文字的第一句是：先看下面这张图。\n"
```

没有图时的「素材：无」和「源码留空。」保持不动。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_model_scaffold_prompt.py tests/test_model_scaffold_agent.py -v`

Expected: PASS。提示词测试锁定新句子。智能体测试仍调用 `build_messages`，不因文案改动失败。

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_scaffold.py tests/test_model_scaffold_prompt.py
git commit -m "fix: address scaffold text to the student"
```

---

### Task 2: Rewrite teacher voice once

**Files:**
- Modify: `src/scaffolding/model_scaffold.py:26-32`
- Modify: `src/scaffolding/model_scaffold.py:213-240`
- Test: `tests/test_model_scaffold_agent.py`
- Test: `tests/test_model_trace.py`

**Interfaces:**
- Consumes: Task 1 的 `build_messages`。现有 `parse_scaffold`、`begin_scaffold_progress`、`end_scaffold_progress`、`feed_scaffold_stream`、`remember_model_result`、`tracing_model_call`。
- Produces: `clear_scaffold_progress() -> None`。它把当前流式进度的 `shown` 设为 `""`；没有进度时什么也不做。`ModelScaffoldAgent.produce` 的参数和返回类型不变。教师口吻时第二次调用收到三元组 `(system, user, followup)`，其中 `followup` 是 `{"role": "user", "content": "上一稿是在对教师说话，按规则改成直接对学生说的话。\n上一稿：" + 第一稿文字}`。

- [ ] **Step 1: Write the failing tests**

在 `tests/test_model_scaffold_agent.py` 增加导入：

```python
from scaffolding.model_scaffold import (
    ModelScaffoldAgent,
    Rejected,
    begin_scaffold_progress,
    build_messages,
    clear_scaffold_progress,
    end_scaffold_progress,
    feed_scaffold_stream,
)
```

删掉原来单独的 `from scaffolding.model_scaffold import ModelScaffoldAgent, Rejected, build_messages`。文件顶部已有 `json` 和 `pytest`。

在文件末尾追加：

```python
def _follow(previous: str) -> dict[str, str]:
    return {
        "role": "user",
        "content": "上一稿是在对教师说话，按规则改成直接对学生说的话。\n上一稿：" + previous,
    }


def test_teacher_voice_is_rewritten_once_with_the_same_materials():
    questions, answers = _materials()
    previous = "引导学生看空序列。"
    complete = QueueComplete([_reply(previous), _reply("你看空序列。")])
    passages = (("笔记.txt", "空序列"),)

    draft = ModelScaffoldAgent(complete).produce(
        "提示",
        "还缺什么？",
        questions,
        answers,
        passages=passages,
        example_source="网络\n  空\n",
    )

    system, user = build_messages(
        "提示",
        "还缺什么？",
        questions,
        answers,
        passages,
        example_source="网络\n  空\n",
    )
    assert draft == ScaffoldDraft(text="你看空序列。")
    assert complete.calls == [(system, user), (system, user, _follow(previous))]


def test_a_second_teacher_voice_reply_is_returned():
    questions, answers = _materials()
    complete = QueueComplete([_reply("引导学生。"), _reply("你让学生再看一次。")])

    draft = ModelScaffoldAgent(complete).produce("反馈", "还缺什么？", questions, answers)

    assert draft.text == "你让学生再看一次。"
    assert len(complete.calls) == 2


def test_blank_text_and_a_marked_source_do_not_retry():
    questions, answers = _materials()
    blank = QueueComplete([_reply(text="   ")])
    marked = QueueComplete([_reply("你看这个节点。", source="节点：学生")])

    assert ModelScaffoldAgent(blank).produce("反馈", "还缺什么？", questions, answers) == ScaffoldDraft(text="   ")
    assert ModelScaffoldAgent(marked).produce("提示", "还缺什么？", questions, answers) == ScaffoldDraft(
        text="你看这个节点。",
        source="节点：学生",
    )
    assert len(blank.calls) == 1
    assert len(marked.calls) == 1


def test_the_first_failure_does_not_retry():
    questions, answers = _materials()
    fenced = QueueComplete(["```json\n" + _reply("引导学生。") + "\n```"])
    extra = QueueComplete([json.dumps({"文字": "引导学生。", "源码": "", "多余": ""}, ensure_ascii=False)])
    failing = QueueComplete([RuntimeError("down")])
    foreign = QueueComplete([{"文字": "引导学生。"}])

    with pytest.raises(Rejected):
        ModelScaffoldAgent(fenced).produce("提示", "还缺什么？", questions, answers)
    with pytest.raises(Rejected):
        ModelScaffoldAgent(extra).produce("提示", "还缺什么？", questions, answers)
    with pytest.raises(RuntimeError):
        ModelScaffoldAgent(failing).produce("提示", "还缺什么？", questions, answers)
    with pytest.raises(Rejected):
        ModelScaffoldAgent(foreign).produce("提示", "还缺什么？", questions, answers)

    assert len(fenced.calls) == 1
    assert len(extra.calls) == 1
    assert len(failing.calls) == 1
    assert len(foreign.calls) == 1


def test_the_second_failure_propagates_and_stops():
    questions, answers = _materials()
    fenced = QueueComplete([_reply("引导学生。"), "```json\n" + _reply("你看空序列。") + "\n```"])
    failing = QueueComplete([_reply("引导学生。"), RuntimeError("down")])

    with pytest.raises(Rejected):
        ModelScaffoldAgent(fenced).produce("提示", "还缺什么？", questions, answers)
    with pytest.raises(RuntimeError):
        ModelScaffoldAgent(failing).produce("提示", "还缺什么？", questions, answers)

    assert len(fenced.calls) == 2
    assert len(failing.calls) == 2


def test_clear_scaffold_progress_emits_the_same_partial_again():
    seen = []
    token = begin_scaffold_progress(seen.append)
    try:
        feed_scaffold_stream('{"文字": "先看"')
        feed_scaffold_stream('{"文字": "先看"')
        assert seen == ["先看"]
        clear_scaffold_progress()
        feed_scaffold_stream('{"文字": "先看"')
        assert seen == ["先看", "先看"]
    finally:
        end_scaffold_progress(token)


def test_a_rewrite_clears_the_stream_before_the_second_reply():
    seen = []
    token = begin_scaffold_progress(seen.append)
    chunks = [
        ['{"文字": "引导学生"'],
        ['{"文字": "引导学生"', '{"文字": "你看空序列。"'],
    ]

    def complete(messages):
        complete.calls.append(messages)
        for raw in chunks.pop(0):
            feed_scaffold_stream(raw)
        return complete.replies.pop(0)

    complete.calls = []
    complete.replies = [_reply("引导学生"), _reply("你看空序列。")]
    questions, answers = _materials()
    try:
        draft = ModelScaffoldAgent(complete).produce("反馈", "还缺什么？", questions, answers)
    finally:
        end_scaffold_progress(token)

    assert draft.text == "你看空序列。"
    assert seen == ["引导学生", "引导学生", "你看空序列。"]
```

在 `tests/test_model_trace.py` 的 `test_scaffold_generation_records_the_type_and_the_body` 后面追加：

```python
def test_a_rewritten_scaffold_records_the_final_wording(traces):
    first = json.dumps({"文字": "引导学生看空序列。", "源码": ""}, ensure_ascii=False)
    second = json.dumps({"文字": "你看空序列。", "源码": ""}, ensure_ascii=False)
    replies = [first, second]
    questions = (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),)
    answers = (ItemAnswer(selected=("正确",)),)

    draft = ModelScaffoldAgent(lambda _messages: replies.pop(0)).produce(
        "反馈",
        "还缺什么？",
        questions,
        answers,
    )

    assert draft.text == "你看空序列。"
    assert len(traces) == 1
    assert traces[0]["metadata"]["支架类型"] == "反馈"
    assert traces[0]["metadata"]["支架正文"] == "你看空序列。"
    assert traces[0]["output"] == first


def test_a_failed_rewrite_keeps_the_first_record(traces):
    first = json.dumps({"文字": "引导学生看空序列。", "源码": ""}, ensure_ascii=False)
    replies = [first, RuntimeError("down")]
    questions = (TrueFalseQuestion("判断说法", "正确", "题目里有依据"),)
    answers = (ItemAnswer(selected=("正确",)),)

    def complete(_messages):
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    with pytest.raises(RuntimeError):
        ModelScaffoldAgent(complete).produce("反馈", "还缺什么？", questions, answers)

    assert len(traces) == 1
    assert traces[0]["output"] == first
    assert "支架正文" not in traces[0]["metadata"]
```

保留 `test_produce_returns_the_model_wording_and_calls_once`、`test_empty_strings_do_not_fail` 和 `test_a_bad_reply_or_completer_error_propagates`。它们继续证明不含禁语时只调用一次。

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_model_scaffold_agent.py tests/test_model_trace.py::test_a_rewritten_scaffold_records_the_final_wording tests/test_model_trace.py::test_a_failed_rewrite_keeps_the_first_record -v`

Expected: FAIL。`clear_scaffold_progress` 尚不存在，导入失败。含「引导学生」的用例若已能导入，则实际只调用一次，`calls` 长度为 1，草稿文字仍是第一稿。

- [ ] **Step 3: Write minimal implementation**

在 `begin_scaffold_progress` 和 `end_scaffold_progress` 旁边增加：

```python
def clear_scaffold_progress() -> None:
    progress = _progress.get()
    if progress is None:
        return
    progress.shown = ""
```

在 `_SYSTEM` 前面增加：

```python
_FORBIDDEN = ("学生", "教师", "引导", "让学生", "请学生", "学情")


def _teacher_voice(text: str) -> bool:
    return any(word in text for word in _FORBIDDEN)
```

把 `ModelScaffoldAgent.produce` 换成：

```python
    def produce(
        self,
        scaffold_type: str,
        question: str,
        questions: tuple,
        answers: tuple,
        passages: tuple[tuple[str, str], ...] = (),
        example_source: str = "",
    ) -> ScaffoldDraft:
        messages = build_messages(
            scaffold_type,
            question,
            questions,
            answers,
            passages,
            example_source=example_source,
        )
        with tracing_model_call("支架", 支架类型=scaffold_type) as meta:
            text = self._complete(messages)
            if isinstance(text, str):
                remember_model_result(messages, text)
            draft = parse_scaffold(text)
            if _teacher_voice(draft.text):
                clear_scaffold_progress()
                follow = (
                    messages[0],
                    messages[1],
                    {
                        "role": "user",
                        "content": "上一稿是在对教师说话，按规则改成直接对学生说的话。\n上一稿："
                        + draft.text,
                    },
                )
                text = self._complete(follow)
                if isinstance(text, str):
                    remember_model_result(follow, text)
                draft = parse_scaffold(text)
            meta["支架正文"] = draft.text
            return draft
```

不要改 `remember_model_result`。它见到已有输出就返回，所以追踪里的 `output` 仍是第一份字符串。第二次在返回字符串之前抛出异常时，第一份记录留着，异常继续向外传。`meta["支架正文"]` 只在第二次解析成功后赋值；第二次解析失败时不会改成第一稿。

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_model_scaffold_prompt.py tests/test_model_scaffold_agent.py tests/test_model_trace.py tests/test_scaffold_stream.py tests/test_model_decision_prompt.py -v`

Expected: PASS。新用例覆盖一次重写、第二次仍命中、空白、源码里的「学生」、第一次失败、第二次失败、流式进度被清空，「支架正文」是最终文字，以及第二次抛出异常时追踪只留下第一份字符串。决策智能体的提示词测试保持通过。

- [ ] **Step 5: Commit**

```powershell
git add src/scaffolding/model_scaffold.py tests/test_model_scaffold_agent.py tests/test_model_trace.py
git commit -m "fix: rewrite scaffold text that speaks to the teacher"
```
