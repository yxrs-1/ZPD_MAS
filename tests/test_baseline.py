from pathlib import Path


def test_scaffolding_loop_spec_is_in_the_workspace():
    spec = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "superpowers"
        / "specs"
        / "2026-10-18-scaffolding-loop-design.md"
    )
    assert spec.is_file()
