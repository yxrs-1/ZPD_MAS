import json

import pytest

from scaffolding.generation import LessonOrigin, QuestionCounts, Rejected, StageOrigin, TaskGeneration
from scaffolding.knowledge import CurriculumStandard
from scaffolding.model_generator import ModelQuestionGenerator, build_messages
from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.records import ChoiceQuestion, SelectionMode
from scaffolding.tasks import TaskCatalog
from tests.generation_helpers import prepared_objectives
from tests.objective_helpers import ScriptedExtractor


class RecordingComplete:
    def __init__(self, text: str = "", error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        if self.error is not None:
            raise self.error
        return self.text


def _reply(**overrides) -> str:
    body = {
        "单选": [
            {"题目": "单选乙", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["乙"], "解析": "原因"},
            {"题目": "单选甲", "选项": ["甲", "乙", "丙", "丁"], "参考答案": ["甲"], "解析": "原因"},
        ],
        "多选": [],
        "判断": [
            {"题目": "判断题", "参考答案": "正确", "解析": "原因"},
        ],
        "综合": [],
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


def test_a_matching_reply_creates_an_unpublished_task_for_each_origin():
    base, objectives = prepared_objectives()
    base.add_standard(CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文"))
    junior = base.retrieve_stage("初中")
    extractor = ScriptedExtractor()
    extractor.stage_results = (ObjectiveDraft("信息社会责任", "遵守规范", junior.standard_source),)
    stage_objectives = ObjectiveCatalog(base, extractor)
    stage_objectives.extract_stage("初中")
    complete = RecordingComplete(_reply())
    tasks = TaskCatalog()
    generation = TaskGeneration(objectives, tasks, ModelQuestionGenerator(complete))

    task = generation.generate_lesson(
        "人教版", "必修一", "信息系统的组成", single=2, multiple=0, true_false=1, open_ended=0
    )

    assert task.published is False
    assert [question.prompt for question in task.questions] == ["单选乙", "单选甲", "判断题"]
    assert generation.origin(task.task_id) == LessonOrigin("人教版", "必修一", "信息系统的组成")
    assert complete.calls == [
        build_messages(
            QuestionCounts(2, 0, 1, 0),
            objectives.lesson_objectives("人教版", "必修一", "信息系统的组成"),
        )
    ]
    stage_complete = RecordingComplete(_reply(单选=[], 判断=[{"题目": "学段判断", "参考答案": "正确", "解析": "原因"}]))
    stage_generation = TaskGeneration(stage_objectives, tasks, ModelQuestionGenerator(stage_complete))
    stage_task = stage_generation.generate_stage("初中", single=0, multiple=0, true_false=1, open_ended=0)
    assert stage_generation.origin(stage_task.task_id) == StageOrigin("初中")
    assert len(stage_complete.calls) == 1


def test_guards_do_not_call_the_completer():
    _, objectives = prepared_objectives()
    complete = RecordingComplete(_reply())
    tasks = TaskCatalog()
    generation = TaskGeneration(objectives, tasks, ModelQuestionGenerator(complete))

    with pytest.raises(Rejected):
        generation.generate_lesson("沪科教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=0, multiple=0, true_false=0, open_ended=0)
    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=1.5, multiple=0, true_false=0, open_ended=0)

    assert complete.calls == []


def test_a_bad_reply_or_count_mismatch_creates_nothing():
    _, objectives = prepared_objectives()
    tasks = TaskCatalog()
    existing = tasks.create((ChoiceQuestion("已有题", SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析"),))
    fenced = RecordingComplete("```json\n" + _reply() + "\n```")
    generation = TaskGeneration(objectives, tasks, ModelQuestionGenerator(fenced))

    with pytest.raises(Rejected):
        generation.generate_lesson("人教版", "必修一", "信息系统的组成", single=2, multiple=0, true_false=1, open_ended=0)
    mismatched = RecordingComplete(_reply())
    mismatched_generation = TaskGeneration(objectives, tasks, ModelQuestionGenerator(mismatched))
    with pytest.raises(Rejected):
        mismatched_generation.generate_lesson(
            "人教版", "必修一", "信息系统的组成", single=1, multiple=0, true_false=0, open_ended=0
        )
    failing = RecordingComplete(error=RuntimeError("down"))
    failed = TaskGeneration(objectives, tasks, ModelQuestionGenerator(failing))
    with pytest.raises(RuntimeError):
        failed.generate_lesson("人教版", "必修一", "信息系统的组成", single=2, multiple=0, true_false=1, open_ended=0)

    assert len(fenced.calls) == 1
    assert len(mismatched.calls) == 1
    assert len(failing.calls) == 1
    assert tasks.get(existing.task_id).questions[0].prompt == "已有题"
    assert generation.origin(existing.task_id) is None
    with pytest.raises(KeyError):
        tasks.get("task-2")
