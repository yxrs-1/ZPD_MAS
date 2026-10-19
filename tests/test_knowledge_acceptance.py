from pathlib import Path

import pytest

from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, Rejected, TextbookLesson


def test_knowledge_retrieval_spec_is_in_the_workspace():
    spec = Path(__file__).resolve().parents[1] / "docs" / "superpowers" / "specs" / "2026-10-18-knowledge-retrieval-design.md"
    assert spec.is_file()


def test_retrieval_matches_the_spec():
    base = KnowledgeBase()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))

    found = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    assert found is not None
    assert found.lesson_text == "课时原文"
    assert (found.lesson_source.version, found.lesson_source.volume, found.lesson_source.lesson, found.lesson_source.stage, found.lesson_source.pages) == ("人教版", "必修一", "信息系统的组成", "高中", "12-15")
    assert found.standard_source.current is True

    stage_only = base.retrieve_stage("高中")
    assert stage_only is not None
    assert stage_only.standard_text == "课标全文"
    assert not hasattr(stage_only, "lesson_text")

    assert base.retrieve_lesson("人教版", "必修一", "不存在的课时") is None
    bare = KnowledgeBase()
    bare.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    assert bare.retrieve_lesson("人教版", "必修一", "信息系统的组成") is None

    with pytest.raises(Rejected):
        base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "20", "新原文"))
    with pytest.raises(Rejected):
        base.add_standard(CurriculumStandard("另一份高中课标", "高中", "2.1", "另一份全文"))
    assert base.get_lesson("人教版", "必修一", "信息系统的组成").text == "课时原文"
    assert base.retrieve_lesson("沪科教版", "必修一", "信息系统的组成") is None
