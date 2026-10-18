from pathlib import Path

from scaffolding.agents import ScaffoldDraft
from scaffolding.html_assets import export_assets
from scaffolding.records import Asset, AssetKind, HelpSource, OpenQuestion, TrueFalseQuestion
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session
from scaffolding.tasks import TaskCatalog


def _started(decision, scaffold_agent) -> Session:
    catalog = TaskCatalog()
    task = catalog.create(
        (
            TrueFalseQuestion("判断说法", "正确", "按题目判断"),
            OpenQuestion("完成一份信息系统组成说明", "说明人员、硬件、软件、数据和网络"),
        )
    )
    catalog.publish(task.task_id)
    return Session(catalog, catalog.start(task.task_id), decision, scaffold_agent)


def test_teacher_sample_matches_the_scaffolding_loop_spec(tmp_path: Path):
    decision = ScriptedDecisionAgent(presets=("组成还缺哪一类？",), scaffold_type="提示")
    clicked_agent = ScriptedScaffoldAgent(
        ScaffoldDraft(
            text="提示：组成还缺哪一类？",
            html='<article>整页不能导出</article><asset kind="思维导图" name="map.svg">map</asset>',
            assets=(Asset(AssetKind.IMAGE, "photo.png", b"img"),),
        )
    )
    session = _started(decision, clicked_agent)

    before = session.view()
    assert before.presets == ("组成还缺哪一类？",)
    assert before.scaffold is None

    clicked = session.ask("组成还缺哪一类？", HelpSource.PRESET)
    call = clicked_agent.calls[0]
    assert call["question"] == "组成还缺哪一类？"
    assert call["scaffold_type"] == "提示"
    assert set(call) == {"scaffold_type", "question", "questions", "answers"}
    assert clicked.scaffold is not None
    assert "组成还缺哪一类？" in clicked.scaffold.text
    assert [asset.kind for asset in clicked.scaffold.assets] == [AssetKind.IMAGE, AssetKind.MIND_MAP]

    export_assets(clicked.scaffold, tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["map.svg", "photo.png"]
    assert "整页不能导出".encode() not in b"".join(path.read_bytes() for path in tmp_path.iterdir())

    own_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="解释：网络要不要写？"))
    own = _started(
        ScriptedDecisionAgent(presets=("组成还缺哪一类？",), scaffold_type="解释"),
        own_agent,
    )
    own.edit_answer(1, text="人员硬件都写了")
    written = own.ask("网络要不要写？", HelpSource.OWN)
    assert own_agent.calls[0]["question"] == "网络要不要写？"
    assert "人员硬件都写了" in own_agent.calls[0]["answers"][1].text
    assert written.scaffold is not None
    assert written.scaffold.text == "解释：网络要不要写？"

    silent_agent = ScriptedScaffoldAgent(clicked_agent.draft)
    silent = _started(decision, silent_agent)
    silent.ask("   ", HelpSource.OWN)
    refused = _started(
        ScriptedDecisionAgent(presets=("组成还缺哪一类？",), scaffold_type="第4级"),
        ScriptedScaffoldAgent(clicked_agent.draft),
    )
    failed = refused.ask("组成还缺哪一类？", HelpSource.PRESET)
    empty = _started(
        ScriptedDecisionAgent(presets=("组成还缺哪一类？",), scaffold_type="反馈"),
        ScriptedScaffoldAgent(ScaffoldDraft()),
    )
    blank = empty.ask("组成还缺哪一类？", HelpSource.PRESET)
    broken = _started(
        ScriptedDecisionAgent(presets=("组成还缺哪一类？",), error=RuntimeError("down")),
        ScriptedScaffoldAgent(clicked_agent.draft),
    )
    called = broken.ask("组成还缺哪一类？", HelpSource.PRESET)

    assert silent.view().scaffold is None
    assert silent_agent.calls == []
    assert failed.scaffold is None and failed.presets == ("组成还缺哪一类？",)
    assert blank.scaffold is None and blank.presets == ("组成还缺哪一类？",)
    assert called.scaffold is None and called.presets == ("组成还缺哪一类？",)
