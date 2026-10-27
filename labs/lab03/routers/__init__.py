"""Маршрути API ЛР №3."""

from labs.lab03.schemas import ErrorRead

NOT_FOUND = {404: {"model": ErrorRead, "description": "Об'єкт не знайдено"}}
CONFLICT = {409: {"model": ErrorRead, "description": "Конфлікт даних"}}
