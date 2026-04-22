import argparse

from canvasapi import Canvas

from config import load_config
from display import display_all
from fetcher import fetch_courses
from models import CourseRecord


def _parse_assumption(spec: str, courses: list[CourseRecord]) -> tuple[int, int, float]:
    """
    Parses 'course:assignment=score' and resolves it against the fetched courses.
    Returns (course_id, assignment_id, raw_point_score).

    - course and assignment use case-insensitive substring matching and must match
      exactly one candidate (courses: any; assignments: ungraded only).
    - score may be 'N%' (percentage of points_possible) or a bare number (raw points).
    """
    if "=" not in spec:
        raise ValueError(f"missing '=' in {spec!r}")
    head, score_str = spec.rsplit("=", 1)
    if ":" not in head:
        raise ValueError(f"missing ':' in {spec!r}")
    course_key, assignment_key = head.split(":", 1)
    course_key = course_key.strip().lower()
    assignment_key = assignment_key.strip().lower()
    score_str = score_str.strip()

    course_matches = [c for c in courses if course_key in c.name.lower()]
    if not course_matches:
        raise ValueError(f"no course matched {course_key!r}")
    if len(course_matches) > 1:
        names = ", ".join(c.name for c in course_matches)
        raise ValueError(f"multiple courses matched {course_key!r}: {names}")
    course = course_matches[0]

    candidates = [
        a
        for g in course.groups
        for a in g.assignments
        if not a.is_graded and a.points_possible > 0
    ]
    name_matches = [a for a in candidates if assignment_key in a.name.lower()]
    if not name_matches:
        raise ValueError(
            f"no ungraded assignment in {course.name!r} matched {assignment_key!r}"
        )
    if len(name_matches) > 1:
        names = ", ".join(a.name for a in name_matches)
        raise ValueError(
            f"multiple ungraded assignments matched {assignment_key!r}: {names}"
        )
    assignment = name_matches[0]

    try:
        if score_str.endswith("%"):
            pct = float(score_str[:-1].strip())
            score = pct / 100.0 * assignment.points_possible
        else:
            score = float(score_str)
    except ValueError as e:
        raise ValueError(f"invalid score {score_str!r}: {e}") from e

    return course.id, assignment.id, score


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculate what-if grades and minimum scores needed for Canvas courses."
    )
    parser.add_argument(
        "--all-courses",
        action="store_true",
        default=False,
        help="Include all active courses instead of only favorited ones.",
    )
    parser.add_argument(
        "--assume",
        action="append",
        default=[],
        metavar="COURSE:ASSIGNMENT=SCORE",
        help=(
            "Pin a hypothetical score on an ungraded assignment and recompute "
            "minimums for the rest. SCORE can be a percentage ('69.9%%') or raw "
            "points ('69.9'). Course and assignment match by case-insensitive "
            "substring. Repeatable. Example: --assume 'calc:midterm exam 2=69.9%%'"
        ),
    )
    args = parser.parse_args()

    config = load_config()
    canvas = Canvas(config.api_url, config.api_token)

    scope = "all active" if args.all_courses else "favorited"
    print(f"Fetching {scope} courses... (target grade: {config.target_grade:.1f}%)\n")
    courses = fetch_courses(canvas, all_courses=args.all_courses)

    assumptions: dict[int, dict[int, float]] = {}
    for spec in args.assume:
        try:
            course_id, assignment_id, score = _parse_assumption(spec, courses)
        except ValueError as e:
            raise SystemExit(f"Error in --assume {spec!r}: {e}")
        assumptions.setdefault(course_id, {})[assignment_id] = score

    display_all(courses, config.target_grade, assumptions)


if __name__ == "__main__":
    main()
