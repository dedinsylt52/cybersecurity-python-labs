"""Відтворювані перевірки завдання 3 на тимчасовій копії бази.

Запуск: python -m labs.lab03.check_api
Робоча база data/lab3.sqlite3 не змінюється.
"""

import json
import sys
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from labs.lab03 import database, repository, seed
from labs.lab03.main import app

failures: list[str] = []


def show(client: TestClient, method: str, url: str, expected: int, **kwargs) -> dict:
    """Виконати запит, надрукувати його та перевірити HTTP-код."""
    response = client.request(method, url, **kwargs)
    body = kwargs.get("json")
    mark = "OK " if response.status_code == expected else "ERR"
    print(f"[{mark}] {method} {url}")
    if body is not None:
        print(f"      body: {json.dumps(body, ensure_ascii=False)}")
    text = response.text if response.content else "<порожнє тіло>"
    print(f"      -> {response.status_code}: {text[:300]}")
    if response.status_code != expected:
        failures.append(f"{method} {url}: {response.status_code} != {expected}")
    return response.json() if response.content else {}


def check(condition: bool, message: str) -> None:
    print(f"[{'OK ' if condition else 'ERR'}] {message}")
    if not condition:
        failures.append(message)


def all_codes() -> set[str]:
    return {row["code"] for row in repository.list_records(limit=10**6)}


def record(code: str, category_id: int = 1, value: int = 12, **extra) -> dict:
    return {
        "code": code,
        "title": f"Підсумок спрацювань {code}",
        "category_id": category_id,
        "value": value,
        "status": "new",
        **extra,
    }


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        database.DATABASE_PATH = Path(tmp) / "lab3.sqlite3"
        run_scenarios()
    print("\nПідсумок:", "усі перевірки пройдено" if not failures else failures)
    return 1 if failures else 0


def run_scenarios() -> None:
    print("== 1. Початкове заповнення та повторний запуск seed")
    seed.run()
    check(repository.count_records() == 8, "8 записів після першого запуску")
    seed.run()
    check(repository.count_records() == 8, "повторний запуск не додав дублікатів")
    check(len(repository.list_categories()) == 3, "3 категорії")

    with TestClient(app) as client:
        print("\n== 2. Службові маршрути")
        show(client, "GET", "/ping", 200)
        show(client, "GET", "/student", 200)
        show(client, "GET", "/categories", 200)

        print("\n== 3. CRUD одного запису")
        created = show(client, "POST", "/records", 201, json=record("V05-TEST"))
        rid = created["id"]
        show(client, "GET", f"/records/{rid}", 200)
        replaced = record("V05-TEST", category_id=2, value=40, status="done")
        show(client, "PUT", f"/records/{rid}", 200, json=replaced)
        show(client, "DELETE", f"/records/{rid}", 204)
        show(client, "GET", f"/records/{rid}", 404)

        print("\n== 4. Фільтри, два фільтри, limit/offset")
        rows = show(client, "GET", "/records?category_id=1", 200)
        check([r["code"] for r in rows] == ["V05-01", "V05-04", "V05-07"], "category=1")
        rows = show(client, "GET", "/records?status=new&min_value=15", 200)
        check([r["code"] for r in rows] == ["V05-04"], "status=new AND value>=15")
        page1 = show(client, "GET", "/records?limit=3&offset=0", 200)
        page2 = show(client, "GET", "/records?limit=3&offset=3", 200)
        ids = [r["id"] for r in page1 + page2]
        check(ids == sorted(ids) and len(set(ids)) == 6, "сторінки стабільні")
        rows = show(client, "GET", "/records?q=спрацювань 0", 200)
        check(len(rows) == 8, "пошук підрядка q")
        show(client, "GET", "/records?category_id=99", 200)

        print("\n== 5. Невалідні дані -> 422, база не змінюється")
        before = repository.count_records()
        show(client, "POST", "/records", 422, json=record("V05-NEG", value=-1))
        show(client, "POST", "/records", 422, json=record("V05-EMP", title="   "))
        show(client, "POST", "/records", 422, json=record("V05-ST", status="closed"))
        show(client, "GET", "/records?limit=0", 422)
        show(client, "POST", "/records", 422, json=record("V05-ID", id=100))
        check(repository.count_records() == before, "кількість записів не змінилась")

        print("\n== 6. Лічильник: дробове значення та переповнення -> 422")
        show(client, "POST", "/records", 422, json=record("V05-FR", value=1.5))
        show(client, "POST", "/records", 422, json=record("V05-STR", value="5"))
        show(client, "POST", "/records", 422, json=record("V05-BIG", value=2**63))
        check(repository.count_records() == before, "кількість записів не змінилась")

        print("\n== 7. Неіснуючі record_id та category_id -> 404")
        show(client, "GET", "/records/9999", 404)
        show(client, "PUT", "/records/9999", 404, json=record("V05-X"))
        show(client, "DELETE", "/records/9999", 404)
        show(client, "POST", "/records", 404, json=record("V05-NC", category_id=99))
        show(client, "GET", "/records/0", 422)

        print("\n== 8. Дублікати -> 409")
        show(client, "POST", "/records", 409, json=record("V05-01"))
        show(client, "POST", "/categories", 409, json={"name": "ids"})
        check(repository.get_record(1)["value"] == 10, "запис V05-01 не змінився")

        print("\n== 9. Видалення категорій")
        show(client, "DELETE", "/categories/1", 409)
        new_cat = show(client, "POST", "/categories", 201, json={"name": "waf"})
        show(client, "DELETE", f"/categories/{new_cat['id']}", 204)
        show(client, "DELETE", "/categories/99", 404)
        check(
            len(repository.list_records(category_id=1)) == 3,
            "записи категорії 1 на місці",
        )

        print("\n== 10. Коректний пакет із двох записів -> 201")
        batch = [record("V05-B1"), record("V05-B2", category_id=3, value=50)]
        show(client, "POST", "/records/bulk", 201, json=batch)
        check({"V05-B1", "V05-B2"} <= all_codes(), "обидва записи збережено")

        print("\n== 11. Пакет із дублікатом code з бази -> 409, відкат")
        before = repository.count_records()
        batch = [record("V05-ROLLBACK"), record("V05-01", category_id=2)]
        show(client, "POST", "/records/bulk", 409, json=batch)
        after = repository.count_records()
        print(f"      записів до: {before}, після: {after}")
        check(after == before, "кількість не змінилась")
        check("V05-ROLLBACK" not in all_codes(), "V05-ROLLBACK відсутній")

        print("\n== 11a. Дублікат усередині пакета -> 409")
        batch = [record("V05-DUP"), record("V05-DUP")]
        show(client, "POST", "/records/bulk", 409, json=batch)
        check("V05-DUP" not in all_codes(), "V05-DUP відсутній")

        print("\n== 12. Пакет із неіснуючою категорією -> 404, відкат")
        before = repository.count_records()
        batch = [record("V05-ROLLBACK2"), record("V05-NOCAT", category_id=99)]
        show(client, "POST", "/records/bulk", 404, json=batch)
        after = repository.count_records()
        print(f"      записів до: {before}, після: {after}")
        check(after == before, "кількість не змінилась")
        check("V05-ROLLBACK2" not in all_codes(), "V05-ROLLBACK2 відсутній")

        print("\n== 12a. Межі пакета: порожній масив і 101 елемент -> 422")
        show(client, "POST", "/records/bulk", 422, json=[])
        big = [record(f"V05-L{i:03d}") for i in range(101)]
        response = client.post("/records/bulk", json=big)
        check(response.status_code == 422, f"101 елемент -> {response.status_code}")

        print("\n== 13. SQL-ін'єкція в q обробляється як дані")
        before = repository.count_records()
        rows = show(client, "GET", "/records", 200, params={"q": "' OR 1=1 --"})
        check(rows == [], "порожній результат")
        check(repository.count_records() == before, "записи не змінились")

        print("\n== 14. Запис доступний після перезапуску")
        created = show(client, "POST", "/records", 201, json=record("V05-PERSIST"))

    with TestClient(app) as client:
        show(client, "GET", f"/records/{created['id']}", 200)


if __name__ == "__main__":
    sys.exit(main())
