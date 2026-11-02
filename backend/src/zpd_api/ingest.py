from pathlib import Path

from zpd_api.bootstrap import install_src_path
from zpd_api.db import sync_session_factory
from zpd_api.models import Material
from zpd_api.retrieval import index_chunks

install_src_path()


def ingest_material(material_id: int, *, reader=None, writer=None, open_session=None) -> None:
    from scaffolding.documents import read_document

    read = reader or read_document
    write = writer or index_chunks
    sessions = open_session or sync_session_factory()
    with sessions() as session:
        material = session.get(Material, material_id)
        content = Path(material.stored_path).read_bytes()
        try:
            chunks = read(material.name, content)
            write(material_id, material.name, chunks)
        except Exception as error:
            material.status = "failed"
            material.detail = getattr(error, "message", str(error))
            session.commit()
            return
        material.status = "ready"
        material.detail = ""
        session.commit()
