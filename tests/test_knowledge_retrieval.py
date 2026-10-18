from scaffolding.knowledge import CurriculumStandard, KnowledgeBase, TextbookLesson


def _base() -> KnowledgeBase:
    base = KnowledgeBase()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))
    return base


def test_lesson_retrieval_returns_the_text_and_both_sources():
    found = _base().retrieve_lesson("人教版", "必修一", "信息系统的组成")

    assert found is not None
    assert found.lesson_text == "课时原文"
    assert found.lesson_source.version == "人教版"
    assert found.lesson_source.volume == "必修一"
    assert found.lesson_source.lesson == "信息系统的组成"
    assert found.lesson_source.stage == "高中"
    assert found.lesson_source.pages == "12-15"
    assert found.standard_text == "课标全文"
    assert found.standard_source.name == "普通高中信息科技课程标准"
    assert found.standard_source.stage == "高中"
    assert found.standard_source.clauses == "1.1.2"
    assert found.standard_source.current is True


def test_stage_retrieval_returns_only_the_current_standard():
    found = _base().retrieve_stage("高中")

    assert found is not None
    assert found.standard_text == "课标全文"
    assert found.standard_source.current is True
    assert not hasattr(found, "lesson_text")
    assert not hasattr(found, "lesson_source")


def test_missing_half_returns_nothing():
    lesson_only = KnowledgeBase()
    lesson_only.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    standard_only = KnowledgeBase()
    standard_only.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))

    assert lesson_only.retrieve_lesson("人教版", "必修一", "信息系统的组成") is None
    assert standard_only.retrieve_lesson("人教版", "必修一", "信息系统的组成") is None
    assert KnowledgeBase().retrieve_stage("高中") is None


def test_a_different_key_does_not_return_the_stored_lesson():
    base = _base()

    assert base.retrieve_lesson("沪科教版", "必修一", "信息系统的组成") is None
    assert base.retrieve_lesson("人教版", "必修二", "信息系统的组成") is None
    assert base.retrieve_lesson("人教版", "必修一", "数据与编码") is None
    assert base.retrieve_stage("初中") is None
