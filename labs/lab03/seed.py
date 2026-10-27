"""Початкове заповнення бази з data/seed.json."""

import json
import logging
import sqlite3
import sys
from pathlib import Path

from pydantic import ValidationError

from labs.lab03 import repository
from labs.lab03.database import BASE_DIR, initialize_database
from labs.lab03.schemas import SeedData

SEED_PATH = BASE_DIR / "data" / "seed.json"

logger = logging.getLogger(__name__)


def load_seed(path: Path = SEED_PATH) -> SeedData:
    """Прочитати JSON і перевірити його структуру та значення."""
    with path.open(encoding="utf-8") as file:
        raw = json.load(file)
    data = SeedData.model_validate(raw)

    category_ids = [category.id for category in data.categories]
    if len(set(category_ids)) != len(category_ids):
        raise ValueError("id категорій мають бути унікальними")
    names = [category.name for category in data.categories]
    if len(set(names)) != len(names):
        raise ValueError("Назви категорій мають бути унікальними")
    codes = [record.code for record in data.records]
    if len(set(codes)) != len(codes):
        raise ValueError("code записів мають бути унікальними")
    unknown = {r.category_id for r in data.records} - set(category_ids)
    if unknown:
        raise ValueError(f"Записи посилаються на відсутні категорії: {unknown}")
    return data


def run(path: Path = SEED_PATH) -> int:
    """Створити таблиці та заповнити порожню базу. Повертає код завершення."""
    try:
        data = load_seed(path)
    except FileNotFoundError:
        print(f"Файл початкових даних не знайдено: {path.name}")
        return 1
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        print(f"Початкові дані некоректні, базу не змінено:\n{error}")
        return 1

    try:
        initialize_database()
        seeded = repository.seed_database(
            [category.model_dump() for category in data.categories],
            [record.model_dump() for record in data.records],
        )
    except sqlite3.IntegrityError:
        logger.exception("Порушення обмежень під час заповнення")
        print("Дані порушують обмеження бази. Усі зміни скасовано.")
        return 1
    except sqlite3.Error:
        logger.exception("Помилка SQLite під час заповнення")
        print("Помилка роботи з базою даних. Усі зміни скасовано.")
        return 1

    if not seeded:
        print("База вже містить дані: повторне заповнення пропущено, змін немає.")
        return 0
    print(
        f"Базу заповнено: категорій — {len(data.categories)}, "
        f"записів — {len(data.records)}."
    )
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    sys.exit(run())
