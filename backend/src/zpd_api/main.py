import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from zpd_api.bootstrap import install_src_path

install_src_path()

from zpd_api.db import init_db
from zpd_api.classroom_api import router as classroom_router
from zpd_api.pages import mount_original_pages
from zpd_api.routes import router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if os.environ.get("ZPD_SKIP_DB") != "1":
        await init_db()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")
app.include_router(classroom_router, prefix="/api")
mount_original_pages(app)
