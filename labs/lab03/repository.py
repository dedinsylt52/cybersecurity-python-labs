"""Шар доступу до даних: параметризовані SQL-запити без залежності від FastAPI."""

import sqlite3
from collections.abc import Iterable, Mapping
from contextlib import closing
from typing import Any

from labs.lab03.database import get_connection

Row = dict[str, Any]

RECORD_SELECT = """
    SELECT r.id, r.code, r.title, r.category_id, c.name AS category_name,
           r.value, r.status
    FROM records AS r
    JOIN categories AS c ON c.id = r.category_id
"""


class NotFoundError(LookupError):
    """Запис або категорія не існує."""


class ConflictError(Exception):
    """Порушено унікальність або категорія ще містить записи."""


def _connect() -> sqlite3.Connection:
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    return connection


def _begin(connection: sqlite3.Connection) -> None:
    """Почати транзакцію запису, щоб перевірки й зміни були атомарними."""
    connection.execute("BEGIN IMMEDIATE")


def _conflict(error: sqlite3.IntegrityError) -> ConflictError:
    message = str(error)
    if "records.code" in message:
        return ConflictError("Запис із таким code уже існує")
    if "categories.name" in message:
        return ConflictError("Категорія з такою назвою вже існує")
    return ConflictError("Дані порушують обмеження бази")


def _ensure_category(connection: sqlite3.Connection, category_id: int) -> None:
    row = connection.execute(
        "SELECT 1 FROM categories WHERE id = ?", (category_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Категорію {category_id} не знайдено")


def _fetch_record(connection: sqlite3.Connection, record_id: int) -> Row:
    row = connection.execute(RECORD_SELECT + " WHERE r.id = ?", (record_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Запис {record_id} не знайдено")
    return dict(row)


def _insert_record(connection: sqlite3.Connection, data: Mapping[str, Any]) -> int:
    cursor = connection.execute(
        "INSERT INTO records (code, title, category_id, value, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (
            data["code"],
            data["title"],
            data["category_id"],
            data["value"],
            data["status"],
        ),
    )
    return cursor.lastrowid


# --- Категорії ---


def list_categories() -> list[Row]:
    """Усі категорії за зростанням id."""
    with closing(_connect()) as connection:
        rows = connection.execute(
            "SELECT id, name FROM categories ORDER BY id"
        ).fetchall()
    return [dict(row) for row in rows]


def create_category(name: str) -> Row:
    """Додати категорію; id створює база."""
    with closing(_connect()) as connection:
        try:
            with connection:
                cursor = connection.execute(
                    "INSERT INTO categories (name) VALUES (?)", (name,)
                )
        except sqlite3.IntegrityError as error:
            raise _conflict(error) from error
    return {"id": cursor.lastrowid, "name": name}


def delete_category(category_id: int) -> None:
    """Видалити категорію, лише якщо вона не містить записів."""
    with closing(_connect()) as connection:
        try:
            with connection:
                _begin(connection)
                _ensure_category(connection, category_id)
                used = connection.execute(
                    "SELECT 1 FROM records WHERE category_id = ? LIMIT 1",
                    (category_id,),
                ).fetchone()
                if used is not None:
                    raise ConflictError("Категорія містить записи")
                connection.execute(
                    "DELETE FROM categories WHERE id = ?", (category_id,)
                )
        except sqlite3.IntegrityError as error:
            raise ConflictError("Категорія містить записи") from error


# --- Записи ---


def get_record(record_id: int) -> Row:
    """Один запис разом із назвою категорії."""
    with closing(_connect()) as connection:
        return _fetch_record(connection, record_id)


def list_records(
    *,
    category_id: int | None = None,
    status: str | None = None,
    min_value: int | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Row]:
    """Список записів із фільтрами (через AND) і поділом на сторінки."""
    # SQL-фрагменти беруться лише з коду, значення передаються параметрами.
    conditions: list[str] = []
    params: list[Any] = []
    if category_id is not None:
        conditions.append("r.category_id = ?")
        params.append(category_id)
    if status is not None:
        conditions.append("r.status = ?")
        params.append(status)
    if min_value is not None:
        conditions.append("r.value >= ?")
        params.append(min_value)
    if q is not None:
        conditions.append("instr(r.title, ?) > 0")
        params.append(q)

    sql = RECORD_SELECT
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY r.id LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with closing(_connect()) as connection:
        rows = connection.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def count_records() -> int:
    """Загальна кількість записів."""
    with closing(_connect()) as connection:
        return connection.execute("SELECT COUNT(*) FROM records").fetchone()[0]


def create_record(data: Mapping[str, Any]) -> Row:
    """Додати запис після перевірки категорії."""
    with closing(_connect()) as connection:
        try:
            with connection:
                _begin(connection)
                _ensure_category(connection, data["category_id"])
                record_id = _insert_record(connection, data)
        except sqlite3.IntegrityError as error:
            raise _conflict(error) from error
        return _fetch_record(connection, record_id)


def replace_record(record_id: int, data: Mapping[str, Any]) -> Row:
    """Повністю замінити змінювані поля запису; id не змінюється."""
    with closing(_connect()) as connection:
        try:
            with connection:
                _begin(connection)
                _fetch_record(connection, record_id)
                _ensure_category(connection, data["category_id"])
                connection.execute(
                    "UPDATE records SET code = ?, title = ?, category_id = ?, "
                    "value = ?, status = ? WHERE id = ?",
                    (
                        data["code"],
                        data["title"],
                        data["category_id"],
                        data["value"],
                        data["status"],
                        record_id,
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise _conflict(error) from error
        return _fetch_record(connection, record_id)


def delete_record(record_id: int) -> None:
    """Видалити запис; NotFoundError, якщо його немає."""
    with closing(_connect()) as connection, connection:
        _begin(connection)
        cursor = connection.execute("DELETE FROM records WHERE id = ?", (record_id,))
        if cursor.rowcount == 0:
            raise NotFoundError(f"Запис {record_id} не знайдено")


def create_records_bulk(items: Iterable[Mapping[str, Any]]) -> list[Row]:
    """Додати пакет записів в одній транзакції: усі або жодного."""
    items = list(items)
    with closing(_connect()) as connection:
        try:
            with connection:
                _begin(connection)
                for category_id in sorted({item["category_id"] for item in items}):
                    _ensure_category(connection, category_id)
                ids = [_insert_record(connection, item) for item in items]
        except sqlite3.IntegrityError as error:
            raise _conflict(error) from error
        return [_fetch_record(connection, record_id) for record_id in ids]


# --- Початкове заповнення ---


def seed_database(
    categories: Iterable[Mapping[str, Any]],
    records: Iterable[Mapping[str, Any]],
) -> bool:
    """Заповнити порожню базу в одній транзакції.

    Повертає False без змін, якщо база вже містить дані.
    """
    with closing(_connect()) as connection, connection:
        _begin(connection)
        has_data = connection.execute(
            "SELECT EXISTS (SELECT 1 FROM categories) OR EXISTS (SELECT 1 FROM records)"
        ).fetchone()[0]
        if has_data:
            return False
        connection.executemany(
            "INSERT INTO categories (id, name) VALUES (?, ?)",
            [(item["id"], item["name"]) for item in categories],
        )
        for record in records:
            _insert_record(connection, record)
    return True
