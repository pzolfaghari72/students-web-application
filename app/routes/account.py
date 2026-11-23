from io import BytesIO

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from PIL import Image, ImageOps
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile

from ..account_input import ProfileInput, password_error, profile_values
from ..auth import CurrentUser, lock_current_user, passwords, start_session, verify_password
from ..preferences import PAGE_SIZE_COOKIE, PAGE_SIZES, PREFERENCE_MAX_AGE, THEME_COOKIE, THEMES
from ..web import Database, FormInput, render, require_same_origin


router = APIRouter()
PHOTO_LIMIT = 2 * 1024 * 1024


@router.get("/account")
def user_panel(request: Request, user: CurrentUser):
    notices = {
        "1": "Preferences saved.", "profile": "Profile updated.",
        "password": "Password changed.", "photo": "Profile picture updated.",
    }
    return show_account(request, notice=notices.get(request.query_params.get("saved")))


def show_account(request: Request, *, notice=None, errors=None, values=None, status_code=200):
    return render(
        request, "account.html", section="account", themes=THEMES, page_sizes=PAGE_SIZES,
        notice=notice, errors=errors or {}, values=values, status_code=status_code,
    )


@router.post("/account")
def save_preferences(request: Request, user: CurrentUser, form: FormInput):
    theme = form.get("theme")
    page_size = form.get("page_size")
    if theme not in THEMES or page_size not in {str(size) for size in PAGE_SIZES}:
        return show_account(request, errors={"preferences": "Select an available theme and page size."}, status_code=422)

    response = RedirectResponse(request.url_for("user_panel").include_query_params(saved=1), status_code=303)
    response.set_cookie(THEME_COOKIE, theme, max_age=PREFERENCE_MAX_AGE, samesite="lax")
    response.set_cookie(
        PAGE_SIZE_COOKIE, page_size, max_age=PREFERENCE_MAX_AGE, httponly=True, samesite="lax",
    )
    return response


def account_url(request: Request, saved: str):
    return request.url_for("user_panel").include_query_params(saved=saved)


@router.post("/account/profile")
def update_profile(request: Request, session: Database, user: CurrentUser, form: FormInput):
    values = profile_values(form)
    try:
        profile = ProfileInput.model_validate(values)
    except ValidationError as exc:
        errors = {item["loc"][0]: item["msg"].removeprefix("Value error, ") for item in exc.errors()}
        return show_account(request, values=values, errors=errors, status_code=422)

    locked = lock_current_user(request, session, user)
    if (locked.username != profile.username or (locked.email or "") != profile.email) and not verify_password(
        form.get("current_password", ""), locked.password_hash,
    ):
        return show_account(
            request, values=values, errors={"profile": "Enter your current password to change your username or email."},
            status_code=422,
        )

    locked.username = profile.username
    locked.first_name = profile.first_name
    locked.last_name = profile.last_name
    locked.email = profile.email or None
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return show_account(
            request, values=values, errors={"username": "This username is already in use."}, status_code=409,
        )
    return RedirectResponse(account_url(request, "profile"), status_code=303)


@router.post("/account/password")
def update_password(request: Request, session: Database, user: CurrentUser, form: FormInput):
    new_password = form.get("password", "")
    error = password_error(new_password, form.get("confirm_password", ""))
    if not error:
        locked = lock_current_user(request, session, user)
        if verify_password(form.get("current_password", ""), locked.password_hash):
            locked.password_hash = passwords.hash(new_password)
            return start_session(request, session, locked, account_url(request, "password"))
        error = "Your current password is incorrect."
    return show_account(request, errors={"password": error}, status_code=422)


def normalize_picture(data: bytes):
    with Image.open(BytesIO(data), formats=("JPEG", "PNG", "WEBP")) as image:
        if image.width * image.height > 16_000_000:
            raise ValueError("Image dimensions exceed the supported size.")
        clean = ImageOps.exif_transpose(image)
        clean.thumbnail((384, 384))
        result = BytesIO()
        clean.convert("RGB").save(result, format="JPEG", quality=86)
        return result.getvalue()


async def read_picture(request: Request):
    require_same_origin(request)
    length = request.headers.get("content-length", "")
    if not length.isdecimal() or len(length) > 10 or int(length) > PHOTO_LIMIT + 8192:
        raise HTTPException(413, "Choose a picture smaller than 2 MB.")
    async with request.form(max_files=1, max_fields=1) as form:
        picture = form.get("picture")
        if not isinstance(picture, UploadFile):
            return None
        data = await picture.read(PHOTO_LIMIT + 1)
    if len(data) > PHOTO_LIMIT:
        raise HTTPException(413, "Choose a picture smaller than 2 MB.")
    try:
        return await run_in_threadpool(normalize_picture, data)
    except (OSError, ValueError, Image.DecompressionBombError):
        return None


@router.post("/account/picture")
async def update_picture(request: Request, session: Database, user: CurrentUser):
    picture = await read_picture(request)
    if picture is None:
        return show_account(
            request, errors={"photo": "Choose a readable JPEG, PNG, or WebP image up to 2 MB."}, status_code=422,
        )
    return await run_in_threadpool(save_picture, request, session, user, picture)


def save_picture(request: Request, session: Database, user, picture: bytes | None):
    locked = lock_current_user(request, session, user)
    locked.profile_picture = picture
    session.commit()
    return RedirectResponse(account_url(request, "photo"), status_code=303)


@router.post("/account/picture/remove")
def remove_picture(request: Request, session: Database, user: CurrentUser, form: FormInput):
    return save_picture(request, session, user, None)


@router.get("/account/picture")
def profile_picture(user: CurrentUser):
    if not user.profile_picture:
        raise HTTPException(404, "Profile picture unavailable.")
    return Response(
        user.profile_picture, media_type="image/jpeg",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
