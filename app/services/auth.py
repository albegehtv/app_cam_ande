"""User authentication and management helpers."""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Optional

from sqlalchemy.orm import Session

from ..database import session_scope
from ..models import User

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 390_000


def _pbkdf2(password: str, *, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def hash_password(password: str, *, iterations: int = _ITERATIONS) -> str:
    """Return a PBKDF2 hashed password string."""

    salt = os.urandom(16)
    digest = _pbkdf2(password, salt=salt, iterations=iterations)
    return f"{_ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Validate a password against the stored hash."""

    try:
        algorithm, iteration_str, salt_hex, hash_hex = stored_hash.split("$", 3)
        iterations = int(iteration_str)
    except (ValueError, TypeError):
        return False

    if algorithm != _ALGORITHM:
        return False

    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    candidate = _pbkdf2(password, salt=salt, iterations=iterations)
    return hmac.compare_digest(candidate, expected)


def _detach(user: Optional[User], session: Session) -> Optional[User]:
    if user is not None:
        session.expunge(user)
    return user


def get_user_by_username(username: str) -> Optional[User]:
    with session_scope() as session:
        user = session.query(User).filter(User.username == username).first()
        return _detach(user, session)


def get_user_by_id(user_id: int) -> Optional[User]:
    with session_scope() as session:
        user = session.query(User).get(user_id)
        return _detach(user, session)


def create_user(username: str, password: str, *, full_name: Optional[str] = None) -> User:
    with session_scope() as session:
        existing = session.query(User).filter(User.username == username).first()
        if existing:
            raise ValueError("El nombre de usuario ya está registrado.")

        user = User(
            username=username.strip(),
            full_name=full_name.strip() if full_name else None,
            password_hash=hash_password(password),
        )
        session.add(user)
        session.flush()
        session.refresh(user)
        return _detach(user, session)


def authenticate_user(username: str, password: str) -> Optional[User]:
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
