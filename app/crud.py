import hashlib
import json

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .models import ClassStanding, Degree, Student, Term
from .preferences import DEFAULT_PAGE_SIZE
from .schemas import SQL_INT_MAX, SQL_INT_MIN, StudentInput


STATUS_LABELS = {"A": "Active", "G": "Graduated", "W": "Withdrawn"}


def status_label(code: str) -> str:
    return STATUS_LABELS.get(code.upper(), f"Code {code}" if code else "Unspecified")


def search_pattern(query: str) -> str:
    escaped = query.replace("!", "!!").replace("%", "!%").replace("_", "!_").replace("[", "![")
    return f"%{escaped}%"


def degree_options(session: Session):
    return session.execute(select(Degree.degree_id, Degree.name).order_by(Degree.name, Degree.degree_id)).all()


def status_options(session: Session):
    statement = select(Student.student_status).distinct().order_by(Student.student_status)
    return [(code, status_label(code)) for code in session.scalars(statement)]


def term_options(session: Session):
    return session.scalars(select(Term.code).order_by(Term.year.desc(), Term.code)).all()


def form_options(session: Session):
    return {
        "degree_id": degree_options(session),
        "class_standing_code": session.execute(
            select(ClassStanding.code, ClassStanding.name).order_by(ClassStanding.name)
        ).all(),
        "enrollment_term": [(code, code) for code in term_options(session)],
        "student_status": status_options(session),
    }


def student_conditions(query: str, status: str, degree_id: int | None, term: str = ""):
    conditions = []
    if query:
        pattern = search_pattern(query)
        matches = [
            column.like(pattern, escape="!")
            for column in (Student.first_name, Student.last_name, Student.email)
        ]
        if " " in query:
            full_name = Student.first_name + " " + Student.last_name
            matches.append(full_name.like(pattern, escape="!"))
        if query.removeprefix("-").isascii() and query.removeprefix("-").isdigit():
            student_id = int(query)
            if SQL_INT_MIN <= student_id <= SQL_INT_MAX:
                matches.append(Student.student_id == student_id)
        conditions.append(or_(*matches))
    if status:
        conditions.append(Student.student_status == status)
    if degree_id is not None:
        conditions.append(Student.degree_id == degree_id)
    if term:
        conditions.append(Student.enrollment_term == term)
    return conditions


def list_students(
    session: Session, query: str, status: str, degree_id: int | None, page: int,
    *, term: str = "", page_size: int = DEFAULT_PAGE_SIZE, full: bool = False,
):
    conditions = student_conditions(query, status, degree_id, term)
    total = session.scalar(select(func.count_big(Student.student_id)).where(*conditions))
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, pages)
    fields = (
        [getattr(Student, name) for name in StudentInput.model_fields] if full else
        [Student.first_name, Student.last_name, Student.email, Student.student_status, Student.enrollment_term]
    )
    statement = (
        select(Student.student_id, *fields, Degree.name.label("degree_name"))
        .outerjoin(Degree, Student.degree_id == Degree.degree_id)
        .where(*conditions)
        .order_by(Student.student_id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return session.execute(statement).all(), total, page, pages


def get_student_details(session: Session, student_id: int):
    statement = (
        select(Student, Degree.name, ClassStanding.name)
        .outerjoin(Degree, Student.degree_id == Degree.degree_id)
        .outerjoin(ClassStanding, Student.class_standing_code == ClassStanding.code)
        .where(Student.student_id == student_id)
    )
    return session.execute(statement).one_or_none()


def student_values(student: Student):
    return {field: getattr(student, field) for field in StudentInput.model_fields}


def student_revision(student: Student) -> str:
    snapshot = json.dumps(student_values(student), default=str, sort_keys=True)
    return hashlib.sha256(snapshot.encode()).hexdigest()


def lock_student(session: Session, student_id: int):
    statement = (
        select(Student)
        .where(Student.student_id == student_id)
        .with_hint(Student, "WITH (UPDLOCK)", dialect_name="mssql")
        .execution_options(populate_existing=True)
    )
    return session.scalar(statement)
