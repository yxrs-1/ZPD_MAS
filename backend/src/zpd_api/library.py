import os
from pathlib import Path

from scaffolding.documents import DocumentError, StoredDocument
from zpd_api.models import Material


class QueuedLibrary:
    def __init__(self, session_factory, enqueue, delete_vectors, upload_dir=None) -> None:
        self._sessions = session_factory
        self._enqueue = enqueue
        self._delete_vectors = delete_vectors
        self._upload_dir = Path(upload_dir or os.environ.get("UPLOAD_DIR", "data/uploads"))

    @property
    def _next(self) -> int:
        with self._sessions() as session:
            current = session.query(Material.id).order_by(Material.id.desc()).first()
        return 1 if current is None else current[0] + 1

    def documents(self) -> tuple[StoredDocument, ...]:
        with self._sessions() as session:
            rows = session.query(Material).order_by(Material.id).all()
            return tuple(
                StoredDocument(str(row.id), row.name, (), row.status, row.detail)
                for row in rows
            )

    def add(self, name: str, content: bytes) -> StoredDocument:
        safe_name = Path(name).name
        extension = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
        if extension not in ("docx", "pdf"):
            raise DocumentError("只接受 docx 或 pdf")
        self._upload_dir.mkdir(parents=True, exist_ok=True)
        with self._sessions() as session:
            material = Material(name=safe_name, stored_path="", status="queued", detail="")
            session.add(material)
            session.flush()
            path = self._upload_dir / f"{material.id}-{safe_name}"
            path.write_bytes(content)
            material.stored_path = str(path)
            session.commit()
            material_id = material.id
        self._enqueue(material_id)
        return StoredDocument(str(material_id), safe_name, (), "queued")

    def delete(self, doc_id: str) -> None:
        if not str(doc_id).isdigit():
            raise DocumentError("文档不存在")
        with self._sessions() as session:
            material = session.get(Material, int(doc_id))
            if material is None:
                raise DocumentError("文档不存在")
            path = Path(material.stored_path)
            material_id = material.id
            self._delete_vectors(material_id)
            if path.is_file():
                path.unlink()
            session.delete(material)
            session.commit()

    def load(self, documents, next_id: int) -> None:
        return None
