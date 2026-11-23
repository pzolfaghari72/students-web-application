import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .auth import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH


class ProfileInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=64)
    first_name: str = Field(min_length=1, max_length=64)
    last_name: str = Field(min_length=1, max_length=64)
    email: str = Field(default="", max_length=254)

    @field_validator("username")
    @classmethod
    def user_name(cls, value: str):
        value = value.lower()
        if not re.fullmatch(r"[a-z0-9._-]+", value):
            raise ValueError("Use only letters A–Z, digits, dots, hyphens, and underscores.")
        return value

    @field_validator("first_name", "last_name", "email")
    @classmethod
    def unicode_length(cls, value: str, info):
        limit = 254 if info.field_name == "email" else 64
        if len(value.encode("utf-16-le")) // 2 > limit:
            raise ValueError(f"Use at most {limit} characters.")
        if info.field_name == "email" and value and not re.fullmatch(r"[^@\s]+@[^@\s]+", value):
            raise ValueError("Enter a valid email address.")
        return value


def profile_values(form: dict):
    return {field: form.get(field, "") for field in ProfileInput.model_fields}


def password_error(password: str, confirmation: str):
    if not PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH:
        return f"Use a password with {PASSWORD_MIN_LENGTH}–{PASSWORD_MAX_LENGTH} characters."
    if password != confirmation:
        return "The two passwords must match."
    return ""
