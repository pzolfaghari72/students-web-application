import re
from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, ValidationInfo, field_validator


SQL_INT_MIN = -(2**31)
SQL_INT_MAX = 2**31 - 1
SqlInt = Annotated[int, Field(ge=SQL_INT_MIN, le=SQL_INT_MAX)]


class StudentInput(BaseModel):
    first_name: str = Field(title="First name", min_length=1, max_length=40)
    middle_name: str = Field(default="", title="Middle name", max_length=40)
    last_name: str = Field(title="Last name", min_length=1, max_length=40)
    date_of_birth: date = Field(title="Date of birth")
    gender: str = Field(title="Gender code", min_length=1, max_length=1)
    email: str = Field(title="Email address", min_length=1, max_length=80)
    telephone: str = Field(title="Telephone", min_length=1, max_length=20)
    street_address: str = Field(title="Street address", min_length=1, max_length=50)
    city: str = Field(title="City", min_length=1, max_length=30)
    state: str = Field(title="State", min_length=1, max_length=2)
    zip_code: str = Field(title="ZIP code", min_length=1, max_length=5)
    degree_id: SqlInt = Field(title="Degree")
    class_standing_code: str | None = Field(default=None, title="Class standing", max_length=2)
    enrollment_term: str = Field(title="Enrollment term", min_length=1, max_length=6)
    student_status: str = Field(title="Student status", min_length=1, max_length=1)

    @field_validator("class_standing_code", mode="before")
    @classmethod
    def blank_class_standing(cls, value):
        return None if value == "" else value

    @field_validator("date_of_birth", mode="before")
    @classmethod
    def iso_date(cls, value):
        if isinstance(value, str) and not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("Enter a date in YYYY-MM-DD format.")
        return value

    @field_validator("email")
    @classmethod
    def email_address(cls, value: str) -> str:
        if not re.fullmatch(r"[^@\s]+@[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value

    @field_validator("*")
    @classmethod
    def varchar_value(cls, value, info: ValidationInfo):
        if isinstance(value, str):
            if not value.strip() and cls.model_fields[info.field_name].is_required():
                raise ValueError("This field is required.")
            try:
                # The existing varchar columns use the SQL Server Windows-1252 collation.
                value.encode("cp1252")
            except UnicodeEncodeError:
                raise ValueError("This field contains characters the database cannot store.") from None
        return value
