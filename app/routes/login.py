import time
from collections import deque
from threading import Lock

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import select

from ..account_input import ProfileInput, password_error, profile_values
from ..auth import (
    COOKIE, CurrentUser, end_session, lock_current_user, passwords, start_session, utc_now,
    verify_password,
)
from ..models import User
from ..web import Database, FormInput, render


router = APIRouter()
login_attempts = deque()
attempt_lock = Lock()


def has_account(session, *, setup_lock=False):
    statement = select(User.user_id).limit(1)
    if setup_lock:
        statement = statement.with_hint(User, "WITH (TABLOCKX, HOLDLOCK)", dialect_name="mssql")
    return session.scalar(statement) is not None


@router.get("/login")
def sign_in(request: Request, session: Database):
    return render(request, "login.html", setup=not has_account(session))


@router.post("/login")
def check_login(request: Request, session: Database, form: FormInput):
    now = time.monotonic()
    with attempt_lock:
        while login_attempts and now - login_attempts[0] > 60:
            login_attempts.popleft()
        if len(login_attempts) >= 12:
            return render(
                request, "login.html", error="Too many sign-in attempts. Try again in a minute.",
                status_code=429,
            )
        login_attempts.append(now)

    username = form.get("username", "").strip().lower()
    if len(username) > 64:
        username = ""
    statement = select(User).where(User.username == username)
    user = session.scalar(statement.with_hint(User, "WITH (UPDLOCK)", dialect_name="mssql"))
    valid = verify_password(form.get("password", ""), user.password_hash if user else None)
    if not valid or not user.is_active:
        return render(
            request, "login.html", username=username, error="Invalid username or password.",
            status_code=401,
        )

    if passwords.check_needs_rehash(user.password_hash):
        user.password_hash = passwords.hash(form["password"])
    destination = request.url_for("dashboard")
    return start_session(request, session, user, destination)


@router.get("/setup")
def first_account(request: Request, session: Database):
    if has_account(session):
        return RedirectResponse(request.url_for("sign_in"), status_code=303)
    return render(request, "login.html", setup=True, values={})


@router.post("/setup")
def create_first_account(request: Request, session: Database, form: FormInput):
    if has_account(session):
        raise HTTPException(409, "Initial account setup has already been completed.")
    values = profile_values(form)
    password = form.get("password", "")
    error = password_error(password, form.get("confirm_password", ""))
    try:
        account = ProfileInput.model_validate(values)
    except ValidationError:
        account = None
        error = "Enter a valid username, first name, last name, and optional email."
    if error:
        return render(request, "login.html", setup=True, values=values, error=error, status_code=422)

    hashed = passwords.hash(password)
    if has_account(session, setup_lock=True):
        raise HTTPException(409, "Initial account setup has already been completed.")
    user = User(
        **account.model_dump(exclude={"email"}), email=account.email or None,
        role="Admin", password_hash=hashed, created_at=utc_now(),
    )
    session.add(user)
    return start_session(request, session, user, request.url_for("dashboard"))


@router.post("/logout")
def sign_out(request: Request, session: Database, user: CurrentUser, form: FormInput):
    end_session(lock_current_user(request, session, user))
    session.commit()
    response = RedirectResponse(request.url_for("sign_in"), status_code=303)
    response.delete_cookie(COOKIE)
    return response
