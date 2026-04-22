from concurrent.futures import ThreadPoolExecutor, as_completed

from canvasapi import Canvas
from canvasapi.course import Course

from models import AssignmentRecord, CourseRecord, GroupRecord, GroupRules


def _get(obj: object, key: str, default: object = None) -> object:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _is_graded(submission: object) -> bool:
    state = _get(submission, "workflow_state")
    score = _get(submission, "score")
    return state == "graded" and score is not None


def fetch_courses(canvas: Canvas, *, all_courses: bool = False) -> list[CourseRecord]:
    """
    Fetches courses for the current user and returns CourseRecord objects
    with groups and assignments (including submission data) populated.

    Args:
        canvas: Authenticated Canvas API client.
        all_courses: If True, fetch all active courses; otherwise fetch only favorited courses.
    """
    raw_courses = canvas.get_courses(
        enrollment_state="active", include=["total_scores", "favorites"]
    )
    if not all_courses:
        raw_courses = (c for c in raw_courses if getattr(c, "is_favorite", False))

    valid = [
        (
            c,
            getattr(c, "grading_type", "points") or "points",
            bool(getattr(c, "apply_assignment_group_weights", False)),
        )
        for c in raw_courses
        if getattr(c, "name", None)
    ]

    courses: list[CourseRecord] = []
    with ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(
                _build_course_record, course, grading_type, is_weighted
            ): course
            for course, grading_type, is_weighted in valid
        }
        for future in as_completed(futures):
            course = futures[future]
            try:
                courses.append(future.result())
            except Exception as e:
                print(f"  Warning: could not fetch data for '{course.name}': {e}")

    return courses


def _build_course_record(
    course: Course, grading_type: str, is_weighted: bool
) -> CourseRecord:
    # Fetch assignment groups (includes assignment IDs and group weights)
    raw_groups = list(course.get_assignment_groups(include=["assignments"]))

    # Fetch all assignments with current user's submission in one call
    raw_assignments = list(course.get_assignments(include=["submission"]))

    # Build assignment lookup by ID
    assignment_map: dict[int, object] = {a.id: a for a in raw_assignments}

    groups: list[GroupRecord] = []
    for raw_group in raw_groups:
        weight = getattr(raw_group, "group_weight", None)
        group_assignment_stubs = getattr(raw_group, "assignments", []) or []

        assignments: list[AssignmentRecord] = []
        for stub in group_assignment_stubs:
            stub_id = _get(stub, "id")
            if stub_id is None:
                continue

            full = assignment_map.get(stub_id)
            if full is None:
                continue

            # Skip assignments that don't count toward grade
            if getattr(full, "omit_from_final_grade", False):
                continue
            submission_types = getattr(full, "submission_types", []) or []
            if "not_graded" in submission_types:
                continue

            points_possible = float(getattr(full, "points_possible", 0) or 0)
            submission = getattr(full, "submission", None)
            score: float | None = None
            graded = False

            if submission is not None:
                raw_score = _get(submission, "score")
                if _is_graded(submission) and raw_score is not None:
                    score = float(raw_score)  # type: ignore[arg-type]
                    graded = True

            assignments.append(
                AssignmentRecord(
                    id=stub_id,
                    name=str(getattr(full, "name", f"Assignment {stub_id}")),
                    group_id=raw_group.id,
                    points_possible=points_possible,
                    score=score,
                    is_graded=graded,
                )
            )

        raw_rules = getattr(raw_group, "rules", {}) or {}
        rules = GroupRules(
            drop_lowest=int(raw_rules.get("drop_lowest", 0) or 0),
            drop_highest=int(raw_rules.get("drop_highest", 0) or 0),
            never_drop=[int(x) for x in (raw_rules.get("never_drop") or [])],
        )

        groups.append(
            GroupRecord(
                id=raw_group.id,
                name=str(getattr(raw_group, "name", f"Group {raw_group.id}")),
                weight=float(weight) if weight is not None else None,
                assignments=assignments,
                rules=rules,
            )
        )

    return CourseRecord(
        id=course.id,
        name=str(course.name),
        is_weighted=is_weighted,
        grading_type=grading_type,
        groups=groups,
    )
