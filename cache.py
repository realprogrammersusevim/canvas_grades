"""File-based JSON cache for Canvas API responses.

Courses are stored individually by ID so that fetching a subset of previously
cached courses (e.g. favorites vs. all) still results in a cache hit for every
course already present.

Format of ~/.cache/canvas_tools/courses_<url_hash>.json:
{
    "<course_id>": {"timestamp": <unix_float>, "data": {<CourseRecord fields>}},
    ...
}
"""

import hashlib
import json
import time
from pathlib import Path

from models import AssignmentRecord, CourseRecord, GroupRecord, GroupRules

_CACHE_DIR = Path.home() / ".cache" / "canvas_tools"
DEFAULT_TTL = 1800  # 30 minutes


def _cache_path(api_url: str) -> Path:
    key = hashlib.sha256(api_url.encode()).hexdigest()[:16]
    return _CACHE_DIR / f"courses_{key}.json"


def _course_to_dict(course: CourseRecord) -> dict:
    return {
        "id": course.id,
        "name": course.name,
        "is_weighted": course.is_weighted,
        "grading_type": course.grading_type,
        "groups": [
            {
                "id": g.id,
                "name": g.name,
                "weight": g.weight,
                "rules": {
                    "drop_lowest": g.rules.drop_lowest,
                    "drop_highest": g.rules.drop_highest,
                    "never_drop": g.rules.never_drop,
                },
                "assignments": [
                    {
                        "id": a.id,
                        "name": a.name,
                        "group_id": a.group_id,
                        "points_possible": a.points_possible,
                        "score": a.score,
                        "is_graded": a.is_graded,
                    }
                    for a in g.assignments
                ],
            }
            for g in course.groups
        ],
    }


def _course_from_dict(d: dict) -> CourseRecord:
    groups = []
    for g in d["groups"]:
        rules_d = g.get("rules", {})
        rules = GroupRules(
            drop_lowest=rules_d.get("drop_lowest", 0),
            drop_highest=rules_d.get("drop_highest", 0),
            never_drop=rules_d.get("never_drop", []),
        )
        assignments = [
            AssignmentRecord(
                id=a["id"],
                name=a["name"],
                group_id=a["group_id"],
                points_possible=a["points_possible"],
                score=a["score"],
                is_graded=a["is_graded"],
            )
            for a in g["assignments"]
        ]
        groups.append(
            GroupRecord(
                id=g["id"],
                name=g["name"],
                weight=g["weight"],
                assignments=assignments,
                rules=rules,
            )
        )
    return CourseRecord(
        id=d["id"],
        name=d["name"],
        is_weighted=d["is_weighted"],
        grading_type=d["grading_type"],
        groups=groups,
    )


def _read_store(api_url: str) -> dict:
    path = _cache_path(api_url)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def load_courses(
    api_url: str, course_ids: list[int], ttl: int = DEFAULT_TTL
) -> dict[int, CourseRecord]:
    """
    Returns a mapping of course_id -> CourseRecord for every requested ID that
    has a fresh cache entry. IDs that are missing or stale are omitted.
    """
    store = _read_store(api_url)
    now = time.time()
    result: dict[int, CourseRecord] = {}
    for course_id in course_ids:
        entry = store.get(str(course_id))
        if entry and now - entry["timestamp"] <= ttl:
            try:
                result[course_id] = _course_from_dict(entry["data"])
            except Exception:
                pass
    return result


def save_courses(api_url: str, courses: list[CourseRecord]) -> None:
    """
    Merges the given courses into the cache store, setting their timestamps to now.
    Existing entries for other course IDs are preserved.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    store = _read_store(api_url)
    now = time.time()
    for course in courses:
        store[str(course.id)] = {"timestamp": now, "data": _course_to_dict(course)}
    _cache_path(api_url).write_text(json.dumps(store))
