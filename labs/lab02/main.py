"""Точка входу ЛР №2: команди demo та analyze."""

from __future__ import annotations

import argparse

from labs.lab02 import task1, task2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m labs.lab02.main")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="демонстрація Завдання 1")
    analyze = sub.add_parser("analyze", help="сканер сервісів (варіант 5)")
    task2.add_arguments(analyze)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "demo":
        task1.run_demo()
        return 0
    return task2.run_scan(args)


if __name__ == "__main__":
    raise SystemExit(main())
