import hashlib
import hmac
import re
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import User
from .web import Database


COOKIE = "student_records_session"
SESSION_SECONDS = 8 * 60 * 60
PASSWORD_MIN_LENGTH = 15
PASSWORD_MAX_LENGTH = 128
passwords = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
dummy_hash = passwords.hash(secrets.token_urlsafe(32))


class SignInRequired(Exception):
    pass


def utc_now():
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)


def verify_password(password: str, stored_hash: str | None) -> bool:
    if len(password) > PASSWORD_MAX_LENGTH:
        return False
    try:
        valid = passwords.verify(stored_hash or dummy_hash, password)
    except (VerificationError, InvalidHashError):
        return False
    return valid and stored_hash is not None


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def lock_user(session: Session, user_id: int) -> User | None:
    statement = select(User).where(User.user_id == user_id)
    return session.scalar(
        statement.with_hint(User, "WITH (UPDLOCK)", dialect_name="mssql")
        .execution_options(populate_existing=True)
    )


def matches_session(user: User | None, token: str) -> bool:
    return bool(
        user and user.is_active and user.session_hash and user.session_expires_at
        and user.session_expires_at > utc_now()
        and hmac.compare_digest(user.session_hash, token_hash(token))
    )


def require_user(request: Request, session: Database) -> User:
    cookie = request.cookies.get(COOKIE, "")
    if not re.fullmatch(r"[0-9]{1,10}\.[A-Za-z0-9_-]{43}", cookie):
        raise SignInRequired
    raw_id, token = cookie.split(".")
    user_id = int(raw_id)
    user = session.get(User, user_id) if 1 <= user_id <= 2147483647 else None
    if not matches_session(user, token):
        raise SignInRequired
    request.state.current_user = user
    request.state.session_token = token
    return user


CurrentUser = Annotated[User, Depends(require_user)]


def require_admin(user: CurrentUser):
    if user.role != "Admin":
        raise HTTPException(403, "This action requires an administrator account.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def lock_current_user(request: Request, session: Session, user: User) -> User:
    locked = lock_user(session, user.user_id)
    if not matches_session(locked, request.state.session_token):
        raise SignInRequired
    return locked


def end_session(user: User):
    user.session_hash = None
    user.session_expires_at = None


def start_session(request: Request, session: Session, user: User, destination: str):
    token = secrets.token_urlsafe(32)
    user.session_hash = token_hash(token)
    user.session_expires_at = utc_now() + timedelta(seconds=SESSION_SECONDS)
    session.flush()
    cookie = f"{user.user_id}.{token}"
    session.commit()
    response = RedirectResponse(destination, status_code=303)
    response.set_cookie(
        COOKIE, cookie, max_age=SESSION_SECONDS, httponly=True,
        samesite="strict", secure=request.url.scheme == "https",
    )
    return response
