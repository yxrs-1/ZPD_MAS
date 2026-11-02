import os
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from scaffolding.classroom import (
    _fields_from_multipart,
    filenames_from_body,
    files_from_body,
    outside_lock,
    production_classroom,
    response_for,
)
from scaffolding.model_generator import post_json
from zpd_api.classroom_records import postgres_records
from zpd_api.db import sync_session_factory
from zpd_api.library import QueuedLibrary
from zpd_api.login_sessions import redis_sessions
from zpd_api.retrieval import delete_material, retrieve_named_passages
from zpd_api.scaffold_bridge import PassageScaffoldAgent, RecordedScaffoldDecision
from zpd_api.worker import enqueue_ingest

_room = None


def get_room():
    global _room
    if _room is None:
        records = postgres_records() if os.environ.get("DATABASE_URL") else None
        sessions = redis_sessions() if os.environ.get("REDIS_URL") else None
        room = production_classroom(post=post_json, records=records, sessions=sessions)
        room.student.decision = RecordedScaffoldDecision(room.student.decision)
        if os.environ.get("DATABASE_URL"):
            library = QueuedLibrary(
                session_factory=sync_session_factory(),
                enqueue=enqueue_ingest,
                delete_vectors=delete_material,
            )
            room.documents = library
            room.teacher.library = library

            def retrieve(query):
                return outside_lock(room._lock, lambda: retrieve_named_passages(query))

            room.teacher.retrieve = retrieve
            room.student.scaffold_agent = PassageScaffoldAgent(
                room.student.scaffold_agent,
                retrieve,
            )
        from zpd_api.scaffold_examples import load_examples
        room.example_loader = load_examples
        _room = room
    return _room


def mount_original_pages(app) -> None:
    static = Path(__file__).resolve().parents[3] / "src" / "scaffolding" / "static"
    app.mount("/static", StaticFiles(directory=str(static)), name="static")

    @app.api_route("/", methods=["GET", "POST"])
    @app.api_route("/{full_path:path}", methods=["GET", "POST"])
    async def original_pages(request: Request, full_path: str = ""):
        if request.url.path == "/api" or request.url.path.startswith("/api/"):
            return Response(status_code=404)
        return await _page(get_room(), request)


async def _page(room, request: Request) -> Response:
    import asyncio

    raw_bytes = await request.body()
    content_type = request.headers.get("content-type", "") or ""
    uploads = None
    filenames = None
    if "multipart/form-data" in content_type.lower():
        uploads = files_from_body(content_type, raw_bytes)
        filenames = filenames_from_body(content_type, raw_bytes)
        raw = _fields_from_multipart(content_type, raw_bytes)
    else:
        raw = raw_bytes.decode("utf-8")
    path = request.url.path
    if request.url.query:
        path = path + "?" + request.url.query
    result = await asyncio.to_thread(
        response_for,
        room,
        request.method,
        path,
        raw,
        time.monotonic(),
        request.headers.get("cookie", ""),
        uploads,
        filenames,
    )
    headers = {"content-type": result.content_type}
    filename = getattr(result, "filename", "")
    if filename:
        headers["content-disposition"] = "attachment; filename*=UTF-8''" + quote(filename, safe="")
    if result.set_cookie:
        headers["set-cookie"] = result.set_cookie
    return Response(content=result.body, status_code=result.status, headers=headers)
