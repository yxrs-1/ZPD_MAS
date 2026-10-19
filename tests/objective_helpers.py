from scaffolding.knowledge import (
    CurriculumStandard,
    KnowledgeBase,
    LessonRetrieval,
    StageRetrieval,
    TextbookLesson,
)


class ScriptedExtractor:
    def __init__(self) -> None:
        self.lesson_results = ()
        self.stage_results = ()
        self.lesson_error = None
        self.stage_error = None
        self.calls = []

    def extract(self, retrieval):
        self.calls.append(retrieval)
        if isinstance(retrieval, LessonRetrieval):
            if self.lesson_error is not None:
                raise self.lesson_error
            return self.lesson_results
        if isinstance(retrieval, StageRetrieval):
            if self.stage_error is not None:
                raise self.stage_error
            return self.stage_results
        raise AssertionError("extractor received something other than a retrieval")


def sample_base() -> KnowledgeBase:
    base = KnowledgeBase()
    base.add_lesson(TextbookLesson("人教版", "必修一", "信息系统的组成", "高中", "12-15", "课时原文"))
    base.add_standard(CurriculumStandard("普通高中信息科技课程标准", "高中", "1.1.2", "课标全文"))
    return base
