from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, ForeignKeyConstraint, Identity,
    Integer, LargeBinary, MetaData, Numeric, String, Unicode, UniqueConstraint, case, text,
)
from sqlalchemy.dialects.mssql import DATETIME2, VARBINARY
from sqlalchemy.orm import DeclarativeBase, Mapped, column_property, mapped_column


class Base(DeclarativeBase):
    metadata = MetaData(schema="dbo")


class User(Base):
    __tablename__ = "Users"
    __table_args__ = (
        UniqueConstraint("Username", name="uq_users_username"),
        CheckConstraint("Role IN ('Admin', 'User')", name="ck_users_role"),
        CheckConstraint(
            "(SessionHash IS NULL AND SessionExpiresAt IS NULL) OR "
            "(SessionHash IS NOT NULL AND SessionExpiresAt IS NOT NULL)",
            name="ck_users_session",
        ),
    )

    user_id: Mapped[int] = mapped_column("UserId", Integer, Identity(), primary_key=True)
    username: Mapped[str] = mapped_column("Username", String(64))
    password_hash: Mapped[str] = mapped_column("PasswordHash", String(255), deferred=True)
    first_name: Mapped[str] = mapped_column("FirstName", Unicode(64))
    last_name: Mapped[str] = mapped_column("LastName", Unicode(64))
    email: Mapped[str | None] = mapped_column("Email", Unicode(254))
    role: Mapped[str] = mapped_column("Role", String(5))
    is_active: Mapped[bool] = mapped_column("IsActive", Boolean, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(
        "CreatedAt", DateTime().with_variant(DATETIME2(0), "mssql")
    )
    profile_picture: Mapped[bytes | None] = mapped_column(
        "ProfilePicture", LargeBinary().with_variant(VARBINARY(None), "mssql"), deferred=True
    )
    session_hash: Mapped[str | None] = mapped_column("SessionHash", String(64))
    session_expires_at: Mapped[datetime | None] = mapped_column(
        "SessionExpiresAt", DateTime().with_variant(DATETIME2(0), "mssql")
    )
    has_picture: Mapped[bool] = column_property(
        case((profile_picture.is_not(None), True), else_=False)
    )


class Student(Base):
    __tablename__ = "Students"

    student_id: Mapped[int] = mapped_column("StudentId", Integer, Identity(10000, 1), primary_key=True)
    first_name: Mapped[str] = mapped_column("FirstName", String(40))
    middle_name: Mapped[str] = mapped_column("MiddleName", String(40))
    last_name: Mapped[str] = mapped_column("LastName", String(40))
    gender: Mapped[str] = mapped_column("Gender", String(1))
    street_address: Mapped[str] = mapped_column("StreetAddress", String(50))
    city: Mapped[str] = mapped_column("City", String(30))
    state: Mapped[str] = mapped_column("State", String(2))
    zip_code: Mapped[str] = mapped_column("ZipCode", String(5))
    telephone: Mapped[str] = mapped_column("Telephone", String(20))
    email: Mapped[str] = mapped_column("email", String(80))
    date_of_birth: Mapped[date] = mapped_column("DateOfBirth", Date)
    degree_id: Mapped[int] = mapped_column("DegreePursued", ForeignKey("dbo.Degrees.DegreeId"))
    class_standing_code: Mapped[str | None] = mapped_column(
        "ClassStandingCode", ForeignKey("dbo.ClassStandings.ClassStandingCode")
    )
    student_status: Mapped[str] = mapped_column("StudentStatus", String(1))
    enrollment_term: Mapped[str] = mapped_column("EnrollmentTerm", ForeignKey("dbo.Terms.TermCode"))


class Applicant(Base):
    __tablename__ = "Applicants"
    __table_args__ = (
        CheckConstraint("Gender IN ('F', 'M')", name="ck_applications_gender"),
        CheckConstraint("Gpa BETWEEN 0.0 AND 4.0", name="ck_applications_gpa"),
        CheckConstraint("SatMathScore BETWEEN 200 AND 800", name="ck_appls_sat_math_score"),
        CheckConstraint("SatReadingScore BETWEEN 200 AND 800", name="ck_appls_sat_reading_score"),
        CheckConstraint("SatWritingScore BETWEEN 200 AND 800", name="ck_appls_sat_writing_score"),
    )

    applicant_id: Mapped[int] = mapped_column("ApplicantId", Integer, Identity(), primary_key=True)
    first_name: Mapped[str] = mapped_column("FirstName", String(40))
    middle_name: Mapped[str] = mapped_column("MiddleName", String(40))
    last_name: Mapped[str] = mapped_column("LastName", String(40))
    gender: Mapped[str] = mapped_column("Gender", String(1))
    street_address: Mapped[str] = mapped_column("StreetAddress", String(50))
    city: Mapped[str] = mapped_column("City", String(30))
    state: Mapped[str] = mapped_column("State", String(2))
    zip_code: Mapped[str] = mapped_column("ZipCode", String(5))
    telephone: Mapped[str] = mapped_column("Telephone", String(20))
    email: Mapped[str] = mapped_column("Email", String(80))
    date_of_birth: Mapped[date] = mapped_column("DateOfBirth", Date)
    application_received_date: Mapped[date] = mapped_column("ApplicationReceivedDate", Date)
    entry_term: Mapped[str] = mapped_column("EntryTerm", ForeignKey("dbo.Terms.TermCode"))
    application_type: Mapped[str] = mapped_column("ApplicationType", String(1))
    gpa: Mapped[Decimal | None] = mapped_column("Gpa", Numeric(3, 2))
    sat_math_score: Mapped[int | None] = mapped_column("SatMathScore")
    sat_reading_score: Mapped[int | None] = mapped_column("SatReadingScore")
    sat_writing_score: Mapped[int | None] = mapped_column("SatWritingScore")
    essay_score: Mapped[int | None] = mapped_column("EssayScore")
    application_status: Mapped[str] = mapped_column("ApplicationStatus", String(1), server_default=text("'N'"))
    admission_points: Mapped[float | None] = mapped_column("AdmissionPoints", Float(53))


class Degree(Base):
    __tablename__ = "Degrees"

    degree_id: Mapped[int] = mapped_column("DegreeId", Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column("DegreeName", String(64))
    department_code: Mapped[str] = mapped_column("DepartmentCode", ForeignKey("dbo.Departments.DepartmentCode"))
    degree_type_code: Mapped[str] = mapped_column("DegreeTypeCode", ForeignKey("dbo.DegreeTypes.DegreeTypeCode"))


class DegreeLevel(Base):
    __tablename__ = "DegreeLevels"

    code: Mapped[str] = mapped_column("DegreeLevelCode", String(1), primary_key=True)
    name: Mapped[str] = mapped_column("DegreeLevelName", String(20))


class DegreeType(Base):
    __tablename__ = "DegreeTypes"

    code: Mapped[str] = mapped_column("DegreeTypeCode", String(3), primary_key=True)
    name: Mapped[str] = mapped_column("DegreeTypeName", String(25))
    degree_level_code: Mapped[str] = mapped_column("DegreeLevelCode", ForeignKey("dbo.DegreeLevels.DegreeLevelCode"))


class ClassStanding(Base):
    __tablename__ = "ClassStandings"

    code: Mapped[str] = mapped_column("ClassStandingCode", String(2), primary_key=True)
    name: Mapped[str] = mapped_column("ClassStandingName", String(25))
    degree_level_code: Mapped[str] = mapped_column("DegreeLevelCode", ForeignKey("dbo.DegreeLevels.DegreeLevelCode"))
    required_credits: Mapped[int] = mapped_column("RequiredCredits")


class Term(Base):
    __tablename__ = "Terms"
    __table_args__ = (CheckConstraint("Year BETWEEN 1990 AND 2050", name="ck_year"),)

    code: Mapped[str] = mapped_column("TermCode", String(6), primary_key=True)
    session_code: Mapped[str] = mapped_column("SessionCode", ForeignKey("dbo.Sessions.SessionCode"))
    year: Mapped[int] = mapped_column("Year")


class AcademicSession(Base):
    __tablename__ = "Sessions"

    code: Mapped[str] = mapped_column("SessionCode", String(2), primary_key=True)
    name: Mapped[str] = mapped_column("SessionName", String(10))


class Department(Base):
    __tablename__ = "Departments"

    code: Mapped[str] = mapped_column("DepartmentCode", String(2), primary_key=True)
    name: Mapped[str] = mapped_column("DepartmentName", String(25))


class Course(Base):
    __tablename__ = "Courses"
    __table_args__ = (CheckConstraint("CourseNumber BETWEEN 9 AND 1000", name="ck_CourseNumber"),)

    department_code: Mapped[str] = mapped_column(
        "DepartmentCode", ForeignKey("dbo.Departments.DepartmentCode"), primary_key=True
    )
    course_number: Mapped[int] = mapped_column("CourseNumber", primary_key=True)
    title: Mapped[str] = mapped_column("CourseTitle", String(64))
    description: Mapped[str] = mapped_column("CourseDescription", String(512))
    credits: Mapped[Decimal] = mapped_column("Credits", Numeric(3, 1))
    maximum_section_size: Mapped[int | None] = mapped_column("MaximumSectionSize")


class CourseOffering(Base):
    __tablename__ = "CourseOfferings"
    __table_args__ = (
        ForeignKeyConstraint(
            ("DepartmentCode", "CourseNumber"),
            ("dbo.Courses.DepartmentCode", "dbo.Courses.CourseNumber"),
            name="fk_CourseOfferings_Courses",
        ),
        CheckConstraint("Capacity BETWEEN 1 AND 999", name="ck_course_offerings_capacity"),
    )

    course_offering_id: Mapped[int] = mapped_column("CourseOfferingId", Integer, Identity(), primary_key=True)
    department_code: Mapped[str] = mapped_column("DepartmentCode", String(2))
    course_number: Mapped[int] = mapped_column("CourseNumber")
    term_code: Mapped[str] = mapped_column("TermCode", ForeignKey("dbo.Terms.TermCode"))
    section: Mapped[int] = mapped_column("Section")
    capacity: Mapped[int] = mapped_column("Capacity")


class Grade(Base):
    __tablename__ = "Grades"

    grade: Mapped[str] = mapped_column("Grade", String(1), primary_key=True)
    points: Mapped[Decimal | None] = mapped_column("Points", Numeric(2, 1))
    include_in_gpa: Mapped[bool] = mapped_column("IncludeInGpa", Boolean, server_default=text("1"))


class CourseEnrollment(Base):
    __tablename__ = "CourseEnrollments"

    course_enrollment_id: Mapped[int] = mapped_column(
        "CourseEnrollmentId", Integer, Identity(), primary_key=True
    )
    course_offering_id: Mapped[int] = mapped_column(
        "CourseOfferingId", ForeignKey("dbo.CourseOfferings.CourseOfferingId")
    )
    student_id: Mapped[int] = mapped_column("StudentId", ForeignKey("dbo.Students.StudentId"))
    grade: Mapped[str | None] = mapped_column("Grade", ForeignKey("dbo.Grades.Grade"))


class DegreeRequirement(Base):
    __tablename__ = "DegreeRequirements"
    __table_args__ = (
        ForeignKeyConstraint(
            ("DepartmentCode", "CourseNumber"),
            ("dbo.Courses.DepartmentCode", "dbo.Courses.CourseNumber"),
            name="fk_DegreeReqirements_Courses",
        ),
    )

    requirement_id: Mapped[int] = mapped_column("RequirementId", Integer, Identity(), primary_key=True)
    degree_id: Mapped[int] = mapped_column("DegreeId", ForeignKey("dbo.Degrees.DegreeId"))
    class_standing_code: Mapped[str] = mapped_column(
        "ClassStandingCode", ForeignKey("dbo.ClassStandings.ClassStandingCode")
    )
    session_code: Mapped[str] = mapped_column("SessionCode", ForeignKey("dbo.Sessions.SessionCode"))
    department_code: Mapped[str] = mapped_column("DepartmentCode", String(2))
    course_number: Mapped[int] = mapped_column("CourseNumber")
