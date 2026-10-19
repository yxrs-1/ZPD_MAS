from scaffolding.objectives import ObjectiveCatalog, ObjectiveDraft
from scaffolding.records import ChoiceQuestion, OpenQuestion, SelectionMode, TrueFalseQuestion
from tests.objective_helpers import ScriptedExtractor, sample_base


class ScriptedGenerator:
    def __init__(self) -> None:
        self.questions = ()
        self.error = None
        self.calls = []

    def generate(self, counts, objectives):
        self.calls.append((counts, objectives))
        if self.error is not None:
            raise self.error
        return self.questions


def single(prompt: str = "单选题") -> ChoiceQuestion:
    return ChoiceQuestion(prompt, SelectionMode.SINGLE, ("甲", "乙"), ("甲",), "解析")


def multiple() -> ChoiceQuestion:
    return ChoiceQuestion("多选题", SelectionMode.MULTIPLE, ("甲", "乙", "丙"), ("甲", "丙"), "解析")


def judged() -> TrueFalseQuestion:
    return TrueFalseQuestion("判断题", "正确", "解析")


def opened() -> OpenQuestion:
    return OpenQuestion("综合题", "写出过程")


def prepared_objectives():
    base = sample_base()
    retrieval = base.retrieve_lesson("人教版", "必修一", "信息系统的组成")
    extractor = ScriptedExtractor()
    extractor.lesson_results = (ObjectiveDraft("信息意识", "能识别信息", retrieval.lesson_source),)
    objectives = ObjectiveCatalog(base, extractor)
    objectives.extract_lesson("人教版", "必修一", "信息系统的组成")
    return base, objectives
