import csv
import hashlib
import json
import os
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from shared.student import VARIANT_NUMBER

class ValidationError(Exception):
    """Виникає, якщо пароль не відповідає мінімальним вимогам."""

PERSONAL_SALT = str(VARIANT_NUMBER).zfill(5)

def generate_hash(password: str, salt: str = "00000") -> str:
    if not password or not salt:
        raise ValueError("Password and salt must not be empty")

    min_length = 16
    if len(password) < min_length:
        raise ValidationError(f"Password must be at least {min_length} characters")

    combined = password + salt
    return hashlib.sha3_256(combined.encode()).hexdigest()

users_to_register = (
    ("alice_forensics", "SuperSecretPass123!"),
    ("bob_security", "AnotherStrongPass456!"),
    ("carol_admin", "YetAnotherPass789!"),
    ("dave_analyst", "PasswordNumberFour1!"),
    ("eve_auditor", "PasswordNumberFive2!"),
    ("frank_ops", "PasswordNumberSix345!"),
    ("grace_it", "PasswordNumberSeven6!"),
    ("henry_dev", "PasswordNumberEight7!"),
    ("ivy_lead", "PasswordNumberNine890!"),
    ("jack_admin", "PasswordNumberTen1234!"),
)

def create_user(username, password):
    hash_value = generate_hash(password, PERSONAL_SALT)
    return username, hash_value

def create_users(users_list):
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)

    csv_path = os.path.join(data_dir, "users.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        for username, password in users_list:
            row = create_user(username, password)
            writer.writerow(row)

def read_users_db():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    csv_path = os.path.join(data_dir, "users.csv")

    users_db = []
    with open(csv_path, "r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        for row in reader:
            users_db.append(tuple(row))
    return users_db

def print_users_db(users_db):
    print(f"{'Логін':<20} {'Хеш пароля':<70}")
    print("-" * 90)
    for username, hash_value in users_db:
        print(f"{username:<20} {hash_value:<70}")

def log_event(func):
    def wrapper(username, password, users_db):
        result = func(username, password, users_db)

        event = {
            "event": "login",
            "user": username,
            "result": "success" if result else "failure",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "args": [],
            "kwargs": {},
        }

        data_dir = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(data_dir, exist_ok=True)
        log_path = os.path.join(data_dir, "log.json")

        logs = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as file:
                logs = json.load(file)

        logs.append(event)

        with open(log_path, "w", encoding="utf-8") as file:
            json.dump(logs, file, ensure_ascii=False, indent=2)

        return result

    return wrapper

@log_event
def login(username: str, password: str, users_db) -> bool:
    if not username or not password:
        raise ValueError("Username and password must not be empty")

    for stored_username, stored_hash in users_db:
        if stored_username == username:
            return generate_hash(password, PERSONAL_SALT) == stored_hash

    return False

def main():
    try:
        create_users(users_to_register)
        print("Users created successfully")
        print()

        db = read_users_db()
        print_users_db(db)
        print()

        print(
            "Login test (correct password):",
            login("alice_forensics", "SuperSecretPass123!", db),
        )
        print(
            "Login test (wrong password):",
            login("alice_forensics", "WrongPassword!!!!", db),
        )

    except FileNotFoundError:
        print("Помилка: файл не знайдено")
    except PermissionError:
        print("Помилка: немає прав доступу до файлу")
    except ValidationError as e:
        print(f"Помилка валідації: {e}")
    except ValueError as e:
        print(f"Помилка значення: {e}")
    except IOError:
        print("Помилка вводу/виводу")

if __name__ == "__main__":
    main()