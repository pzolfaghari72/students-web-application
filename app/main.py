import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import DBAPIError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .auth import COOKIE, SignInRequired, require_user
from .database import DatabaseConfigurationError
from .routes import account, dashboard, login, reference, students, users
from .web import APP_DIR, APP_NAME, problem


app = FastAPI(title=APP_NAME, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost"])
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
app.include_router(login.router)
for router in (dashboard.router, students.router, reference.router, account.router):
    app.include_router(router, dependencies=[Depends(require_user)])
app.include_router(users.router)
logger = logging.getLogger(__name__)


@app.exception_handler(SignInRequired)
async def sign_in_required(request: Request, exc: SignInRequired):
    response = RedirectResponse(request.url_for("sign_in"), status_code=303)
    response.delete_cookie(COOKIE)
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(DatabaseConfigurationError)
async def missing_configuration(request: Request, exc: DatabaseConfigurationError):
    return problem(request, 503, "Database setup required", str(exc))


@app.exception_handler(DBAPIError)
async def database_error(request: Request, exc: DBAPIError):
    logger.warning("Database operation failed (%s).", type(exc.orig).__name__)
    return problem(
        request, 503, "Database unavailable",
        "Check the SQL Server connection settings and database permissions, then try again.",
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return problem(request, 404, "Page not found", exc.detail)
    return problem(request, exc.status_code, "Request could not be completed", exc.detail)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    return problem(request, 400, "Invalid request", "Check the student identifier or filter values.")
