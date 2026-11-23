from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .crud import status_label
from .database import get_session
from .preferences import THEME_COOKIE, get_preferences


APP_DIR = Path(__file__).resolve().parent
APP_NAME = "Students Application"
Database = Annotated[Session, Depends(get_session)]
templates = Jinja2Templates(directory=APP_DIR / "templates")
templates.env.globals.update(app_name=APP_NAME, status_label=status_label)


def render(request: Request, template: str, *, status_code: int = 200, **context):
    context.update(
        preferences=get_preferences(request), theme_cookie=THEME_COOKIE,
        current_user=getattr(request.state, "current_user", None),
    )
    return templates.TemplateResponse(
        request=request, name=template, context=context, status_code=status_code,
        headers={
            "Cache-Control": "no-store", "Referrer-Policy": "same-origin",
            "X-Frame-Options": "SAMEORIGIN",
        },
    )


def problem(request: Request, status_code: int, title: str, message: str):
    return render(request, "error.html", status_code=status_code, title=title, message=message)


def require_same_origin(request: Request):
    if request.headers.get("origin") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "Open the form in this application before submitting it.")


async def read_form(request: Request):
    require_same_origin(request)
    async with request.form(max_files=0, max_fields=24) as form:
        return dict(form)


FormInput = Annotated[dict, Depends(read_form)]
