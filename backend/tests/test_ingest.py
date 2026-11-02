from zpd_api.ingest import ingest_material


def test_ingest_stores_chunks_and_marks_the_material_ready(tmp_path):
    path = tmp_path / "lesson.docx"
    path.write_bytes(b"file")

    class Material:
        name = "lesson.docx"
        stored_path = str(path)
        status = "queued"
        detail = ""

    class Session:
        def get(self, _model, _material_id):
            return material

        def commit(self):
            return None

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    material = Material()
    written = {}

    def reader(name, content):
        assert name == "lesson.docx"
        assert content == b"file"
        return ("第一段", "第二段")

    def writer(material_id, name, chunks):
        written["id"] = material_id
        written["name"] = name
        written["chunks"] = chunks

    ingest_material(4, reader=reader, writer=writer, open_session=lambda: Session())

    assert written == {"id": 4, "name": "lesson.docx", "chunks": ("第一段", "第二段")}
    assert material.status == "ready"
    assert material.detail == ""
