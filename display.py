from calculator import (
    apply_assumptions,
    compute_all_needs,
    compute_grade,
    compute_max_achievable,
    is_course_completed,
)
from models import CourseRecord, NeedScore

_BAR = "─" * 52


def display_course(
    course: CourseRecord,
    target_grade: float,
    assumed_scores: dict[int, float] | None = None,
) -> None:
    print(_BAR)

    current_grade = compute_grade(course)
    grading_label = "Weighted Groups" if course.is_weighted else "Points-based"

    if course.grading_type == "pass_fail":
        print(f"  {course.name}")
        print(f"  Pass/Fail course — grade calculation not applicable")
        print()
        return

    if current_grade is None:
        grade_str = "No grades yet"
        target_str = f"[target: {target_grade:.1f}%]"
    else:
        grade_str = f"{current_grade:.1f}%"
        if current_grade >= target_grade:
            target_str = f"[target: {target_grade:.1f}% ✓]"
        else:
            target_str = f"[target: {target_grade:.1f}%]"

    print(f"  {course.name}")
    print(f"  Current Grade: {grade_str}  {target_str}")
    print(f"  Grading: {grading_label}")
    print()

    # Group summary
    if course.groups:
        print("  Groups:")
        for group in course.groups:
            graded_count = sum(1 for a in group.assignments if a.is_graded)
            total_count = len(group.assignments)
            graded_pts = sum(
                a.score
                for a in group.assignments
                if a.is_graded and a.score is not None
            )
            possible_pts = sum(
                a.points_possible
                for a in group.assignments
                if a.is_graded and a.points_possible > 0
            )

            if graded_count > 0 and possible_pts > 0:
                group_pct = f"{graded_pts / possible_pts * 100:.1f}%"
            else:
                group_pct = "—"

            if course.is_weighted and group.weight is not None:
                weight_str = f"({group.weight:.0f}%)"
            else:
                weight_str = "      "

            name_col = f"{group.name[:24]:<24}"
            print(
                f"    {name_col} {weight_str:>6}  {group_pct:>6}  [{graded_count}/{total_count} graded]"
            )
        print()

    # What you need
    needs = compute_all_needs(course, target_grade)

    if not needs:
        if current_grade is not None and current_grade >= target_grade:
            print("  All assignments graded — target already achieved!")
        else:
            print("  No ungraded assignments found.")
        print()
        return

    # Separate into: already covered, needs work, impossible
    already_covered = [
        (n, g) for n, g in needs if not n.is_impossible and n.min_score_needed <= 0
    ]
    needs_work = [
        (n, g) for n, g in needs if not n.is_impossible and n.min_score_needed > 0
    ]
    impossible = [(n, g) for n, g in needs if n.is_impossible]

    # Only show impossible entries when there's no achievable path — otherwise they're noise.
    # If needs_work items exist, the target is reachable and impossible entries are irrelevant.
    if needs_work:
        print(
            f"  What you need (assuming other ungraded assignments maintain current averages):"
        )
        for need, group_name in needs_work:
            _print_need_row(need, group_name)
    elif impossible:
        # No achievable path — check if target is truly unreachable even with all 100%
        max_grade = compute_max_achievable(course)
        if max_grade is not None and max_grade < target_grade:
            print(f"  Target not achievable — max possible grade: {max_grade:.1f}%")
        else:
            # Target is reachable in aggregate but no single assignment can get you there alone
            print(
                f"  What you need (assuming other ungraded assignments maintain current averages):"
            )
            for need, group_name in impossible:
                _print_impossible_row(need, group_name)

    if already_covered:
        print(f"  Already on track (target met even if these score 0):")
        for need, group_name in already_covered:
            print(
                f"    {need.assignment_name[:40]:<40}  {need.points_possible:.0f} pts  [any score]"
            )

    if not needs_work and not impossible:
        print("  (none — target already covered)")

    if assumed_scores:
        print()
        _display_assumptions(course, target_grade, assumed_scores)

    print()


def _display_assumptions(
    course: CourseRecord,
    target_grade: float,
    assumed_scores: dict[int, float],
) -> None:
    print("  With your assumptions:")
    for group in course.groups:
        for a in group.assignments:
            if a.id in assumed_scores:
                score = assumed_scores[a.id]
                pct = score / a.points_possible * 100 if a.points_possible > 0 else 0.0
                name = a.name[:40]
                print(
                    f"    {name:<40}  {score:.1f} / {a.points_possible:.0f} pts ({pct:.1f}%)"
                )

    modified = apply_assumptions(course, assumed_scores)
    new_grade = compute_grade(modified)
    grade_str = f"{new_grade:.1f}%" if new_grade is not None else "—"
    print(f"  Projected grade with these scores: {grade_str}")

    needs = compute_all_needs(modified, target_grade)
    if not needs:
        print("  No remaining ungraded assignments.")
        return

    needs_work = [
        (n, g) for n, g in needs if not n.is_impossible and n.min_score_needed > 0
    ]
    already_covered = [
        (n, g) for n, g in needs if not n.is_impossible and n.min_score_needed <= 0
    ]
    impossible = [(n, g) for n, g in needs if n.is_impossible]

    if needs_work:
        print("  Recomputed needs:")
        for need, group_name in needs_work:
            _print_need_row(need, group_name)
    elif impossible:
        max_grade = compute_max_achievable(modified)
        if max_grade is not None and max_grade < target_grade:
            print(f"  Target no longer achievable — max possible: {max_grade:.1f}%")
        else:
            print("  Recomputed needs:")
            for need, group_name in impossible:
                _print_impossible_row(need, group_name)

    if already_covered:
        print("  Already on track:")
        for need, _group_name in already_covered:
            print(
                f"    {need.assignment_name[:40]:<40}  {need.points_possible:.0f} pts  [any score]"
            )


def _print_need_row(need: NeedScore, _group_name: str) -> None:
    name = need.assignment_name[:40]
    pts = need.points_possible
    min_pts = need.min_score_needed
    min_pct = need.min_pct_needed
    print(f"    {name:<40}  {pts:.0f} pts  →  need {min_pts:.1f} pts ({min_pct:.1f}%)")


def _print_impossible_row(need: NeedScore, _group_name: str) -> None:
    name = need.assignment_name[:40]
    pts = need.points_possible
    max_g = f"{need.max_achievable:.1f}%" if need.max_achievable is not None else "?"
    print(f"    [✗] {name:<36}  {pts:.0f} pts  →  IMPOSSIBLE (max achievable: {max_g})")


def display_all(
    courses: list[CourseRecord],
    target_grade: float,
    assumptions: dict[int, dict[int, float]] | None = None,
    show_completed: bool = False,
) -> None:
    if not courses:
        print("No active courses found.")
        return
    assumptions = assumptions or {}
    courses_to_show = courses if show_completed else [
        c for c in courses if not is_course_completed(c, target_grade)
    ]
    for course in courses_to_show:
        display_course(course, target_grade, assumptions.get(course.id))
    print(_BAR)
