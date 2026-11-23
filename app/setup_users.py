from sqlalchemy import inspect, text

from .database import get_engine
from .models import User


def main():
    with get_engine().begin() as connection:
        if connection.scalar(text("SELECT DB_NAME()")) != "Students":
            raise SystemExit("Select the Students database before running account setup.")

        object_type = connection.scalar(text(
            "SELECT type FROM sys.objects WHERE object_id = OBJECT_ID(N'dbo.Users')"
        ))
        if object_type is None:
            User.__table__.create(connection)
            print("Created dbo.Users.")
            return
        if object_type.strip() != "U":
            raise SystemExit("dbo.Users exists as a different database object.")

        columns = {column["name"] for column in inspect(connection).get_columns("Users", schema="dbo")}
        if not {column.name for column in User.__table__.columns}.issubset(columns):
            raise SystemExit("dbo.Users exists with a different schema.")
        print("dbo.Users is ready.")


if __name__ == "__main__":
    main()
