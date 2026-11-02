import os
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from scaffolding.records import ScaffoldType
from scaffolding.scaffold_decision import PreviousScaffold
from zpd_api.models import Material, ScaffoldEvent


class SqlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def previous(self, student_id: str, task_id: str) -> list[PreviousScaffold]:
        result = await self.session.execute(
            select(ScaffoldEvent)
            .where(ScaffoldEvent.student_id == student_id, ScaffoldEvent.task_id == task_id)
            .order_by(ScaffoldEvent.id)
        )
        return [
            PreviousScaffold(scaffold_type=ScaffoldType(row.scaffold_type), content=row.content)
            for row in result.scalars()
        ]

    async def save_decision(
        self,
        *,
        student_id: str,
        task_id: str,
        student_state: str,
        student_answer: str,
        scaffold_type: str,
        content: str,
        reason: str,
    ) -> None:
        self.session.add(
            ScaffoldEvent(
                student_id=student_id,
                task_id=task_id,
                student_state=student_state,
                student_answer=student_answer,
                scaffold_type=scaffold_type,
                content=content,
                reason=reason,
            )
        )
        await self.session.commit()

    async def add_material(self, name: str, content: bytes) -> int:
        safe_name = Path(name).name
        material = Material(name=safe_name, stored_path="", status="queued", detail="")
        self.session.add(material)
        await self.session.flush()
        directory = Path(os.environ.get("UPLOAD_DIR", "data/uploads"))
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{material.id}-{safe_name}"
        path.write_bytes(content)
        material.stored_path = str(path)
        await self.session.commit()
        return material.id
