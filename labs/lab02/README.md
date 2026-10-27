# Лабораторна робота №2 — Варіант 5

**Тема:** Сканер доступності мережевих сервісів та перевірка портів.

## Встановлення
```bash
pip install -r requirements.txt   # з кореня репозиторію (містить ruff)
```
Додайте до `.gitignore`: `.venv/` та `__pycache__/`.

## Структура
```
labs/lab02/
├── main.py      # команди demo та analyze
├── task1.py     # User, Admin, Session, AuditLog, UserAccount
├── task2.py     # сканер сервісів (варіант 5)
└── data/data_v05/targets.json   # вхідний файл
```

## Вхідний файл
`data/data_v05/targets.json` — масив об'єктів `{"host": ..., "port": ...}`
(11 цілей, серед них навмисно некоректні: `bad host name`, `999.10.10.10`, порт `70000`).
Також підтримується CSV із колонками `host,port`.

## Запуск
```bash
python -m labs.lab02.main demo
python -m labs.lab02.main analyze
python -m labs.lab02.main analyze --targets labs/lab02/data/data_v05/targets.json \
    --timeout 2 --out-csv labs/lab02/data/scan_results.csv --verbose
```

## Параметри `analyze`
| Параметр | Опис |
|---|---|
| `--targets` | шлях до JSON/CSV зі списком цілей |
| `--timeout` | таймаут з'єднання в секундах (> 0, за замовч. 2.0) |
| `--out-csv` | файл CSV із результатами |
| `--verbose` | рівень логування DEBUG |
| `--log-file` | додатково писати аудиторський лог у файл |

## Поведінка при помилках
- Файл не знайдено / некоректний JSON — `[ERROR]`, код виходу 2.
- Помилка запису звіту — код виходу 3.
- Некоректний host або порт — ціль позначається `INVALID`, пропускається, у лог іде `[WARNING]`.
- Таймаут, відмова з'єднання, помилка DNS — статус `OFFLINE` з поясненням у `Notes`.

## Перевірка коду
```bash
ruff check .
ruff format --check .
```
