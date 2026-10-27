"""Завдання 1: модель користувача, сеансу, аудиту та облікового запису."""

from __future__ import annotations

import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

PBKDF2_ITERATIONS = 310_000
SALT_SIZE = 16
SESSION_TIMEOUT_SEC = 900

# Локальна частина: літера + 2..63 символи [A-Za-z0-9_] (разом 3-64),
# домен містить принаймні одну крапку.
EMAIL_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,63}@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")


def utc_now() -> datetime:
    """Поточний час UTC з часовим поясом."""
    return datetime.now(timezone.utc)


class User:
    """Користувач із безпечним зберіганням пароля."""

    def __init__(
        self,
        username: str,
        email: str,
        role: str = "user",
        active: bool = True,
        password: str | None = None,
    ) -> None:
        self.username = username
        self.email = email  # проходить через setter із валідацією
        self.role = role
        self.active = active
        self.__password_hash: bytes = b""
        self.__password_salt: bytes = b""
        if password is not None:
            self.set_password(password)

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        if not isinstance(value, str) or not EMAIL_RE.fullmatch(value):
            raise ValueError(f"Некоректний email: {value!r}")
        self._email = value

    @staticmethod
    def _derive(password: str, salt: bytes) -> bytes:
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
        )

    def set_password(self, password: str) -> None:
        if not isinstance(password, str) or not password:
            raise ValueError("Пароль має бути непорожнім рядком")
        self.__password_salt = os.urandom(SALT_SIZE)
        self.__password_hash = self._derive(password, self.__password_salt)

    def check_password(self, password: str) -> bool:
        if not self.__password_hash or not isinstance(password, str):
            return False
        candidate = self._derive(password, self.__password_salt)
        return hmac.compare_digest(candidate, self.__password_hash)

    def deactivate(self) -> None:
        self.active = False

    def __str__(self) -> str:
        state = "active" if self.active else "inactive"
        return (
            f"User(username={self.username}, email={self.email}, "
            f"role={self.role}, {state})"
        )


class Admin(User):
    """Адміністратор: користувач із набором дозволів (наслідування)."""

    def __init__(
        self,
        username: str,
        email: str,
        role: str = "admin",
        active: bool = True,
        password: str | None = None,
        permissions: set[str] | None = None,
    ) -> None:
        super().__init__(username, email, role, active, password)
        self.permissions: set[str] = set(permissions) if permissions else set()

    def grant_permission(self, permission: str) -> None:
        self.permissions.add(permission)

    def revoke_permission(self, permission: str) -> None:
        self.permissions.discard(permission)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def __str__(self) -> str:
        perms = ", ".join(sorted(self.permissions)) or "none"
        return f"{super().__str__()} permissions=[{perms}]"


class Session:
    """Сеанс користувача."""

    def __init__(self, ip: str) -> None:
        self.ip = ip
        self.login_time: datetime = utc_now()
        self.last_activity: datetime = self.login_time

    def touch(self) -> None:
        self.last_activity = utc_now()

    def is_active(self, timeout_sec: int, now: datetime | None = None) -> bool:
        if timeout_sec <= 0:
            raise ValueError("timeout_sec має бути додатним")
        current = now or utc_now()
        return current - self.last_activity <= timedelta(seconds=timeout_sec)


@dataclass(frozen=True)
class AuditEntry:
    """Окремий запис аудиту."""

    timestamp: datetime
    username: str
    action: str


class AuditLog:
    """Журнал аудиту (паролі не записуються)."""

    def __init__(self) -> None:
        self.entries: list[AuditEntry] = []

    def add_log(self, username: str, action: str) -> None:
        self.entries.append(AuditEntry(utc_now(), username, action))

    def show_all(self) -> None:
        for e in self.entries:
            ts = e.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"{ts} | {e.username} | {e.action}")


class UserAccount:
    """Обліковий запис: композиція User + Session + AuditLog."""

    def __init__(
        self,
        user: User,
        session: Session | None = None,
        audit_log: AuditLog | None = None,
    ) -> None:
        self.user = user
        self.session = session
        self.audit_log = audit_log if audit_log is not None else AuditLog()

    def login(self, username: str, password: str, ip: str) -> bool:
        ok = (
            self.user.active
            and username == self.user.username
            and self.user.check_password(password)
        )
        if not ok:
            self.audit_log.add_log(username, "login_failure")
            return False
        self.session = Session(ip)
        self.session.touch()
        self.audit_log.add_log(username, "login_success")
        return True

    def is_authenticated(self) -> bool:
        """Перевірка не продовжує сеанс."""
        return self.session is not None and self.session.is_active(SESSION_TIMEOUT_SEC)

    def logout(self) -> None:
        if self.session is None:
            return
        self.session = None
        self.audit_log.add_log(self.user.username, "logout")

    def __getitem__(self, key: str):
        if key == "user":
            return self.user
        if key == "session":
            return self.session
        if key == "audit_log":
            return self.audit_log
        raise KeyError(key)

    def __setitem__(self, key: str, value) -> None:
        if key == "user":
            if not isinstance(value, User):
                raise TypeError("user має бути User")
            self.user = value
        elif key == "session":
            if value is not None and not isinstance(value, Session):
                raise TypeError("session має бути Session або None")
            self.session = value
        elif key == "audit_log":
            if not isinstance(value, AuditLog):
                raise TypeError("audit_log має бути AuditLog")
            self.audit_log = value
        else:
            raise KeyError(key)


def run_demo() -> None:
    """Демонстрація роботи класів."""
    print("=== Завдання 1: демонстрація ===")
    admin = Admin("admin01", "admin01@example.com", password="S3cret!pass")
    account = UserAccount(admin)

    print("Невдалий вхід:", account.login("admin01", "wrong", "10.0.0.5"))
    print("Успішний вхід:", account.login("admin01", "S3cret!pass", "10.0.0.5"))
    print("Автентифіковано:", account.is_authenticated())

    try:
        admin.email = "1bad@example"
    except ValueError as exc:
        print("Помилка валідації email:", exc)
    admin.email = "new_admin@corp.example.com"
    print("Email змінено на:", admin.email)

    admin.grant_permission("read_logs")
    admin.grant_permission("manage_users")
    admin.revoke_permission("read_logs")
    print(admin)
    print("manage_users:", admin.has_permission("manage_users"))

    account["session"].last_activity -= timedelta(seconds=SESSION_TIMEOUT_SEC + 60)
    print("Після таймауту автентифіковано:", account.is_authenticated())

    account.login("admin01", "S3cret!pass", "10.0.0.5")
    account.logout()
    print("Після logout автентифіковано:", account.is_authenticated())

    try:
        account["password_hash"]
    except KeyError as exc:
        print("Доступ до хешу заборонено, KeyError:", exc)

    print("--- AuditLog ---")
    account.audit_log.show_all()
