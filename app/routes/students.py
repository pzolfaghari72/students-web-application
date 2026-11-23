import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from .. import crud
from ..auth import AdminUser, CurrentUser
from ..models import Student
from ..preferences import get_preferences
from ..schemas import SQL_INT_MAX, SQL_INT_MIN, StudentInput
from ..web import Database, FormInput, render


router = APIRouter(prefix="/students")
StudentId = Annotated[int, Path(ge=SQL_INT_MIN, le=SQL_INT_MAX)]


def student_filters(
    q: Annotated[str, Query(max_length=100)] = "",
    status: Annotated[str, Query(max_length=1)] = "",
    degree: Annotated[str, Query(max_length=11)] = "",
    page: Annotated[int, Query(ge=1)] = 1,
    term: Annotated[str, Query(max_length=6)] = "",
):
    try:
        degree_id = int(degree) if degree else None
        if degree_id is not None and not SQL_INT_MIN <= degree_id <= SQL_INT_MAX:
            raise ValueError
    except ValueError:
        raise HTTPException(400, "Choose a valid degree filter.") from None
    return {"q": q.strip(), "status": status, "degree": degree_id, "page": page, "term": term}


StudentFilters = Annotated[dict, Depends(student_filters)]


def table_context(request: Request, session: Session, filters: dict, management: bool):
    page_size = get_preferences(request).page_size
    students, total, page, pages = crud.list_students(
        session, filters["q"], filters["status"], filters["degree"], filters["page"],
        term=filters["term"], page_size=page_size, full=management,
    )
    return dict(
        filters | {"page": page}, students=students, total=total, pages=pages, management=management,
        first=(page - 1) * page_size + 1, last=(page - 1) * page_size + len(students),
        degrees=crud.degree_options(session), statuses=crud.status_options(session),
        terms=crud.term_options(session),
    )


@router.get("")
def students_list(request: Request, session: Database, user: CurrentUser, filters: StudentFilters):
    if user.role == "Admin":
        return render_form(request, session, crud.form_options(session), {}, filters=filters)
    return render(request, "students.html", section="students", **table_context(request, session, filters, False))


def render_form(
    request: Request, session: Session, options, values, *,
    student_id: int | None = None, revision: str = "",
    errors: dict | None = None, message: str = "", status_code: int = 200, filters: dict | None = None,
):
    lengths = {
        name: next((rule.max_length for rule in field.metadata if hasattr(rule, "max_length")), None)
        for name, field in StudentInput.model_fields.items()
    }
    if filters is None:
        filters = {"q": "", "status": "", "degree": None, "page": 1, "term": ""}
    notices = {"created": "Student inserted.", "updated": "Student updated.", "deleted": "Student deleted."}
    return render(
        request, "student_form.html", section="students", fields=StudentInput.model_fields,
        lengths=lengths, options=options, values=values, student_id=student_id,
        revision=revision, errors=errors or {}, message=message, status_code=status_code,
        notice=notices.get(request.query_params.get("saved")),
        **table_context(request, session, filters, True),
    )


@router.get("/new")
def student_new(request: Request, session: Database, admin: AdminUser, filters: StudentFilters):
    return render_form(request, session, crud.form_options(session), {}, filters=filters)


def student_or_404(session: Session, student_id: int):
    student = session.get(Student, student_id)
    if student is None:
        raise HTTPException(404, "This student record could not be found.")
    return student


@router.get("/{student_id}")
def student_detail(request: Request, session: Database, student_id: StudentId):
    result = crud.get_student_details(session, student_id)
    if result is None:
        raise HTTPException(404, "This student record could not be found.")
    student, degree_name, standing_name = result
    notice = {"created": "Student registered.", "updated": "Student record saved."}
    return render(
        request, "student_detail.html", section="students", student=student,
        degree_name=degree_name, standing_name=standing_name,
        notice=notice.get(request.query_params.get("saved")),
    )


@router.get("/{student_id}/edit")
def student_edit(request: Request, session: Database, admin: AdminUser, student_id: StudentId, filters: StudentFilters):
    student = student_or_404(session, student_id)
    return render_form(
        request, session, crud.form_options(session), crud.student_values(student),
        student_id=student_id, revision=crud.student_revision(student), filters=filters,
    )


def form_values(form, options):
    values = {name: form[name] for name in StudentInput.model_fields if name in form}
    try:
        data = StudentInput.model_validate(values).model_dump()
    except ValidationError as exc:
        return values, {}, {
            item["loc"][0]: item["msg"].removeprefix("Value error, ")
            for item in exc.errors()
        }

    errors = {}
    for field, choices in options.items():
        if data[field] is not None and data[field] not in {value for value, _ in choices}:
            errors[field] = "Choose an available option."
    return values, data, errors


def save_student(request: Request, session: Session, form: dict, student_id: int | None = None):
    if student_id is not None:
        student_or_404(session, student_id)
    options = crud.form_options(session)
    values, data, errors = form_values(form, options)
    revision = form.get("revision", "")
    if errors:
        return render_form(
            request, session, options, values, student_id=student_id, revision=revision,
            errors=errors, status_code=422,
        )

    created = student_id is None
    try:
        if created:
            student = Student(**data)
            session.add(student)
        else:
            student = crud.lock_student(session, student_id)
            if student is None:
                raise HTTPException(404, "This student record could not be found.")
            if revision != crud.student_revision(student):
                session.rollback()
                return render_form(
                    request, session, options, values, student_id=student_id, revision=revision,
                    message="This record changed while the form was open. Open the edit form again to review the latest values.",
                    status_code=409,
                )
            for field, value in data.items():
                setattr(student, field, value)

        session.flush()
        saved_id = student.student_id
        session.commit()
    except IntegrityError:
        session.rollback()
        return render_form(
            request, session, crud.form_options(session), values, student_id=student_id, revision=revision,
            message="SQL Server rejected the change. Review the available options and try again.",
            status_code=409,
        )
    except DBAPIError as exc:
        session.rollback()
        if not re.search(r"\((?:229|230)\)", str(exc.orig)):
            raise
        return render_form(
            request, session, options, values, student_id=student_id, revision=revision,
            message="The configured SQL Server login does not have permission to save student records.",
            status_code=403,
        )

    return RedirectResponse(
        request.url_for("student_edit", student_id=saved_id).include_query_params(
            saved="created" if created else "updated"
        ),
        status_code=303,
    )


@router.post("/new")
def student_create(request: Request, session: Database, admin: AdminUser, form: FormInput):
    return save_student(request, session, form)


@router.post("/{student_id}/edit")
def student_update(request: Request, session: Database, admin: AdminUser, student_id: StudentId, form: FormInput):
    return save_student(request, session, form, student_id)


@router.get("/{student_id}/delete")
def confirm_student_delete(request: Request, session: Database, admin: AdminUser, student_id: StudentId):
    student = student_or_404(session, student_id)
    return render(
        request, "confirm_delete.html", section="students", record_type="student",
        record_label=f"{student.first_name} {student.last_name} (ID {student_id})",
        action=request.url_for("student_delete", student_id=student_id),
        cancel=request.url_for("student_edit", student_id=student_id), revision=crud.student_revision(student),
    )


@router.post("/{student_id}/delete")
def student_delete(request: Request, session: Database, admin: AdminUser, student_id: StudentId, form: FormInput):
    if form.get("confirm") != "yes":
        raise HTTPException(400, "Confirm deletion before continuing.")
    student = crud.lock_student(session, student_id)
    if student is None:
        raise HTTPException(404, "This student record could not be found.")
    if form.get("revision") != crud.student_revision(student):
        raise HTTPException(409, "This record changed. Review it and confirm deletion again.")
    try:
        session.delete(student)
        session.commit()
    except IntegrityError:
        session.rollback()
        return render_form(
            request, session, crud.form_options(session), crud.student_values(student),
            student_id=student_id, revision=crud.student_revision(student), status_code=409,
            message="This student has related records, such as course enrollments, and could not be deleted.",
        )
    return RedirectResponse(request.url_for("students_list").include_query_params(saved="deleted"), status_code=303)
