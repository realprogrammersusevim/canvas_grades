import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    api_url: str
    api_token: str
    target_grade: float = 90.0


def load_config() -> Config:
    api_url = os.environ.get("CANVAS_API_URL", "").strip().rstrip("/")
    api_token = os.environ.get("CANVAS_API_TOKEN", "").strip()

    if not api_url:
        raise SystemExit("Error: CANVAS_API_URL is not set. Add it to .env or set it as an environment variable.")
    if not api_token:
        raise SystemExit("Error: CANVAS_API_TOKEN is not set. Add it to .env or set it as an environment variable.")

    target_raw = os.environ.get("TARGET_GRADE", "90.0").strip()
    try:
        target_grade = float(target_raw)
    except ValueError:
        raise SystemExit(f"Error: TARGET_GRADE must be a number, got '{target_raw}'")

    return Config(api_url=api_url, api_token=api_token, target_grade=target_grade)
