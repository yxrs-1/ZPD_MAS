import json


def choice(prompt, answers=("甲",)):
    return {"题目": prompt, "选项": ["甲", "乙"], "参考答案": list(answers), "解析": "解析"}


def judged(prompt="判断题", answer="正确"):
    return {"题目": prompt, "参考答案": answer, "解析": "解析"}


def opened(prompt="综合题"):
    return {"题目": prompt, "作答要求": "写出过程", "参考答案": "", "解析": ""}


def body(reading=None, objectives=None, questions=None):
    if reading is None:
        reading = {"单选": 1, "多选": "未指定", "判断": 0, "综合": "未指定"}
    if objectives is None:
        objectives = [{"维度": "信息意识", "表述": "能识别信息"}]
    if questions is None:
        questions = {
            "单选": [choice("第一")],
            "多选": [],
            "判断": [],
            "综合": [opened()],
        }
    return {"读法": reading, "目标": objectives, "题目": questions}


def dumped(**kwargs):
    return json.dumps(body(**kwargs), ensure_ascii=False)
