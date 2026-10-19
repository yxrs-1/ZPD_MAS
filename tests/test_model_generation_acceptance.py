import json
from pathlib import Path

import pytest

from scaffolding.generation import LessonOrigin, Rejected, StageOrigin, TaskGeneration
from scaffolding.knowledge import CurriculumStandard
from scaffolding.model_generator import DEEPSEEK_URL, ModelQuestionGenerator, deepseek_complete
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.records import ChoiceQuestion, SelectionMode
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import prepared_objectives
from tests.objective_helpers import ScriptedExtractor


def _reply() -> str:
    return json.dumps(
        {
            "单选": [
                {"题目": "单选甲", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["甲"], "解析": "原因"},
            ],
            "多选": [],
            "判断": [],
            "综合": [],
        },
        ensure_ascii=False,
    )


def test_model_task_generator_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-19-model-task-generator-design.md"
    assert spec.is_file()


def test_generation_uses_one_reply_and_keeps_existing_task_rules():
    base, objectives = prepared_objectives()
    stored_lesson = base.get_lesson("人教版", "必修一", "信息系统的组成")
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    junior = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", junior.standard_source),)
    stage_objectives = ObjectiveCatalog(base, extractor)
    stage_objectives.extract_stage("初中")
    calls = []

    def complete(messages):
        calls.append(messages)
        return _reply()

    tasks = TaskCatalog()
    existing = tasks.create((ChoiceQuestion("已有题", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析"),))
    generation = TaskGeneration(objectives, tasks, ModelQuestionGenerator(complete))
    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
    )

    assert task.published is False
    assert [question.prompt for question in task.questions] == ["单选甲"]
    assert task.questions[0].choices == ("甲", "乙", "丙", "丁")
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert len(calls) == 1
    assert "课时原文" not in calls[0][1]["content"]
    assert "objective-1" not in calls[0][1]["content"]

    def fail(messages):
        calls.append(messages)
        return "```json\n" + _reply() + "\n```"

    with pytest.raises(Rejected):
        TaskGeneration(objectives, tasks, ModelQuestionGenerator(fail)).generate_lesson(
            "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
        )
    assert tasks.get(existing.task_id).questions[0].prompt == "已有题"
    with pytest.raises(KeyError):
        tasks.get("task-3")

    stage_calls = []

    def stage_complete(messages):
        stage_calls.append(messages)
        return json.dumps(
            {
                "单选": [],
                "多选": [],
                "判断": [{"题目": "学段判断", "参考答案": "正确", "解析": "原因"}],
                "综合": [],
            },
            ensure_ascii=False,
        )

    stage_generation = TaskGeneration(stage_objectives, tasks, ModelQuestionGenerator(stage_complete))
    stage_task = stage_generation.generate_stage("初中", single=0, multiple=0, true_false=1, open_ended=0)
    assert stage_generation.origin(stage_task.task_id) == StageOrigin("初中")
    assert stage_task.questions[0].prompt == "学段判断"
    assert len(stage_calls) == 1
    sent = []

    def post(url, headers, payload):
        sent.append((url, headers, payload))
        return 200, {"choices": [{"message": {"content": _reply()}}]}

    assert deepseek_complete(calls[0], post=post, api_key="secret") == _reply()
    assert sent[0][0] == DEEPSEEK_URL
    assert sent[0][1]["Authorization"] == "Bearer secret"
    assert sent[0][2]["model"] == "deepseek-flash"
    assert sent[0][2]["stream"] is False
    assert sent[0][2]["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in sent[0][2]
    assert base.get_lesson("人教版", "必修一", "信息系统的组成") is stored_lesson
    ChoiceQuestion("两个选项", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析")
