from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import ValidationError
from sqlalchemy import false, func, or_, select
from sqlalchemy.exc import IntegrityError

from ..auth import AdminUser, CurrentUser
from ..crud import search_pattern
from ..models import Course, CourseEnrollment, CourseOffering, DegreeRequirement, Student
from ..preferences import get_preferences
from ..reference import REFERENCES, reference_input_types, reference_options
from ..schemas import SQL_INT_MAX, SQL_INT_MIN
from ..web import Database, FormInput, render


router = APIRouter(prefix="/catalog")
Code = Annotated[str, Query(max_length=11)]
Number = Annotated[int | None, Query(ge=9, le=1000)]


def get_reference(entity):
    if entity not in REFERENCES:
        raise HTTPException(404, "This management page could not be found.")
    return REFERENCES[entity]


def selected_record(session, reference, code, number, *, lock=False):
    key = (code, number) if len(reference.keys) == 2 else (code,)
    if any(value is None or value == "" for value in key):
        raise HTTPException(404, "Select a record first.")
    if reference.generated_id_label:
        try:
            record_id = int(code)
            if not SQL_INT_MIN <= record_id <= SQL_INT_MAX:
                raise ValueError
        except ValueError:
            raise HTTPException(400, f"Enter a valid {reference.generated_id_label.lower()}.") from None
        key = (record_id,)
    conditions = [getattr(reference.model, field) == value for field, value in zip(reference.keys, key)]
    statement = select(reference.model).where(*conditions)
    if lock:
        statement = statement.with_hint(reference.model, "WITH (UPDLOCK)", dialect_name="mssql")
    record = session.scalar(statement)
    if record is None:
        raise HTTPException(404, "This record could not be found.")
    return record


def reference_key(reference, record):
    return {"code": getattr(record, reference.keys[0])} | (
        {"number": getattr(record, reference.keys[1])} if len(reference.keys) == 2 else {}
    )


def show_reference(
    request, session, entity, reference, *, selected=None, q="", page=1, values=None,
    errors=None, message="", status_code=200,
):
    conditions = []
    keys = [getattr(reference.model, field) for field in reference.keys]
    if q:
        if reference.generated_id_label and q.isascii() and q.removeprefix("-").isdigit():
            record_id = int(q)
            if SQL_INT_MIN <= record_id <= SQL_INT_MAX:
                columns = (*keys, *reference.numeric_search)
                conditions.append(or_(*(column == record_id for column in columns)))
            else:
                conditions.append(false())
        else:
            pattern = search_pattern(q)
            conditions.append(or_(*(column.like(pattern, escape="!") for column in reference.search)))
    count = session.scalar(select(func.count()).select_from(reference.model).where(*conditions))
    page_size = get_preferences(request).page_size
    pages = max(1, (count + page_size - 1) // page_size)
    page = min(page, pages)
    if reference.generated_id_label:
        keys = [keys[0].desc()]
    statement = select(reference.model).where(*conditions).order_by(*keys)
    records = session.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    fields = reference.schema.model_fields
    input_types, steps = reference_input_types(reference)
    columns = {reference.keys[0]: reference.generated_id_label} if reference.generated_id_label else {}
    columns.update({name: field.title for name, field in fields.items()})
    if values is None:
        values = {field: getattr(selected, field) for field in fields} if selected is not None else {}
    notices = {"inserted": "Record inserted.", "updated": "Record updated.", "deleted": "Record deleted."}
    return render(
        request, "reference.html", section=entity, entity=entity, reference=reference,
        fields=fields, columns=columns, selected=reference_key(reference, selected) if selected is not None else None,
        rows=[(record, reference_key(reference, record)) for record in records],
        values=values, input_types=input_types, steps=steps,
        options=reference_options(session, reference) if request.state.current_user.role == "Admin" else {},
        errors=errors or {}, message=message,
        notice=notices.get(request.query_params.get("saved")), total=count, q=q, page=page, pages=pages,
        status_code=status_code,
    )


@router.get("/{entity}")
def reference_page(
    request: Request, session: Database, user: CurrentUser, entity: str,
    code: Code = "", number: Number = None,
    q: Annotated[str, Query(max_length=100)] = "", page: Annotated[int, Query(ge=1)] = 1,
):
    reference = get_reference(entity)
    selected = selected_record(session, reference, code, number) if code and user.role == "Admin" else None
    return show_reference(request, session, entity, reference, selected=selected, q=q.strip(), page=page)


def validate_relationships(session, reference, data):
    errors = {}
    for field, options in reference_options(session, reference).items():
        value = data[field]
        if value is not None and str(value).casefold() not in {str(key).casefold() for key, _ in options}:
            errors[field] = "Choose an available option."

    if reference.model in (CourseOffering, DegreeRequirement):
        course_key = (data["department_code"], data["course_number"])
        if "department_code" not in errors and session.get(Course, course_key) is None:
            errors["course_number"] = "Enter a course number from the selected department."
    elif reference.model is CourseEnrollment:
        if session.scalar(select(Student.student_id).where(Student.student_id == data["student_id"])) is None:
            errors["student_id"] = "Enter an existing student ID."
        if session.get(CourseOffering, data["course_offering_id"]) is None:
            errors["course_offering_id"] = "Enter an existing course offering ID."
    return errors


@router.post("/{entity}")
def save_reference(
    request: Request, session: Database, admin: AdminUser, form: FormInput, entity: str,
    code: Code = "", number: Number = None,
):
    reference = get_reference(entity)
    selected = selected_record(session, reference, code, number, lock=True) if code else None
    values = {key: form[key] for key in reference.schema.model_fields if key in form}
    if selected is not None:
        values.update({field: getattr(selected, field) for field in reference.keys})
    try:
        data = reference.schema.model_validate(values).model_dump()
    except ValidationError as exc:
        errors = {item["loc"][0]: item["msg"].removeprefix("Value error, ") for item in exc.errors()}
        return show_reference(
            request, session, entity, reference, selected=selected, values=values, errors=errors, status_code=422,
        )
    errors = validate_relationships(session, reference, data)
    if errors:
        return show_reference(
            request, session, entity, reference, selected=selected, values=values, status_code=422, errors=errors,
        )

    record = selected if selected is not None else reference.model()
    for key, value in data.items():
        if selected is None or key not in reference.keys:
            setattr(record, key, value)
    session.add(record)
    try:
        session.flush()
        key = reference_key(reference, record)
        session.commit()
    except IntegrityError:
        session.rollback()
        return show_reference(
            request, session, entity, reference, selected=selected, values=values, status_code=409,
            message="The key already exists or SQL Server rejected a field value or relationship.",
        )
    return RedirectResponse(
        request.url_for("reference_page", entity=entity).include_query_params(
            **key, saved="updated" if selected is not None else "inserted",
        ),
        status_code=303,
    )


@router.get("/{entity}/delete")
def confirm_reference_delete(
    request: Request, session: Database, admin: AdminUser, entity: str, code: Code = "", number: Number = None,
):
    reference = get_reference(entity)
    record = selected_record(session, reference, code, number)
    key = reference_key(reference, record)
    return render(
        request, "confirm_delete.html", section=entity, record_type=reference.singular,
        record_label=" ".join(str(getattr(record, field)) for field in reference.keys),
        action=request.url_for("delete_reference", entity=entity).include_query_params(**key),
        cancel=request.url_for("reference_page", entity=entity).include_query_params(**key),
    )


@router.post("/{entity}/delete")
def delete_reference(
    request: Request, session: Database, admin: AdminUser, form: FormInput, entity: str,
    code: Code = "", number: Number = None,
):
    if form.get("confirm") != "yes":
        raise HTTPException(400, "Confirm deletion before continuing.")
    reference = get_reference(entity)
    record = selected_record(session, reference, code, number, lock=True)
    try:
        session.delete(record)
        session.commit()
    except IntegrityError:
        session.rollback()
        return show_reference(
            request, session, entity, reference, selected=record, status_code=409,
            message=f"This {reference.singular} is used by other records and could not be deleted.",
        )
    return RedirectResponse(
        request.url_for("reference_page", entity=entity).include_query_params(saved="deleted"), status_code=303,
    )
