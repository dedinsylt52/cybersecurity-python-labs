"""Маршрути категорій (джерел спрацювань)."""

from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from labs.lab03 import repository
from labs.lab03.routers import CONFLICT, NOT_FOUND
from labs.lab03.schemas import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])

CategoryId = Annotated[int, Path(gt=0, description="Ідентифікатор категорії")]


@router.get("", summary="Список категорій", response_model=list[CategoryRead])
def list_categories() -> list[dict]:
    """Усі категорії за зростанням id."""
    return repository.list_categories()


@router.post(
    "",
    summary="Створити категорію",
    status_code=status.HTTP_201_CREATED,
    response_model=CategoryRead,
    responses=CONFLICT,
)
def create_category(payload: CategoryCreate) -> dict:
    """Додати нове джерело спрацювань; назва має бути унікальною."""
    return repository.create_category(payload.name)


@router.delete(
    "/{category_id}",
    summary="Видалити порожню категорію",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={**NOT_FOUND, **CONFLICT},
)
def delete_category(category_id: CategoryId) -> Response:
    """Видалити категорію без записів; непорожня категорія — 409."""
    repository.delete_category(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
