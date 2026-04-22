import argparse

from canvasapi import Canvas

from config import load_config
from display import display_all
from fetcher import fetch_courses


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
    args = parser.parse_args()

    config = load_config()
    canvas = Canvas(config.api_url, config.api_token)

    scope = "all active" if args.all_courses else "favorited"
    print(f"Fetching {scope} courses... (target grade: {config.target_grade:.1f}%)\n")
    courses = fetch_courses(canvas, all_courses=args.all_courses)
    display_all(courses, config.target_grade)


if __name__ == "__main__":
    main()
