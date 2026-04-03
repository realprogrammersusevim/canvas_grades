from canvasapi import Canvas

from config import load_config
from display import display_all
from fetcher import fetch_courses


def main() -> None:
    config = load_config()
    canvas = Canvas(config.api_url, config.api_token)

    print(f"Fetching courses... (target grade: {config.target_grade:.1f}%)\n")
    courses = fetch_courses(canvas)
    display_all(courses, config.target_grade)


if __name__ == "__main__":
    main()
