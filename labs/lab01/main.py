import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER

import task1
import task2
import task3


def main():
    print(f"Лабораторна робота №1 — {STUDENT_NAME}, {GROUP_NAME}, варіант {VARIANT_NUMBER}")
    print()

    print("=" * 50)
    print("Завдання 1: Аналізатор надійності паролів")
    print("=" * 50)
    task1.main()
    print()

    print("=" * 50)
    print("Завдання 2: Система контролю доступу")
    print("=" * 50)
    task2.main()
    print()

    print("=" * 50)
    print("Завдання 3: Хешування, CSV, JSON-логування")
    print("=" * 50)
    task3.main()


if __name__ == "__main__":
    main()