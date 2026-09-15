import sys
import random
import os
import string


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from shared.student import STUDENT_NAME, GROUP_NAME, VARIANT_NUMBER

passwords = [
    "DataS3cur3!",
    "123",
    "Crypt0@Analysis",
    "test123",
    "Quantum#2023",
    "access",
    "Secur1ty@Pro",
    "password1",
    "Adv@nced123",
    "guest123",
]

criteria = {
    "min_length": 12,
    "require_digits": True,
    "require_upper": True,
    "require_special": True,
}

forbidden_passwords = {"123", "test123", "access", "password1", "guest123", "admin"}

random_indices = random.sample(range(len(passwords)), k=3)
for i in random_indices:
    passwords.append(passwords[i])


def has_digit(password: str) -> bool:
    return any(ch.isdigit() for ch in password)


def has_upper(password: str) -> bool:
    return any(ch.isupper() for ch in password)


def has_lower(password: str) -> bool:
    return any(ch.islower() for ch in password)


def has_special(password: str) -> bool:
    return any(ch in string.punctuation for ch in password)


def evaluate_password(password, criteria, forbidden_passwords, all_passwords):
    min_length = criteria["min_length"]

    if password in forbidden_passwords or len(password) < min_length:
        return "Заборонений"

    checks = [
        has_digit(password),
        has_upper(password),
        has_special(password),
        has_lower(password),
    ]
    passed_count = sum(checks)

    if (
        all(checks)
        and len(password) >= min_length + 4
        and all_passwords.count(password) == 1
    ):
        return "Дуже сильний"
    if all(checks):
        return "Сильний"
    if passed_count > 1:
        return "Середній"
    return "Слабкий"


def main():
    print(f"Студент: {STUDENT_NAME}, Група: {GROUP_NAME}, Варіант: {VARIANT_NUMBER}")
    print()
    print(f"{'Пароль':<20} {'Статус':<20}")
    print("-" * 40)

    for password in passwords:
        status = evaluate_password(password, criteria, forbidden_passwords, passwords)
        print(f"{password:<20} {status:<20}")


if __name__ == "__main__":
    main()
