"""Маршрути записів про кількість спрацювань."""

from typing import Annotated

from fastapi import APIRouter, Body, Path, Query, Response, status

from labs.lab03 import repository
from labs.lab03.config import BULK_MAX_ITEMS, UNIT, VALUE_MAX, VALUE_MIN
from labs.lab03.routers import CONFLICT, NOT_FOUND
from labs.lab03.schemas import RecordCreate, RecordRead, RecordReplace, Status

router = APIRouter(prefix="/records", tags=["records"])

RecordId = Annotated[int, Path(gt=0, description="Ідентифікатор запису")]


@router.get("", summary="Список записів із фільтрами", response_model=list[RecordRead])
def list_records(
    category_id: Annotated[
        int | None, Query(gt=0, description="Лише записи цієї категорії")
    ] = None,
    status: Annotated[Status | None, Query(description="Стан перевірки")] = None,
    min_value: Annotated[
        int | None,
        Query(
            ge=VALUE_MIN,
            le=VALUE_MAX,
            description=f"Мінімальна кількість спрацювань, {UNIT}",
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=120,
            description="Буквальний підрядок у title (з урахуванням регістру)",
        ),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Розмір сторінки")] = 20,
    offset: Annotated[int, Query(ge=0, description="Скільки записів пропустити")] = 0,
) -> list[dict]:
    """Фільтри поєднуються через AND, результат упорядковано за id."""
    return repository.list_records(
        category_id=category_id,
        status=status,
        min_value=min_value,
        q=q,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/bulk",
    summary="Пакетне створення записів (атомарно)",
    status_code=status.HTTP_201_CREATED,
    response_model=list[RecordRead],
    responses={**NOT_FOUND, **CONFLICT},
)
def create_records_bulk(
    payload: Annotated[
        list[RecordCreate],
        Body(min_length=1, max_length=BULK_MAX_ITEMS),
    ],
) -> list[dict]:
    """Зберегти всі записи пакета в одній транзакції або жодного."""
    return repository.create_records_bulk(item.model_dump() for item in payload)


@router.get(
    "/{record_id}",
    summary="Отримати запис",
    response_model=RecordRead,
    responses=NOT_FOUND,
)
def get_record(record_id: RecordId) -> dict:
    """Один запис разом із назвою категорії."""
    return repository.get_record(record_id)


@router.post(
    "",
    summary="Створити запис",
    status_code=status.HTTP_201_CREATED,
    response_model=RecordRead,
    responses={**NOT_FOUND, **CONFLICT},
)
def create_record(payload: RecordCreate) -> dict:
    """Додати запис; id створює база."""
    return repository.create_record(payload.model_dump())


@router.put(
    "/{record_id}",
    summary="Замінити запис",
    response_model=RecordRead,
    responses={**NOT_FOUND, **CONFLICT},
)
def replace_record(record_id: RecordId, payload: RecordReplace) -> dict:
    """Повністю замінити всі змінювані поля запису."""
    return repository.replace_record(record_id, payload.model_dump())


@router.delete(
    "/{record_id}",
    summary="Видалити запис",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=NOT_FOUND,
)
def delete_record(record_id: RecordId) -> Response:
    """Видалити запис за id."""
    repository.delete_record(record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
