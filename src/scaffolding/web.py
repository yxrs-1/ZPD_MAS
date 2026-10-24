import time
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from scaffolding.classroom import (
    _fields_from_multipart,
    filenames_from_body,
    files_from_body,
    response_for,
)


def create_app(room) -> FastAPI:
    app = FastAPI()
    static = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static)), name="static")

    @app.api_route("/", methods=["GET", "POST"])
    @app.api_route("/{full_path:path}", methods=["GET", "POST"])
    async def pages(request: Request, full_path: str = ""):
        return await _page(room, request)

    return app


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
