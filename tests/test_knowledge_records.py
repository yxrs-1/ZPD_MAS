import pytest

from scaffolding.knowledge import CurriculumStandard, LessonSource, TextbookLesson


def test_lesson_and_standard_keep_their_sources():
    lesson = TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "人员、硬件、软件、数据和网络")
    standard = CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "信息意识、计算思维、数字化学习与创新、信息社会责任")

    assert lesson.source() == LessonSource("人教版", "必修一", "信息系统的组成", "高中", "12-15")
    assert lesson.text == "人员、硬件、软件、数据和网络"
    assert standard.source().name == "普通高中信息科技课程标准"
    assert standard.source().stage == "高中"
    assert standard.source().clauses == "1.1.2"
    assert standard.source().current is True
    assert standard.text.startswith("信息意识")


@pytest.mark.parametrize(
    "build",
    [
        lambda: TextbookLesson(" ", "必修一", "组成", "高中", "12", "原文"),
        lambda: TextbookLesson("人教版", " ", "组成", "高中", "12", "原文"),
        lambda: TextbookLesson("人教版", "必修一", " ", "高中", "12", "原文"),
        lambda: TextbookLesson("人教版", "必修一", "组成", " ", "12", "原文"),
        lambda: TextbookLesson("人教版", "必修一", "组成", "高中", " ", "原文"),
        lambda: TextbookLesson("人教版", "必修一", "组成", "高中", "12", " "),
        lambda: CurriculumStandard(" ", "高中", "1.1", "全文"),
        lambda: CurriculumStandard("课标", " ", "1.1", "全文"),
        lambda: CurriculumStandard("课标", "高中", " ", "全文"),
        lambda: CurriculumStandard("课标", "高中", "1.1", " "),
    ],
)
def test_blank_fields_are_rejected(build):
    with pytest.raises(ValueError):
        build()
