"""Завдання 2, варіант 5: сканер доступності мережевих сервісів."""

from __future__ import annotations

import argparse
import csv
import ipaddress
import json
import logging
import re
import socket
import sys
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger("lab02.scanner")

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_TARGETS = DATA_DIR / "data_v05" / "targets.json"
DEFAULT_OUT_CSV = DATA_DIR / "scan_results.csv"

IPV4_SHAPE_RE = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")
_LABEL = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
DOMAIN_RE = re.compile(rf"{_LABEL}(?:\.{_LABEL})*")

SERVICES = {
    21: "FTP",
    22: "SSH",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    443: "HTTPS",
    3389: "RDP",
    5432: "PostgreSQL",
    8080: "HTTP-Alt",
}


class Status(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    INVALID = "INVALID"


@dataclass
class ScanResult:
    host: str
    port: int | str
    service: str
    status: Status
    response_time_ms: float | None = None
    notes: str = ""


def validate_host(host: str) -> bool:
    """IP-адреса (перевірка через ipaddress) або доменне ім'я (через re)."""
    if not host or len(host) > 253:
        return False
    if ":" in host:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return False
        return True
    if IPV4_SHAPE_RE.fullmatch(host):
        try:
            ipaddress.IPv4Address(host)
        except ValueError:
            return False
        return True
    return DOMAIN_RE.fullmatch(host) is not None


def validate_port(value: object) -> int:
    if isinstance(value, bool):
        raise TypeError("порт не може бути булевим значенням")
    try:
        port = int(value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        raise ValueError(f"порт не є числом: {value!r}") from None
    if not 1 <= port <= 65535:
        raise ValueError(f"порт поза діапазоном 1-65535: {port}")
    return port


def load_targets(path: Path) -> list[dict]:
    """Читає цілі з JSON (список або {"targets": [...]}) чи CSV (host,port)."""
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("targets", [])
    if not isinstance(data, list):
        raise TypeError("JSON має містити список цілей")
    return [item for item in data if isinstance(item, dict)]


def check_connection(
    host: str, port: int, timeout: float
) -> tuple[Status, float | None, str]:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except TimeoutError:
        return Status.OFFLINE, None, "Connection timed out"
    except socket.gaierror as exc:
        return Status.OFFLINE, None, f"DNS error: {exc.strerror}"
    except ConnectionRefusedError:
        return Status.OFFLINE, None, "Connection refused"
    except OSError as exc:
        return Status.OFFLINE, None, f"Network error: {exc.strerror or exc}"
    elapsed = (time.perf_counter() - start) * 1000
    return Status.ONLINE, round(elapsed, 1), "OK"


def scan_target(raw: dict, timeout: float) -> ScanResult:
    host = str(raw.get("host", "")).strip()
    if not validate_host(host):
        logger.warning("Invalid host skipped: %r", host)
        return ScanResult(
            host, raw.get("port", ""), "-", Status.INVALID, None, "Invalid host"
        )
    try:
        port = validate_port(raw.get("port"))
    except (TypeError, ValueError) as exc:
        logger.warning("Invalid port for %s: %s", host, exc)
        return ScanResult(
            host, raw.get("port", ""), "-", Status.INVALID, None, "Invalid port"
        )
    service = SERVICES.get(port, "Unknown")
    logger.debug("Checking %s:%d (timeout=%.1fs)", host, port, timeout)
    status, rt, notes = check_connection(host, port, timeout)
    if status is Status.ONLINE:
        logger.info("%s:%d is ONLINE (%.1f ms)", host, port, rt)
    else:
        logger.warning("%s:%d is OFFLINE: %s", host, port, notes)
    return ScanResult(host, port, service, status, rt, notes)


def print_table(results: list[ScanResult]) -> None:
    header = (
        f"{'Target Host':<26}{'Port':<7}{'Service':<12}"
        f"{'Status':<9}{'Response Time':<15}Notes"
    )
    print(header)
    print("-" * 90)
    for r in results:
        if r.response_time_ms is not None:
            rt = f"{r.response_time_ms} ms"
        elif r.status is Status.OFFLINE and "timed out" in r.notes:
            rt = "TIMEOUT"
        else:
            rt = "-"
        print(
            f"{r.host:<26}{r.port!s:<7}{r.service:<12}"
            f"{r.status.value:<9}{rt:<15}{r.notes}"
        )


def print_statistics(results: list[ScanResult]) -> None:
    online = sum(r.status is Status.ONLINE for r in results)
    offline = sum(r.status is Status.OFFLINE for r in results)
    invalid = sum(r.status is Status.INVALID for r in results)
    scanned = online + offline

    def pct(n: int) -> str:
        return f"{n / scanned * 100:.1f}%" if scanned else "0.0%"

    print("\n=== Scan Statistics ===")
    print(f"Total Scanned : {scanned}")
    print(f"Online        : {online} ({pct(online)})")
    print(f"Offline       : {offline} ({pct(offline)})")
    print(f"Invalid (skipped): {invalid}")


def save_csv(results: list[ScanResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["host", "port", "service", "status", "response_time_ms", "notes"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for r in results:
            row = asdict(r)
            row["status"] = r.status.value
            writer.writerow(row)


def setup_logging(verbose: bool, log_file: Path | None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    handlers: list[logging.Handler] = [console]
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        handlers.append(fh)
    logging.basicConfig(level=level, handlers=handlers, force=True)


def positive_float(value: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("timeout має бути числом") from None
    if number <= 0:
        raise argparse.ArgumentTypeError("timeout має бути > 0")
    return number


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--targets",
        type=Path,
        default=DEFAULT_TARGETS,
        help="шлях до JSON/CSV зі списком цілей",
    )
    parser.add_argument(
        "--timeout",
        type=positive_float,
        default=2.0,
        help="таймаут з'єднання, секунди (за замовч. 2.0)",
    )
    parser.add_argument(
        "--out-csv",
        type=Path,
        default=DEFAULT_OUT_CSV,
        help="файл CSV із результатами",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="детальне логування (DEBUG)"
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=None,
        help="додатково писати аудиторський лог у файл",
    )


def run_scan(args: argparse.Namespace) -> int:
    setup_logging(args.verbose, args.log_file)
    logger.info(
        "Starting service availability scan from target list %s...", args.targets
    )
    try:
        targets = load_targets(args.targets)
    except FileNotFoundError:
        logger.error("Targets file not found: %s", args.targets)
        return 2
    except (json.JSONDecodeError, TypeError, ValueError, OSError) as exc:
        logger.error("Cannot read targets file: %s", exc)
        return 2

    results = [scan_target(t, args.timeout) for t in targets]
    print()
    print_table(results)
    print_statistics(results)
    try:
        save_csv(results, args.out_csv)
    except OSError as exc:
        logger.error("Cannot write report: %s", exc)
        return 3
    logger.info("Detailed scan report saved to %s", args.out_csv)
    return 0
