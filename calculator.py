from models import AssignmentRecord, CourseRecord, GroupRecord, NeedScore


def _group_totals(group: GroupRecord) -> tuple[float, float]:
    """
    Returns (earned, possible) for a group after applying Canvas drop rules.

    - Assignments with points_possible == 0 are treated as pure bonus: their
      score is added to `earned` but they contribute nothing to `possible` and
      are never eligible for dropping.
    - drop_lowest / drop_highest are applied to the remaining graded items,
      excluding IDs in never_drop. We approximate Canvas by dropping the items
      with the lowest (or highest) score/points_possible ratio.
    """
    graded = [a for a in group.assignments if a.is_graded and a.score is not None]

    bonus = [a for a in graded if a.points_possible <= 0]
    scored = [a for a in graded if a.points_possible > 0]

    rules = group.rules
    never_drop = set(rules.never_drop)

    droppable = [a for a in scored if a.id not in never_drop]
    protected = [a for a in scored if a.id in never_drop]

    # Canvas won't drop past the point of leaving zero assignments in the group.
    max_droppable = max(0, len(droppable) - (1 if not protected else 0))
    n_low = min(rules.drop_lowest, max_droppable)
    n_high = min(rules.drop_highest, max(0, max_droppable - n_low))

    droppable.sort(key=lambda a: (a.score or 0.0) / a.points_possible)
    kept = droppable[n_low: len(droppable) - n_high] if n_high else droppable[n_low:]

    retained = kept + protected
    earned = sum((a.score or 0.0) for a in retained) + sum((a.score or 0.0) for a in bonus)
    possible = sum(a.points_possible for a in retained)
    return earned, possible


def _compute_weighted_grade(groups: list[GroupRecord]) -> float | None:
    """
    Returns current grade as a percentage (0-100), or None if nothing is graded.
    Matches Canvas behavior: re-normalizes weights of active groups (those with
    at least one graded assignment) to sum to 100%, and applies per-group
    drop rules.
    """
    total_active_weight = 0.0
    weighted_sum = 0.0

    for group in groups:
        if group.weight is None:
            continue
        earned, possible = _group_totals(group)
        if possible <= 0:
            continue
        group_score = earned / possible
        weight = group.weight / 100.0
        weighted_sum += weight * group_score
        total_active_weight += weight

    if total_active_weight == 0.0:
        return None

    return (weighted_sum / total_active_weight) * 100.0


def _compute_points_grade(groups: list[GroupRecord]) -> float | None:
    """
    Returns current grade as a percentage for points-based (non-weighted) courses.
    Applies per-group drop rules and pure-bonus (0-point) assignments.
    """
    total_earned = 0.0
    total_possible = 0.0
    for group in groups:
        earned, possible = _group_totals(group)
        total_earned += earned
        total_possible += possible
    if total_possible == 0.0:
        return None
    return (total_earned / total_possible) * 100.0


def compute_grade(course: CourseRecord) -> float | None:
    if course.is_weighted:
        return _compute_weighted_grade(course.groups)
    return _compute_points_grade(course.groups)


def _grade_with_score(
    course: CourseRecord, target_group_id: int, target_assignment_id: int, hypothetical_score: float
) -> float | None:
    """
    Returns the course grade as if the target assignment has hypothetical_score and is graded.
    Does not mutate the original course.
    """
    modified_groups = []
    for group in course.groups:
        new_assignments = []
        for a in group.assignments:
            if a.id == target_assignment_id and group.id == target_group_id:
                new_assignments.append(
                    AssignmentRecord(
                        id=a.id,
                        name=a.name,
                        group_id=a.group_id,
                        points_possible=a.points_possible,
                        score=hypothetical_score,
                        is_graded=True,
                    )
                )
            else:
                new_assignments.append(a)
        modified_groups.append(
            GroupRecord(id=group.id, name=group.name, weight=group.weight, assignments=new_assignments)
        )
    modified_course = CourseRecord(
        id=course.id,
        name=course.name,
        is_weighted=course.is_weighted,
        grading_type=course.grading_type,
        groups=modified_groups,
    )
    return compute_grade(modified_course)


def min_score_needed(
    course: CourseRecord,
    target_group_id: int,
    assignment: AssignmentRecord,
    target_grade: float,
) -> NeedScore:
    """
    Computes the minimum score needed on an ungraded assignment to achieve target_grade.
    Conservative: assumes all other ungraded assignments score 0.
    """
    if assignment.points_possible <= 0:
        return NeedScore(
            assignment_name=assignment.name,
            points_possible=assignment.points_possible,
            min_score_needed=0.0,
            min_pct_needed=0.0,
            is_impossible=True,
            max_achievable=None,
        )

    g0 = _grade_with_score(course, target_group_id, assignment.id, 0.0) or 0.0
    g_max = _grade_with_score(course, target_group_id, assignment.id, assignment.points_possible) or 0.0

    grade_range = g_max - g0

    if abs(grade_range) < 1e-9:
        # Assignment has zero marginal effect
        is_impossible = g0 < target_grade
        return NeedScore(
            assignment_name=assignment.name,
            points_possible=assignment.points_possible,
            min_score_needed=0.0,
            min_pct_needed=0.0,
            is_impossible=is_impossible,
            max_achievable=g_max,
        )

    min_score = (target_grade - g0) / grade_range * assignment.points_possible
    is_impossible = min_score > assignment.points_possible
    min_score_clamped = max(0.0, min_score)
    min_pct = min_score_clamped / assignment.points_possible * 100.0

    return NeedScore(
        assignment_name=assignment.name,
        points_possible=assignment.points_possible,
        min_score_needed=min_score_clamped,
        min_pct_needed=min_pct,
        is_impossible=is_impossible,
        max_achievable=g_max,
    )


def compute_max_achievable(course: CourseRecord) -> float | None:
    """Returns the maximum possible grade if all ungraded assignments score 100%."""
    modified_groups = []
    for group in course.groups:
        new_assignments = []
        for a in group.assignments:
            if not a.is_graded and a.points_possible > 0:
                new_assignments.append(
                    AssignmentRecord(
                        id=a.id,
                        name=a.name,
                        group_id=a.group_id,
                        points_possible=a.points_possible,
                        score=a.points_possible,
                        is_graded=True,
                    )
                )
            else:
                new_assignments.append(a)
        modified_groups.append(
            GroupRecord(id=group.id, name=group.name, weight=group.weight, assignments=new_assignments)
        )
    modified_course = CourseRecord(
        id=course.id,
        name=course.name,
        is_weighted=course.is_weighted,
        grading_type=course.grading_type,
        groups=modified_groups,
    )
    return compute_grade(modified_course)


def compute_all_needs(course: CourseRecord, target_grade: float) -> list[tuple[NeedScore, str]]:
    """
    Returns list of (NeedScore, group_name) for every ungraded assignment in the course.
    """
    results = []
    for group in course.groups:
        for assignment in group.assignments:
            if not assignment.is_graded and assignment.points_possible > 0:
                need = min_score_needed(course, group.id, assignment, target_grade)
                results.append((need, group.name))
    return results
