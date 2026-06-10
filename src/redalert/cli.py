"""Command-line entry point for redalert."""

import argparse
import sys

from redalert import scraper, telegram
from redalert.scraper import StockLevel

DEFAULT_THRESHOLD = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redalert",
        description=(
            "Check the OVSZ blood stock and send a Telegram alert when a "
            "blood type is at or below the threshold."
        ),
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=DEFAULT_THRESHOLD,
        help=(
            "Alert when the stock (in days) is at or below this value "
            f"(default: {DEFAULT_THRESHOLD})."
        ),
    )
    parser.add_argument(
        "--type",
        dest="types",
        action="append",
        metavar="BLOOD_TYPE",
        help=(
            "Blood type to watch, e.g. AB+ (repeatable). "
            "If omitted, all blood types are checked."
        ),
    )
    parser.add_argument(
        "--url",
        default=scraper.DEFAULT_URL,
        help=f"Page to scrape (default: {scraper.DEFAULT_URL}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the alert instead of sending it to Telegram.",
    )
    return parser


def selected_codes(types: list[str] | None) -> list[str] | None:
    """Resolve the requested blood types to HTML codes, or None for all."""
    if not types:
        return None
    return [scraper.blood_type_to_code(t) for t in types]


def select_levels(
    levels: dict[str, StockLevel], codes: list[str] | None
) -> list[StockLevel]:
    """Pick the watched levels; warn about requested types with no data."""
    if codes is None:
        return list(levels.values())

    watched: list[StockLevel] = []
    for code in codes:
        level = levels.get(code)
        if level is None:
            blood_type = scraper.code_to_blood_type(code)
            print(
                f"warning: no data for {blood_type} on the page; skipping.",
                file=sys.stderr,
            )
            continue
        watched.append(level)
    return watched


def report_status(levels: list[StockLevel], threshold: int) -> None:
    """Log the current readings so the Action log is useful on its own."""
    print(f"Threshold: {threshold} day(s). Current readings:")
    for level in sorted(levels, key=lambda lvl: lvl.blood_type):
        flag = "  LOW" if level.days <= threshold else ""
        print(f"  {level.blood_type:<3} {level.days} -> {level.text}{flag}")


def send_alert(low: list[StockLevel], threshold: int, dry_run: bool) -> int:
    """Format and deliver the alert; return the process exit code."""
    message = telegram.format_message(low, threshold)
    if dry_run:
        print("--- DRY RUN: message that would be sent ---")
        print(message)
        return 0

    try:
        telegram.send_message(message)
    except telegram.TelegramConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # Telegram API/network failure
        print(f"error: failed to send Telegram message: {exc}", file=sys.stderr)
        return 1

    print(f"Alert sent for {len(low)} blood type(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        codes = selected_codes(args.types)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        html = scraper.fetch_html(args.url)
    except Exception as exc:  # network/HTTP failure
        print(f"error: failed to download {args.url}: {exc}", file=sys.stderr)
        return 1

    levels = scraper.parse_levels(html)
    if not levels:
        print("error: no blood-stock data found on the page.", file=sys.stderr)
        return 1

    watched = select_levels(levels, codes)
    report_status(watched, args.threshold)

    low = [level for level in watched if level.days <= args.threshold]
    if not low:
        print("All watched blood types are above the threshold. No alert sent.")
        return 0

    return send_alert(low, args.threshold, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
