# CLAUDE.md

## Project

A Python CLI tool using the [canvasapi](https://canvasapi.readthedocs.io/)
library to calculate "what-if" grades and identify minimum scores needed to
reach a target grade across Canvas LMS courses.

## Commands

This project uses [uv](https://docs.astral.sh/uv/) for dependency management.

```bash
uv run main.py          # Run the main grade calculation script
uv add <package>        # Add a dependency
uv sync                 # Sync dependencies from lockfile
```

### CLI Flags

- `--all-courses`: Include all active courses instead of only favorited ones.
- `--refresh`: Bypass the local cache and fetch fresh data from Canvas.
- `--cache-ttl SECONDS`: Cache lifetime in seconds (default: 1800 / 30 min).
- `--assume COURSE:ASSIGNMENT=SCORE`: Pin a hypothetical score on an ungraded
  assignment and recompute minimums. `SCORE` can be a percentage (`69.9%`) or
  raw points (`69.9`). Course and assignment match by case-insensitive substring.
  Repeatable.

## Environment Setup

Create a `.env` file in the project root with the following variables:

- `CANVAS_API_URL`: The base URL of your Canvas instance (e.g.,
  `https://canvas.instructure.com`)
- `CANVAS_API_TOKEN`: Your personal access token from Canvas user settings.
- `TARGET_GRADE`: (Optional) Default target percentage for "what-if"
  calculations (defaults to `90.0`).

## Coding Standards

- **Python Version:** 3.13+ (enforced by `pyproject.toml`).
- **Type Safety:** Use Python type hints for all function signatures and
  variable declarations.
- **Documentation:** Provide docstrings (PEP 257) for all modules, classes, and
  public functions.
- **Models:** Use `dataclasses` (from `models.py`) for structured data
  representations.
- **Concurrency:** Use `ThreadPoolExecutor` for fetching course/assignment data
  to improve API performance.
- **Modularity:**
  - `config.py`: Environment variable loading and validation.
  - `models.py`: Core data structures using `dataclasses`.
  - `fetcher.py`: Logic for retrieving data from the Canvas API.
  - `calculator.py`: Grade computation logic (handling weighted and point-based
    grading).
  - `display.py`: Console output formatting and visualization.
  - `cache.py`: File-based JSON cache for Canvas API responses, stored in
    `~/.cache/canvas_tools/`. Courses are cached individually by ID so
    partial cache hits still work when switching between favorites and all courses.
- **Grade Calculation Logic:** Matches Canvas behavior by re-normalizing weights
  of active assignment groups (those with at least one graded assignment) to sum
  to 100%.
- **Error Handling:** Gracefully handle missing environment variables or API
  failures using `SystemExit` or warnings.
