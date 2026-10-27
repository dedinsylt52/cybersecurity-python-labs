# ЛР №3. Облік спрацювань засобів захисту (варіант 5)

Web API на FastAPI + SQLite (без ORM) для збереження кількості спрацювань
засобів захисту за навчальні інтервали.

## Предметна область

| Поле          | Значення                                                         |
|---------------|------------------------------------------------------------------|
| `categories`  | Джерело спрацювання: `firewall`, `ids`, `antivirus`              |
| `code`        | Унікальний код запису, `V05-01` … `V05-08`                       |
| `title`       | `Підсумок спрацювань NN`                                          |
| `value`       | Кількість спрацювань за інтервал, ціле число ≥ 0, одиниця `events` |
| `status`      | Стан перевірки запису: `new`, `in_progress`, `done`              |
| Поріг         | **15 events**: у відповіді `exceeds_threshold = value >= 15`     |

Між таблицями `categories` і `records` зв'язок «один до багатьох»
(`records.category_id → categories.id`, `ON DELETE RESTRICT`).

## Структура

```
labs/lab03/
├── main.py          # FastAPI, lifespan, обробники помилок, /ping, /student
├── database.py      # з'єднання (PRAGMA foreign_keys = ON) і виконання schema.sql
├── schema.sql       # готова схема для варіантів 4–6
├── repository.py    # параметризовані SQL-запити та транзакції
├── schemas.py       # Pydantic-моделі
├── config.py        # одиниця, поріг, межі значень варіанта
├── seed.py          # заповнення бази з data/seed.json
├── check_api.py     # відтворювані перевірки завдання 3
├── routers/
│   ├── categories.py
│   └── records.py
└── data/
    ├── seed.json      # у Git
    └── lab3.sqlite3   # створюється програмою, не в Git
```

## Запуск (з кореня репозиторію)

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

python -m labs.lab03.database   # створити таблиці (необов'язково: це робить і seed)
python -m labs.lab03.seed       # 3 категорії + 8 записів; повторний запуск нічого не змінює
uvicorn labs.lab03.main:app --reload --host 127.0.0.1 --port 8000
```

Документація: <http://127.0.0.1:8000/docs>, схема: <http://127.0.0.1:8000/openapi.json>.

Автоматичні перевірки всіх сценаріїв завдання 3 на тимчасовій базі
(робоча база не змінюється):

```bash
python -m labs.lab03.check_api
```

У консолі Windows для коректної кирилиці: `set PYTHONUTF8=1`
(PowerShell: `$env:PYTHONUTF8=1`).

## Маршрути

| Метод і маршрут               | Успіх                  | Помилки        |
|-------------------------------|------------------------|----------------|
| `GET /ping`                   | 200 `{"status":"ok"}`  |                |
| `GET /student`                | 200                    |                |
| `GET /categories`             | 200                    |                |
| `POST /categories`            | 201                    | 409, 422       |
| `DELETE /categories/{id}`     | 204                    | 404, 409, 422  |
| `GET /records`                | 200                    | 422            |
| `GET /records/{id}`           | 200                    | 404, 422       |
| `POST /records`               | 201                    | 404, 409, 422  |
| `PUT /records/{id}`           | 200                    | 404, 409, 422  |
| `DELETE /records/{id}`        | 204                    | 404, 422       |
| `POST /records/bulk`          | 201                    | 404, 409, 422  |

Параметри `GET /records`: `category_id` (>0), `status`, `min_value` (≥0),
`q` (1–120 символів, буквальний підрядок у `title`), `limit` (1–100, типово 20),
`offset` (≥0). Фільтри поєднуються через `AND`, сортування за `id`.

## Приклади запитів (bash)

```bash
curl -i "http://127.0.0.1:8000/ping"
curl -i "http://127.0.0.1:8000/records?category_id=1&status=new&limit=5&offset=0"

curl -i -X POST "http://127.0.0.1:8000/records" \
  -H "Content-Type: application/json" \
  -d '{"code":"V05-TEST","title":"Навчальний підсумок","category_id":1,"value":18,"status":"new"}'

curl -i -X PUT "http://127.0.0.1:8000/records/9" \
  -H "Content-Type: application/json" \
  -d '{"code":"V05-TEST","title":"Навчальний підсумок","category_id":2,"value":40,"status":"done"}'

curl -i -X DELETE "http://127.0.0.1:8000/records/9"

# дробове значення лічильника -> 422
curl -i -X POST "http://127.0.0.1:8000/records" \
  -H "Content-Type: application/json" \
  -d '{"code":"V05-FR","title":"Дробове значення","category_id":1,"value":1.5,"status":"new"}'

# пакет із дублікатом V05-01 -> 409, V05-ROLLBACK не зберігається
curl -i -X POST "http://127.0.0.1:8000/records/bulk" \
  -H "Content-Type: application/json" \
  -d '[{"code":"V05-ROLLBACK","title":"Перший елемент","category_id":1,"value":4,"status":"new"},{"code":"V05-01","title":"Дублікат коду","category_id":2,"value":5,"status":"new"}]'
```

## Захист даних

* Усі значення передаються в SQL лише через параметри `?`; динамічні
  фрагменти `WHERE` беруться тільки з рядків у коді.
* `PRAGMA foreign_keys = ON` для кожного з'єднання; з'єднання відкривається
  й закривається в межах однієї операції.
* Операції зміни виконуються в `with connection` з `BEGIN IMMEDIATE`:
  перевірки (існування запису/категорії) і зміни атомарні; пакет зберігається
  повністю або не зберігається зовсім.
* `value` перевіряється як строгий `int` (1.5, `"5"` → 422) у межах 0 … 2⁶³−1.
* Помилки SQLite журналюються через `logging`, клієнт отримує 500 без SQL і шляхів.
