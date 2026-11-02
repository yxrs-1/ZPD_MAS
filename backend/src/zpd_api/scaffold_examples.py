from zpd_api.db import sync_session_factory
from zpd_api.models import Base, ScaffoldExampleRow


def load_examples(task_id: str) -> dict:
    factory = sync_session_factory()
    engine = factory.kw["bind"]
    Base.metadata.create_all(engine, tables=[ScaffoldExampleRow.__table__])
    with factory() as session:
        rows = session.query(ScaffoldExampleRow).filter(ScaffoldExampleRow.task_id == task_id).all()
    return {row.kind: (row.source, row.svg.encode()) for row in rows}


def save_examples(task_id: str, examples: dict) -> None:
    factory = sync_session_factory()
    engine = factory.kw["bind"]
    Base.metadata.create_all(engine, tables=[ScaffoldExampleRow.__table__])
    with factory() as session:
        session.query(ScaffoldExampleRow).filter(ScaffoldExampleRow.task_id == task_id).delete()
        for kind, (source, svg) in examples.items():
            session.add(ScaffoldExampleRow(
                task_id=task_id,
                kind=kind,
                source=source,
                svg=svg.decode() if isinstance(svg, bytes) else svg,
            ))
        session.commit()


def prepare_examples(task_id: str, questions: tuple, complete) -> None:
    from scaffolding.scaffold_figures import build_examples, example_messages

    reply = complete(example_messages(questions))
    if not isinstance(reply, str):
        return
    examples = build_examples(reply)
    if examples:
        save_examples(task_id, examples)
