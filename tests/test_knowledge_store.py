import pytest

from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, Rejected, TextbookLesson


def _lesson(lesson: str = "信息系统的组成", version: str = "人教版", volume: str = "必修一") -> TextbookLesson:
    return TextbookLesson(version, volume, lesson, "高中", "12-15", "人员、硬件、软件、数据和网络")


def _standard(stage: str = "高中", name: str = "普通高中信息科技课程标准") -> CurriculumStandard:
    return CurriculumStandard(name, stage, "1.1.2", "四个核心素养")


def test_duplicate_lesson_and_standard_keep_the_original():
    base = KnowledgeBase()
    original = _lesson()
    base.add_lesson(original)
    base.add_standard(_standard())

    with pytest.raises(Rejected):
        base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "99", "另一份原文"))
    with pytest.raises(Rejected):
        base.add_standard(_standard(name="另一份课标"))

    assert base.lesson_count() == 1
    assert base.standard_count() == 1
    stored = base.get_lesson("人教版", "必修一", "信息系统的组成")
    assert stored is original
    assert base.get_standard("高中").name == "普通高中信息科技课程标准"


def test_a_different_lesson_key_can_be_stored():
    base = KnowledgeBase()
    base.add_lesson(_lesson())
    base.add_lesson(_lesson(version="沪科教版"))
    base.add_lesson(_lesson(volume="必修二"))
    base.add_lesson(_lesson(lesson="数据与编码"))
    base.add_standard(_standard())
    base.add_standard(_standard(stage="初中", name="义务教育信息科技课程标准"))

    assert base.lesson_count() == 4
    assert base.standard_count() == 2
