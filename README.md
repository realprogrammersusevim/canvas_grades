# canvas-grades

A Python CLI tool that connects to the Canvas LMS API to calculate what-if
grades and identify the minimum scores needed on upcoming assignments to reach a
target grade.

## Features

- Fetches grades from your Canvas courses via the official API
- Computes your current grade (supporting both weighted-group and points-based
  courses)
- Shows per-assignment minimum scores needed to hit your target
- Detects when a target is impossible and reports the maximum achievable grade
- Pins hypothetical scores on ungraded assignments (`--assume`) and recomputes
  minimums
- Caches responses locally so repeated runs are instant

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

**1. Clone the repo**

```bash
git clone <repo-url>
cd canvas_grades
```

**2. Install dependencies**

```bash
uv sync
```

**3. Create a `.env` file** in the project root:

```env
CANVAS_API_URL=https://canvas.instructure.com
CANVAS_API_TOKEN=your_token_here
TARGET_GRADE=90.0
```

- `CANVAS_API_URL` — base URL of your Canvas instance
- `CANVAS_API_TOKEN` — personal access token from **Account → Settings → New
  Access Token** in Canvas
- `TARGET_GRADE` — (optional) target percentage, defaults to `90.0`

## Usage

```bash
uv run main.py
```

### Flags

| Flag                               | Description                                                     |
| ---------------------------------- | --------------------------------------------------------------- |
| `--all-courses`                    | Include all active courses, not just favorited ones             |
| `--refresh`                        | Bypass the local cache and fetch fresh data from Canvas         |
| `--cache-ttl SECONDS`              | Cache lifetime in seconds (default: 1800 / 30 min)              |
| `--assume COURSE:ASSIGNMENT=SCORE` | Pin a hypothetical score on an ungraded assignment (repeatable) |

### `--assume` examples

Score as a percentage:

```bash
uv run main.py --assume "calc:midterm exam 2=85%"
```

Score as raw points:

```bash
uv run main.py --assume "biology:lab report=47.5"
```

Multiple assumptions:

```bash
uv run main.py --assume "calc:midterm=85%" --assume "bio:quiz 4=9"
```

Course and assignment names use **case-insensitive substring matching** and must
uniquely identify one course and one ungraded assignment.

## Sample Output

```
────────────────────────────────────────────────────
  Calculus II
  Current Grade: 87.3%  [target: 90.0%]
  Grading: Weighted Groups

  Groups:
    Homework                  (20%)   92.4%  [8/10 graded]
    Exams                     (50%)   84.1%  [2/3 graded]
    Quizzes                   (30%)   89.0%  [5/6 graded]

  What you need (assuming other ungraded assignments maintain current averages):
    Exam 3                            100 pts  →  need 73.2 pts (73.2%)
    Quiz 6                             20 pts  →  need 14.1 pts (70.5%)
────────────────────────────────────────────────────
```
