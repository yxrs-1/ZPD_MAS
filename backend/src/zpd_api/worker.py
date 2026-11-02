import os

from celery import Celery

from zpd_api.ingest import ingest_material

celery_app = Celery("zpd", broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


@celery_app.task(name="zpd.ingest_material")
def ingest_material_task(material_id: int) -> None:
    ingest_material(material_id)


def enqueue_ingest(material_id: int) -> None:
    ingest_material_task.delay(material_id)


@celery_app.task(name="zpd.prepare_scaffold_examples")
def prepare_scaffold_examples_task(task_id: str) -> None:
    from zpd_api.models import TaskRow
    from zpd_api.scaffold_examples import prepare_examples
    from scaffolding.model_generator import deepseek_complete, post_json
    from scaffolding.store import _question

    factory = __import__("zpd_api.db", fromlist=["sync_session_factory"]).sync_session_factory()
    with factory() as session:
        row = session.query(TaskRow).filter(TaskRow.task_id == task_id).one_or_none()
        questions = () if row is None else tuple(_question(item) for item in row.questions)
    if not questions:
        return

    def complete(messages):
        return deepseek_complete(messages, post=post_json)

    prepare_examples(task_id, questions, complete)


def enqueue_scaffold_examples(task_id: str) -> None:
    prepare_scaffold_examples_task.delay(task_id)
