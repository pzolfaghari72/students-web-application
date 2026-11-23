from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import String, cast, select

from .crud import term_options
from .models import (
    AcademicSession, Applicant, ClassStanding, Course, CourseEnrollment, CourseOffering,
    Degree, DegreeLevel, DegreeRequirement, DegreeType, Department, Grade, Term,
)
from .schemas import SqlInt


class ReferenceInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("*")
    @classmethod
    def validate_text(cls, value):
        if isinstance(value, str):
            try:
                value.encode("cp1252")
            except UnicodeEncodeError:
                raise ValueError("This field contains characters the database cannot store.") from None
        return value


class CourseKeyInput(ReferenceInput):
    department_code: str = Field(title="Department", min_length=1, max_length=2)
    course_number: int = Field(title="Course number", ge=9, le=1000)


class CourseInput(CourseKeyInput):
    title: str = Field(title="Title", min_length=1, max_length=64)
    description: str = Field(title="Description", default="", max_length=512)
    credits: Decimal = Field(title="Credits", ge=-99.9, le=99.9, max_digits=3, decimal_places=1)
    maximum_section_size: SqlInt | None = Field(title="Maximum section size", default=None)

    @field_validator("maximum_section_size", mode="before")
    @classmethod
    def optional_size(cls, value):
        return None if value == "" else value


class TermInput(ReferenceInput):
    code: str = Field(title="Term code", min_length=1, max_length=6)
    session_code: str = Field(title="Session", min_length=1, max_length=2)
    year: int = Field(title="Year", ge=1990, le=2050)


class DepartmentInput(ReferenceInput):
    code: str = Field(title="Department code", min_length=1, max_length=2)
    name: str = Field(title="Department name", min_length=1, max_length=25)


class DegreeLevelInput(ReferenceInput):
    code: str = Field(title="Degree level code", min_length=1, max_length=1)
    name: str = Field(title="Degree level name", min_length=1, max_length=20)


class DegreeTypeInput(ReferenceInput):
    code: str = Field(title="Degree type code", min_length=1, max_length=3)
    name: str = Field(title="Degree type name", min_length=1, max_length=25)
    degree_level_code: str = Field(title="Degree level", min_length=1, max_length=1)


class DegreeInput(ReferenceInput):
    name: str = Field(title="Degree name", min_length=1, max_length=64)
    department_code: str = Field(title="Department", min_length=1, max_length=2)
    degree_type_code: str = Field(title="Degree type", min_length=1, max_length=3)


class ClassStandingInput(ReferenceInput):
    code: str = Field(title="Class standing code", min_length=1, max_length=2)
    name: str = Field(title="Class standing name", min_length=1, max_length=25)
    degree_level_code: str = Field(title="Degree level", min_length=1, max_length=1)
    required_credits: SqlInt = Field(title="Required credits")


class AcademicSessionInput(ReferenceInput):
    code: str = Field(title="Session code", min_length=1, max_length=2)
    name: str = Field(title="Session name", min_length=1, max_length=10)


class GradeInput(ReferenceInput):
    grade: str = Field(title="Grade", min_length=1, max_length=1)
    points: Decimal | None = Field(
        title="Points", default=None, ge=-9.9, le=9.9, max_digits=2, decimal_places=1,
    )
    include_in_gpa: bool = Field(title="Include in GPA", default=True)

    @field_validator("points", mode="before")
    @classmethod
    def optional_points(cls, value):
        return None if value == "" else value


class CourseEnrollmentInput(ReferenceInput):
    course_offering_id: SqlInt = Field(title="Course offering ID")
    student_id: SqlInt = Field(title="Student ID")
    grade: str | None = Field(title="Grade", default=None, min_length=1, max_length=1)

    @field_validator("grade", mode="before")
    @classmethod
    def optional_grade(cls, value):
        return None if value == "" else value


class CourseOfferingInput(CourseKeyInput):
    term_code: str = Field(title="Term", min_length=1, max_length=6)
    section: SqlInt = Field(title="Section")
    capacity: int = Field(title="Capacity", ge=1, le=999)


class DegreeRequirementInput(CourseKeyInput):
    degree_id: SqlInt = Field(title="Degree")
    class_standing_code: str = Field(title="Class standing", min_length=1, max_length=2)
    session_code: str = Field(title="Session", min_length=1, max_length=2)


class ApplicantInput(ReferenceInput):
    first_name: str = Field(title="First name", min_length=1, max_length=40)
    middle_name: str = Field(title="Middle name", default="", max_length=40)
    last_name: str = Field(title="Last name", min_length=1, max_length=40)
    gender: Literal["F", "M"] = Field(title="Gender")
    date_of_birth: date = Field(title="Date of birth")
    email: str = Field(title="Email address", min_length=1, max_length=80, pattern=r"^[^@\s]+@[^@\s]+$")
    telephone: str = Field(title="Telephone", min_length=1, max_length=20)
    street_address: str = Field(title="Street address", min_length=1, max_length=50)
    city: str = Field(title="City", min_length=1, max_length=30)
    state: str = Field(title="State", min_length=1, max_length=2)
    zip_code: str = Field(title="ZIP code", min_length=1, max_length=5)
    application_received_date: date = Field(title="Application received")
    entry_term: str = Field(title="Entry term", min_length=1, max_length=6)
    application_type: str = Field(title="Application type code", min_length=1, max_length=1)
    application_status: str = Field(title="Application status code", default="N", min_length=1, max_length=1)
    gpa: Decimal | None = Field(title="GPA", default=None, ge=0, le=4, max_digits=3, decimal_places=2)
    sat_math_score: int | None = Field(title="SAT math", default=None, ge=200, le=800)
    sat_reading_score: int | None = Field(title="SAT reading", default=None, ge=200, le=800)
    sat_writing_score: int | None = Field(title="SAT writing", default=None, ge=200, le=800)
    essay_score: SqlInt | None = Field(title="Essay score", default=None)
    admission_points: float | None = Field(title="Admission points", default=None, allow_inf_nan=False)

    @field_validator(
        "gpa", "sat_math_score", "sat_reading_score", "sat_writing_score",
        "essay_score", "admission_points", mode="before",
    )
    @classmethod
    def optional_scores(cls, value):
        return None if value == "" else value

    @field_validator("application_status", mode="before")
    @classmethod
    def blank_status(cls, value):
        return "N" if value == "" else value


@dataclass(frozen=True)
class Reference:
    title: str
    singular: str
    model: type
    schema: type[ReferenceInput]
    keys: tuple[str, ...]
    search: tuple
    lookups: tuple[tuple, ...] = ()
    generated_id_label: str | None = None
    numeric_search: tuple = ()
    search_placeholder: str = ""


DEPARTMENT_LOOKUP = ("department_code", Department.code, Department.name)
DEGREE_LEVEL_LOOKUP = ("degree_level_code", DegreeLevel.code, DegreeLevel.name)
SESSION_LOOKUP = ("session_code", AcademicSession.code, AcademicSession.name)


REFERENCES = {
    "applicants": Reference(
        "Applicants", "applicant", Applicant, ApplicantInput, ("applicant_id",),
        (Applicant.first_name, Applicant.last_name, Applicant.email, Applicant.entry_term),
        generated_id_label="Applicant ID",
    ),
    "courses": Reference(
        "Courses", "course", Course, CourseInput, ("department_code", "course_number"),
        (Course.department_code, cast(Course.course_number, String(11)), Course.title, Course.description),
        (DEPARTMENT_LOOKUP,),
    ),
    "terms": Reference(
        "Terms", "term", Term, TermInput, ("code",), (Term.code, Term.session_code, cast(Term.year, String(11))),
        (SESSION_LOOKUP,),
    ),
    "departments": Reference(
        "Departments", "department", Department, DepartmentInput, ("code",), (Department.code, Department.name),
    ),
    "class-standings": Reference(
        "Class Standings", "class standing", ClassStanding, ClassStandingInput, ("code",),
        (ClassStanding.code, ClassStanding.name, ClassStanding.degree_level_code), (DEGREE_LEVEL_LOOKUP,),
    ),
    "course-enrollments": Reference(
        "Course Enrollments", "enrollment", CourseEnrollment, CourseEnrollmentInput, ("course_enrollment_id",),
        (CourseEnrollment.grade,), (("grade", Grade.grade, Grade.grade),),
        generated_id_label="Enrollment ID",
        numeric_search=(CourseEnrollment.student_id, CourseEnrollment.course_offering_id),
        search_placeholder="Enrollment ID, student ID, offering ID, or grade",
    ),
    "course-offerings": Reference(
        "Course Offerings", "course offering", CourseOffering, CourseOfferingInput, ("course_offering_id",),
        (CourseOffering.department_code, CourseOffering.term_code),
        (DEPARTMENT_LOOKUP, ("term_code", Term.code, Term.code)),
        generated_id_label="Offering ID",
        numeric_search=(CourseOffering.course_number,),
        search_placeholder="Offering ID, course number, department, or term",
    ),
    "degree-levels": Reference(
        "Degree Levels", "degree level", DegreeLevel, DegreeLevelInput, ("code",),
        (DegreeLevel.code, DegreeLevel.name),
    ),
    "degree-requirements": Reference(
        "Degree Requirements", "degree requirement", DegreeRequirement, DegreeRequirementInput, ("requirement_id",),
        (DegreeRequirement.department_code, DegreeRequirement.class_standing_code, DegreeRequirement.session_code),
        (
            DEPARTMENT_LOOKUP, ("degree_id", Degree.degree_id, Degree.name),
            ("class_standing_code", ClassStanding.code, ClassStanding.name), SESSION_LOOKUP,
        ),
        generated_id_label="Requirement ID",
        numeric_search=(DegreeRequirement.degree_id, DegreeRequirement.course_number),
        search_placeholder="Requirement ID, degree ID, course number, department, standing, or session",
    ),
    "degrees": Reference(
        "Degrees", "degree", Degree, DegreeInput, ("degree_id",),
        (Degree.name, Degree.department_code, Degree.degree_type_code),
        (DEPARTMENT_LOOKUP, ("degree_type_code", DegreeType.code, DegreeType.name)),
        generated_id_label="Degree ID",
    ),
    "degree-types": Reference(
        "Degree Types", "degree type", DegreeType, DegreeTypeInput, ("code",),
        (DegreeType.code, DegreeType.name, DegreeType.degree_level_code), (DEGREE_LEVEL_LOOKUP,),
    ),
    "grades": Reference(
        "Grades", "grade", Grade, GradeInput, ("grade",), (Grade.grade,),
    ),
    "sessions": Reference(
        "Sessions", "session", AcademicSession, AcademicSessionInput, ("code",),
        (AcademicSession.code, AcademicSession.name),
    ),
}


def reference_options(session, reference):
    if reference.model is Applicant:
        return {
            "gender": [("F", "Female"), ("M", "Male")],
            "entry_term": [(code, code) for code in term_options(session)],
        }
    options = {}
    for field, code, label in reference.lookups:
        if code is label:
            options[field] = [(value, value) for value in session.scalars(select(code).order_by(code))]
        else:
            rows = session.execute(select(code, label).order_by(label, code))
            options[field] = [(key, f"{key} — {value}") for key, value in rows]
    if reference.model is Grade:
        options["include_in_gpa"] = [(True, "Yes"), (False, "No")]
    return options


def reference_input_types(reference):
    types = {}
    steps = {}
    for name in reference.schema.model_fields:
        column_type = getattr(reference.model, name).type
        python_type = column_type.python_type
        if python_type in (int, float, Decimal):
            types[name] = "number"
            if python_type is Decimal:
                steps[name] = str(Decimal(1).scaleb(-column_type.scale))
            elif python_type is float:
                steps[name] = "any"
        elif python_type is date:
            types[name] = "date"
        else:
            types[name] = {"email": "email", "telephone": "tel"}.get(name, "text")
    return types, steps
