"""Persistent user store backed by data/users.json.

Thread-safe for async via asyncio.Lock. Writes are atomic (write to temp file, rename).
Each user may have multiple API keys; all keys resolve to the same account + balance.
"""

import asyncio
import datetime
import json
import os
import secrets
import uuid
from pathlib import Path
from typing import Optional

import bcrypt

from app.models.user import UserRecord

_default_data_dir = str(Path(__file__).parent.parent.parent / "data")
DATA_FILE = Path(os.getenv("ONE_API_DATA_DIR", _default_data_dir)) / "users.json"


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def generate_api_key() -> str:
    return f"sk-{secrets.token_hex(32)}"


def _migrate(raw: dict) -> dict:
    """Migrate old single api_key field to api_keys list."""
    if "api_key" in raw and "api_keys" not in raw:
        raw["api_keys"] = [raw.pop("api_key")]
    return raw


class UserStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # Both dicts point to the same UserRecord object by reference via id.
        self._users: dict[str, UserRecord] = {}   # user.id → record
        self._by_key: dict[str, str] = {}          # api_key → user.id
        self._by_email: dict[str, str] = {}        # email → user.id
        self._load()

    # ------------------------------------------------------------------ load/save

    def _load(self) -> None:
        if not DATA_FILE.exists():
            return
        try:
            raw_list = json.loads(DATA_FILE.read_text())
            for raw in raw_list:
                raw = _migrate(raw)
                rec = UserRecord(**raw)
                self._users[rec.id] = rec
                self._by_email[rec.email] = rec.id
                for key in rec.api_keys:
                    self._by_key[key] = rec.id
        except Exception:
            pass  # corrupt file — start fresh

    def _save_sync(self) -> None:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(
            json.dumps([r.model_dump() for r in self._users.values()], indent=2)
        )
        tmp.replace(DATA_FILE)

    def _update(self, rec: UserRecord) -> None:
        """Replace a record in-place and persist (must be called under lock)."""
        self._users[rec.id] = rec
        for key in rec.api_keys:
            self._by_key[key] = rec.id
        self._save_sync()

    # ------------------------------------------------------------------ public API

    async def create_user(self, email: str, password: str) -> UserRecord:
        async with self._lock:
            if email.lower() in self._by_email:
                raise ValueError(f"Email {email!r} is already registered.")
            key = generate_api_key()
            rec = UserRecord(
                id=str(uuid.uuid4()),
                email=email.lower(),
                password_hash=_hash_password(password),
                api_keys=[key],
                balance=100,
                created_at=datetime.datetime.now(datetime.UTC).isoformat(),
            )
            self._by_email[rec.email] = rec.id
            self._update(rec)
            return rec

    async def add_api_key(self, user_id: str) -> tuple[str, UserRecord]:
        """Generate a new key for the account; return (new_key, updated_record)."""
        async with self._lock:
            rec = self._users.get(user_id)
            if rec is None:
                raise ValueError("User not found.")
            new_key = generate_api_key()
            updated = rec.model_copy(update={"api_keys": rec.api_keys + [new_key]})
            self._update(updated)
            return new_key, updated

    async def get_by_email(self, email: str) -> Optional[UserRecord]:
        uid = self._by_email.get(email.lower())
        return self._users.get(uid) if uid else None

    async def get_by_api_key(self, api_key: str) -> Optional[UserRecord]:
        uid = self._by_key.get(api_key)
        return self._users.get(uid) if uid else None

    async def update_balance(self, api_key: str, new_balance: int) -> None:
        async with self._lock:
            uid = self._by_key.get(api_key)
            if uid is None:
                return
            rec = self._users[uid]
            self._update(rec.model_copy(update={"balance": new_balance}))

    def all_users(self) -> list[UserRecord]:
        return list(self._users.values())
