from collections import Counter

from sqlalchemy import String, cast, func, literal, select, union_all
from sqlalchemy.orm import Session

from .crud import STATUS_LABELS, status_label, student_conditions
from .models import Degree, Student, Term


STATUS_TONES = {"A": "active", "G": "graduated", "W": "withdrawn"}


def dashboard_facets(session: Session, *, query: str, status: str, degree_id: int | None, term: str):
    dimensions = {
        "degree": (Student.degree_id, student_conditions(query, status, None, term)),
        "term": (Student.enrollment_term, student_conditions(query, status, degree_id)),
        "status": (Student.student_status, student_conditions(query, "", degree_id, term)),
    }
    statements = [
        select(literal(name), cast(column, String(11)), func.count_big(Student.student_id))
        .where(*conditions)
        .group_by(column)
        for name, (column, conditions) in dimensions.items()
    ]
    facets = {name: Counter() for name in dimensions}
    for name, value, count in session.execute(union_all(*statements)):
        facets[name][value.upper()] += count

    for counts in facets.values():
        counts[""] = sum(counts.values())
    return facets


def status_breakdown(session: Session, conditions):
    statement = (
        select(Student.student_status, func.count_big(Student.student_id))
        .where(*conditions)
        .group_by(Student.student_status)
    )
    by_code = Counter()
    for code, count in session.execute(statement):
        by_code[code.upper()] += count

    total = sum(by_code.values())
    counts = {
        "total": total,
        "active": by_code["A"],
        "graduated": by_code["G"],
        "withdrawn": by_code["W"],
    }
    slices = []
    stops = []
    cumulative = 0
    for code in (*STATUS_LABELS, *sorted(by_code.keys() - STATUS_LABELS.keys())):
        value = by_code[code]
        if not value:
            continue
        tone = STATUS_TONES.get(code, "other")
        start = cumulative / total * 100
        cumulative += value
        end = cumulative / total * 100
        stops.append(f"var(--chart-{tone}) {start:.3f}% {end:.3f}%")
        slices.append({
            "code": code, "label": status_label(code), "count": value,
            "share": round(value / total * 100, 1), "tone": tone,
        })
    return counts, slices, ", ".join(stops)


def enrollment_trend(session: Session, conditions):
    statement = (
        select(Term.year, func.count_big(Student.student_id))
        .join(Student, Student.enrollment_term == Term.code)
        .where(*conditions)
        .group_by(Term.year)
        .order_by(Term.year)
    )
    years = session.execute(statement).all()
    if not years:
        return [], []

    spacing = (max(count for _, count in years) + 3) // 4
    magnitude = 10 ** (len(str(spacing)) - 1)
    step = next(multiplier * magnitude for multiplier in (1, 2, 5, 10)
                if multiplier * magnitude >= spacing)
    limit = 4 * step
    bars = [{"year": year, "count": count, "height": count / limit * 100} for year, count in years]
    return bars, range(limit, -1, -step)


def dashboard_insights(session: Session, *, query: str, status: str, degree_id: int | None, term: str):
    conditions = student_conditions(query, status, degree_id, term)
    counts, statuses, ring = status_breakdown(session, conditions)
    trend, ticks = enrollment_trend(session, conditions)
    count = func.count_big(Student.student_id).label("student_count")
    degree_rows = session.execute(
        select(Degree.degree_id, Degree.name, count)
        .join(Student, Student.degree_id == Degree.degree_id)
        .where(*conditions)
        .group_by(Degree.degree_id, Degree.name)
        .order_by(count.desc(), Degree.name, Degree.degree_id)
        .limit(6)
    ).all()
    leading_degree = degree_rows[0].student_count if degree_rows else 1
    students = session.execute(
        select(
            Student.student_id, Student.first_name, Student.last_name, Student.student_status,
            Degree.name.label("degree_name"),
        )
        .outerjoin(Degree, Student.degree_id == Degree.degree_id)
        .where(*conditions)
        .order_by(Student.student_id.desc())
        .limit(6)
    ).all()
    return {
        "counts": counts, "status_slices": statuses, "status_ring": ring,
        "trend": trend, "trend_ticks": ticks, "students": students,
        "top_degrees": [
            {"id": degree_id, "name": name, "count": value, "width": value / leading_degree * 100}
            for degree_id, name, value in degree_rows
        ],
    }
