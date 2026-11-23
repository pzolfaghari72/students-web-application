from dataclasses import dataclass

from fastapi import Request


THEME_COOKIE = "student_records_theme"
PAGE_SIZE_COOKIE = "student_records_page_size"
THEMES = {"system": "System", "light": "Light", "dark": "Dark"}
PAGE_SIZES = (20, 40, 80)
DEFAULT_PAGE_SIZE = PAGE_SIZES[0]
PREFERENCE_MAX_AGE = 365 * 24 * 60 * 60


@dataclass(frozen=True)
class Preferences:
    theme: str = "system"
    page_size: int = DEFAULT_PAGE_SIZE


def get_preferences(request: Request) -> Preferences:
    theme = request.cookies.get(THEME_COOKIE, "system")
    saved_size = request.cookies.get(PAGE_SIZE_COOKIE)
    page_size = next((size for size in PAGE_SIZES if str(size) == saved_size), DEFAULT_PAGE_SIZE)
    return Preferences(theme=theme if theme in THEMES else "system", page_size=page_size)
