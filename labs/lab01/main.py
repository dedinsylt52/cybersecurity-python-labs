"""Головний файл для демонстрації роботи Лабораторної роботи №1."""

import os
import sys

# Дозволяє імпортувати shared/ з кореня репозиторію
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from shared.student import GROUP_NAME, STUDENT_NAME, VARIANT_NUMBER


def main() -> None:
    """Точка входу в програму."""
    print(f"Студент: {STUDENT_NAME}")
    print(f"Група: {GROUP_NAME}")
    print(f"Варіант: {VARIANT_NUMBER}")

    # TODO: викликати функції з task1.py, task2.py, task3.py


if __name__ == "__main__":
    main()
