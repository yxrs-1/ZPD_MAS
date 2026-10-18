from pathlib import Path

from scaffolding.agents import ScaffoldDraft
from scaffolding.html_assets import export_assets
from scaffolding.records import AnswerState, Asset, AssetKind, HelpSource, TaskRecord, TaskStatement
from scaffolding.scripted import ScriptedDecisionAgent, ScriptedScaffoldAgent
from scaffolding.session import Session


def _sample(answer: AnswerState = AnswerState()) -> TaskRecord:
    return TaskRecord(
        statement=TaskStatement(
            prompt="判断说法，并完成一份信息系统组成说明",
            choices=("正确", "错误"),
            requirements="说明人员、硬件、软件、数据和网络",
        ),
        answer=answer,
    )


def test_teacher_sample_matches_the_scaffolding_loop_spec(tmp_path: Path):
    decision = ScriptedDecisionAgent(presets=("组成还缺哪一类？",), scaffold_type="提示")
    clicked_agent = ScriptedScaffoldAgent(
        ScaffoldDraft(
            text="提示：组成还缺哪一类？",
            html='<article>整页不能导出</article><asset kind="思维导图" name="map.svg">map</asset>',
            assets=(Asset(AssetKind.IMAGE, "photo.png", b"img"),),
        )
    )
    session = Session(_sample(), decision, clicked_agent)

    before = session.view()
    assert before.presets == ("组成还缺哪一类？",)
    assert before.scaffold is None

    clicked = session.ask("组成还缺哪一类？", HelpSource.PRESET)
    call = clicked_agent.calls[0]
    assert call["question"] == "组成还缺哪一类？"
    assert call["scaffold_type"] == "提示"
    assert set(call) == {"scaffold_type", "question", "statement", "answer"}
    assert clicked.scaffold is not None
    assert "组成还缺哪一类？" in clicked.scaffold.text
    assert [asset.kind for asset in clicked.scaffold.assets] == [AssetKind.IMAGE, AssetKind.MIND_MAP]

    export_assets(clicked.scaffold, tmp_path)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["map.svg", "photo.png"]
    assert "整页不能导出".encode() not in b"".join(path.read_bytes() for path in tmp_path.iterdir())

    own_agent = ScriptedScaffoldAgent(ScaffoldDraft(text="解释：网络要不要写？"))
    own = Session(
        _sample(AnswerState(content="判断：正确", revisions=("判断：",))),
        ScriptedDecisionAgent(presets=("组成还缺哪一类？",), scaffold_type="解释"),
        own_agent,
    )
    written = own.ask("网络要不要写？", HelpSource.OWN)
    assert own_agent.calls[0]["question"] == "网络要不要写？"
    assert written.scaffold is not None
    assert written.scaffold.text == "解释：网络要不要写？"

    silent_agent = ScriptedScaffoldAgent(clicked_agent.draft)
    silent = Session(_sample(), decision, silent_agent)
    silent.ask("   ", HelpSource.OWN)
    refused = Session(
        _sample(),
        ScriptedDecisionAgent(presets=("组成还缺哪一类？",), scaffold_type="第4级"),
        ScriptedScaffoldAgent(clicked_agent.draft),
    )
    failed = refused.ask("组成还缺哪一类？", HelpSource.PRESET)
    empty = Session(
        _sample(),
        ScriptedDecisionAgent(presets=("组成还缺哪一类？",), scaffold_type="反馈"),
        ScriptedScaffoldAgent(ScaffoldDraft()),
    )
    blank = empty.ask("组成还缺哪一类？", HelpSource.PRESET)
    broken = Session(
        _sample(),
        ScriptedDecisionAgent(presets=("组成还缺哪一类？",), error=RuntimeError("down")),
        ScriptedScaffoldAgent(clicked_agent.draft),
    )
    called = broken.ask("组成还缺哪一类？", HelpSource.PRESET)

    assert silent.view().scaffold is None
    assert silent_agent.calls == []
    assert failed.scaffold is None and failed.presets == ("组成还缺哪一类？",)
    assert blank.scaffold is None and blank.presets == ("组成还缺哪一类？",)
    assert called.scaffold is None and called.presets == ("组成还缺哪一类？",)
