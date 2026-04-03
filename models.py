from dataclasses import dataclass, field


@dataclass
class AssignmentRecord:
    id: int
    name: str
    group_id: int
    points_possible: float
    score: float | None  # None = not yet graded
    is_graded: bool  # score is not None and workflow_state == 'graded'


@dataclass
class GroupRecord:
    id: int
    name: str
    weight: float | None  # None means non-weighted course; stored as e.g. 30.0 for 30%
    assignments: list[AssignmentRecord] = field(default_factory=list)


@dataclass
class CourseRecord:
    id: int
    name: str
    is_weighted: bool
    grading_type: str  # 'points', 'percent', 'letter_grade', 'gpa_scale', 'pass_fail'
    groups: list[GroupRecord] = field(default_factory=list)


@dataclass
class NeedScore:
    assignment_name: str
    points_possible: float
    min_score_needed: float  # absolute points
    min_pct_needed: float    # as percentage (0-100)
    is_impossible: bool      # even 100% won't reach target
    max_achievable: float | None  # grade if this assignment scores 100%
