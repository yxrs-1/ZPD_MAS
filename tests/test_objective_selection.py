from scaffolding.knowledge import (
    CurriculumStandard,
    LessonRetrieval,
    LessonSource,
    StageRetrieval,
    StandardSource,
    TextbookLesson,
)
from scaffolding.objectives import ObjectiveDraft, select_objectives


def _retrieval():
    lesson = TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文")
    standard = CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文")
    return LessonRetrieval(lesson.text, lesson.source(), standard.text, standard.source())


def test_valid_drafts_keep_their_order_and_a_missing_dimension_stays_missing():
    retrieval = _retrieval()
    drafts = (
        ObjectiveDraft("计算思维", "能描述组成", retrieval.lesson_source),
        ObjectiveDraft("超纲维度", "不算", retrieval.lesson_source),
        ObjectiveDraft("信息意识", " ", retrieval.standard_source),
        ObjectiveDraft("信息意识", "能识别信息", retrieval.standard_source),
        ObjectiveDraft("信息社会责任", "外来目标", LessonSource("其他版", "必修一", "其他课", "高中", "1")),
        ObjectiveDraft("数字化学习与创新", "现行标记不对", StandardSource("普通高中信息科技课程标准", "高中", "1.1.2", current=False)),
        ObjectiveDraft("信息意识", " 能再举一例 ", retrieval.lesson_source),
    )

    kept = select_objectives(drafts, retrieval)

    assert [(item.dimension, item.statement, item.source) for item in kept] == [
        ("计算思维", "能描述组成", retrieval.lesson_source),
        ("信息意识", "能识别信息", retrieval.standard_source),
        ("信息意识", " 能再举一例 ", retrieval.lesson_source),
    ]


def test_stage_retrieval_keeps_only_the_standard_source():
    standard = CurriculumStandard("义务教育信息科技课程标准", "初中", "2.1", "初中课标全文")
    retrieval = StageRetrieval(standard.text, standard.source())
    lesson_source = LessonSource("人教版", "必修一", "信息系统的组成", "初中", "12-15")
    drafts = (
        ObjectiveDraft("信息社会责任", "遵守规范", retrieval.standard_source),
        ObjectiveDraft("信息意识", "课时目标", lesson_source),
    )

    kept = select_objectives(drafts, retrieval)

    assert kept == (drafts[0],)
