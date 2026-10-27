"""FastAPI-застосунок ЛР №3: облік спрацювань засобів захисту."""

import logging
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from labs.lab03.config import APP_DESCRIPTION, APP_TITLE
from labs.lab03.database import initialize_database
from labs.lab03.repository import ConflictError, NotFoundError
from labs.lab03.routers import categories, records
from labs.lab03.schemas import StatusRead, StudentRead
from shared import student

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Створити відсутні таблиці під час запуску; дані не змінюються."""
    initialize_database()
    yield


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan,
)
app.include_router(categories.router)
app.include_router(records.router)


@app.exception_handler(NotFoundError)
def handle_not_found(_request: Request, error: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(error)})


@app.exception_handler(ConflictError)
def handle_conflict(_request: Request, error: ConflictError) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(error)})


@app.exception_handler(sqlite3.Error)
def handle_database_error(_request: Request, _error: sqlite3.Error) -> JSONResponse:
    # Подробиці лише в журналі; клієнт не бачить SQL, шляхів і трасування.
    logger.exception("Помилка SQLite під час обробки запиту")
    return JSONResponse(
        status_code=500, content={"detail": "Внутрішня помилка сервера"}
    )


@app.get("/ping", summary="Перевірка доступності API", tags=["service"])
def ping() -> StatusRead:
    return StatusRead(status="ok")


@app.get("/student", summary="Дані студента", tags=["service"])
def get_student() -> StudentRead:
    return StudentRead(
        student_name=student.STUDENT_NAME,
        group_name=student.GROUP_NAME,
        variant_number=student.VARIANT_NUMBER,
    )
