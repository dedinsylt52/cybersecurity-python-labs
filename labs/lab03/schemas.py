"""Pydantic-моделі запитів і відповідей."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from labs.lab03.config import THRESHOLD, UNIT, VALUE_MAX, VALUE_MIN

Status = Literal["new", "in_progress", "done"]

# strict=True: JSON-число 1.5 (і навіть 1.0) або рядок "5" не приймаються.
EventCount = Annotated[
    int,
    Field(
        strict=True,
        ge=VALUE_MIN,
        le=VALUE_MAX,
        description=f"Кількість спрацювань за інтервал, {UNIT}",
        examples=[12],
    ),
]
PositiveId = Annotated[int, Field(strict=True, gt=0)]


class InputModel(BaseModel):
    """Спільні правила для тіла запиту."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")


class CategoryCreate(InputModel):
    name: str = Field(
        min_length=2,
        max_length=40,
        description="Джерело спрацювання",
        examples=["waf"],
    )


class CategoryRead(BaseModel):
    id: int
    name: str


class RecordCreate(InputModel):
    code: str = Field(min_length=3, max_length=40, examples=["V05-TEST"])
    title: str = Field(
        min_length=3, max_length=120, examples=["Підсумок спрацювань тест"]
    )
    category_id: PositiveId
    value: EventCount
    status: Status


class RecordReplace(RecordCreate):
    """Повна заміна змінюваних полів: усі поля обов'язкові."""


class RecordRead(BaseModel):
    id: int
    code: str
    title: str
    category_id: int
    category_name: str
    value: int
    status: Status

    @computed_field(description=f"value >= {THRESHOLD} {UNIT}")
    @property
    def exceeds_threshold(self) -> bool:
        return self.value >= THRESHOLD


class SeedCategory(CategoryCreate):
    id: PositiveId


class SeedData(InputModel):
    """Структура data/seed.json."""

    categories: list[SeedCategory] = Field(min_length=3, max_length=3)
    records: list[RecordCreate] = Field(min_length=8, max_length=8)


class StudentRead(BaseModel):
    student_name: str
    group_name: str
    variant_number: int


class StatusRead(BaseModel):
    status: Literal["ok"]


class ErrorRead(BaseModel):
    detail: str
