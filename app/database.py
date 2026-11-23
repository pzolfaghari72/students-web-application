import os
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session


class DatabaseConfigurationError(RuntimeError):
    pass


@lru_cache
def get_engine():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", interpolate=False)
    keys = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_ODBC_DRIVER")
    config = {key: os.environ.get(key, "") for key in keys}
    missing = [key for key, value in config.items() if not value]
    if missing:
        raise DatabaseConfigurationError("Set " + ", ".join(missing) + " in .env.")

    try:
        port = int(config["DB_PORT"])
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise DatabaseConfigurationError("DB_PORT must be a number from 1 to 65535.") from None

    tls = {
        "Encrypt": os.environ.get("DB_ENCRYPT", "yes").lower(),
        "TrustServerCertificate": os.environ.get("DB_TRUST_SERVER_CERTIFICATE", "no").lower(),
    }
    if any(value not in {"yes", "no"} for value in tls.values()):
        raise DatabaseConfigurationError("Set each TLS option to yes or no.")

    url = URL.create(
        "mssql+pyodbc",
        host=config["DB_HOST"],
        port=port,
        database=config["DB_NAME"],
        username=config["DB_USER"],
        password=config["DB_PASSWORD"],
        query={"driver": config["DB_ODBC_DRIVER"], **tls},
    )
    return create_engine(
        url, connect_args={"timeout": 5}, pool_pre_ping=True, hide_parameters=True
    )


def get_session():
    with Session(get_engine()) as session:
        yield session


@contextmanager
def query_timeout(session: Session, seconds: int):
    dialect = session.get_bind().dialect
    if (dialect.name, dialect.driver) != ("mssql", "pyodbc"):
        yield
        return

    connection = session.connection()
    driver_connection = connection.connection.driver_connection
    previous_timeout = driver_connection.timeout
    driver_connection.timeout = seconds
    try:
        yield
    finally:
        if not connection.invalidated:
            driver_connection.timeout = previous_timeout
