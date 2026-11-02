import asyncio

from fastapi import APIRouter, Depends, UploadFile
from pydantic import BaseModel

from scaffolding.scaffold_decision import decide_scaffold_type
from zpd_api.db import session_factory
from zpd_api.llm import deepseek_client
from zpd_api.repository import SqlRepository
from zpd_api.retrieval import retrieve_passages
from zpd_api.worker import enqueue_ingest

router = APIRouter()


class DecisionBody(BaseModel):
    student_id: str
    task_id: str
    student_state: str
    student_answer: str


async def get_repo():
    async with session_factory()() as session:
        yield SqlRepository(session)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/scaffold-decisions")
async def scaffold_decision(body: DecisionBody, repo: SqlRepository = Depends(get_repo)) -> dict:
    previous = await repo.previous(body.student_id, body.task_id)
    decision = await decide_scaffold_type(
        body.student_state,
        body.student_answer,
        previous,
        client=deepseek_client(),
    )
    query = decision.scaffold_type.value + "\n" + body.student_answer
    passages = await asyncio.to_thread(retrieve_passages, query)
    await repo.save_decision(
        student_id=body.student_id,
        task_id=body.task_id,
        student_state=body.student_state,
        student_answer=body.student_answer,
        scaffold_type=decision.scaffold_type.value,
        content=decision.reason,
        reason=decision.reason,
    )
    return {
        "scaffold_type": decision.scaffold_type.value,
        "reason": decision.reason,
        "passages": passages,
    }


@router.post("/documents")
async def upload_document(file: UploadFile, repo: SqlRepository = Depends(get_repo)) -> dict:
    content = await file.read()
    material_id = await repo.add_material(file.filename or "upload", content)
    enqueue_ingest(material_id)
    return {"id": material_id, "status": "queued"}
