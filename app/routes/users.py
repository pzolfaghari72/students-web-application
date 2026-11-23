from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from ..account_input import ProfileInput, password_error, profile_values
from ..auth import AdminUser, end_session, matches_session, passwords, utc_now
from ..crud import search_pattern
from ..models import User
from ..preferences import get_preferences
from ..web import Database, FormInput, render


router = APIRouter(prefix="/admin")
ROLES = ("Admin", "User")


def show_users(request, session, *, selected=None, values=None, error="", status_code=200, q="", page=1):
    columns = (
        User.user_id, User.username, User.first_name, User.last_name, User.email,
        User.role, User.is_active, User.created_at,
    )
    records = select(*columns)
    total_records = select(func.count(User.user_id))
    if q:
        pattern = search_pattern(q)
        match = or_(*(field.like(pattern, escape="!") for field in columns[1:5]))
        records = records.where(match)
        total_records = total_records.where(match)
    size = get_preferences(request).page_size
    total = session.scalar(total_records)
    pages = max(1, (total + size - 1) // size)
    page = min(page, pages)
    users = session.execute(records.order_by(User.user_id.desc()).offset((page - 1) * size).limit(size)).all()
    return render(
        request, "users.html", section="users", users=users, selected=selected, values=values,
        roles=ROLES, error=error, status_code=status_code, q=q, page=page, pages=pages, total=total,
        saved=request.query_params.get("saved") == "1",
    )


@router.get("/users")
def manage_users(
    request: Request, session: Database, admin: AdminUser,
    user_id: Annotated[int | None, Query(ge=1, le=2147483647)] = None,
    q: Annotated[str, Query(max_length=100)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
):
    if user_id == admin.user_id:
        return RedirectResponse(request.url_for("user_panel"), status_code=303)
    selected = session.get(User, user_id) if user_id is not None else None
    if user_id is not None and selected is None:
        raise HTTPException(404, "This account could not be found.")
    return show_users(request, session, selected=selected, q=q.strip(), page=page)


@router.post("/users")
def save_user(
    request: Request, session: Database, admin: AdminUser, form: FormInput,
    user_id: Annotated[int | None, Query(ge=1, le=2147483647)] = None,
):
    if user_id == admin.user_id:
        raise HTTPException(403, "Use My Panel to update your own account.")
    actor = session.scalar(
        select(User).where(User.user_id == admin.user_id)
        .with_hint(User, "WITH (TABLOCKX, HOLDLOCK)", dialect_name="mssql")
        .execution_options(populate_existing=True)
    )
    if not matches_session(actor, request.state.session_token) or actor.role != "Admin":
        raise HTTPException(403, "Your administrator session has changed. Sign in again.")

    selected = session.get(User, user_id) if user_id is not None else None
    if user_id is not None and selected is None:
        raise HTTPException(404, "This account could not be found.")
    role = form.get("role")
    active = form.get("is_active") == "1"
    password = form.get("password", "")
    confirmation = form.get("confirm_password", "")
    values = profile_values(form) | {"role": role, "is_active": active}
    error = ""
    try:
        profile = ProfileInput.model_validate(values)
    except ValidationError:
        error = "Enter a valid username, first name, last name, and optional email."
    if role not in ROLES:
        error = "Choose an available role."
    if form.get("is_active") not in {"0", "1"}:
        error = "Choose an available account status."
    if not error and (password or confirmation or selected is None):
        error = password_error(password, confirmation)
    if error:
        return show_users(request, session, selected=selected, values=values, error=error, status_code=422)

    if selected is None:
        selected = User(created_at=utc_now())
        session.add(selected)
    elif selected.role != role or selected.is_active != active or password:
        end_session(selected)
    for field, value in profile.model_dump().items():
        setattr(selected, field, value or None)
    selected.role = role
    selected.is_active = active
    if password:
        selected.password_hash = passwords.hash(password)
    try:
        session.flush()
        selected_id = selected.user_id
        session.commit()
    except IntegrityError:
        session.rollback()
        existing = session.get(User, user_id) if user_id is not None else None
        return show_users(
            request, session, selected=existing, values=values,
            error="This username is already in use.", status_code=409,
        )

    location = request.url_for("manage_users").include_query_params(user_id=selected_id, saved=1)
    return RedirectResponse(location, status_code=303)
