import argparse
import sys

from .ranking import compare
from .scrapers import SCRAPERS


def refresh():
    """Re-scrape every provider (writes DB/*.csv). Entry point for the daily Action."""
    for name, scrape in SCRAPERS.items():
        try:
            scrape()
        except Exception as e:  # keep going so one dead site doesn't block the rest
            print(f"warning: {name} scrape failed: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        prog="besarfeh",
        description="Besarfeh (به‌صرفه) — rank Iranian mobile-internet packages by price-per-MB",
    )
    parser.add_argument(
        "-b", "--budget", type=int, help="<Required> max budget (toman)", required=True
    )
    parser.add_argument(
        "-p",
        "--provider",
        nargs="+",
        choices=list(SCRAPERS),  # rejects typos like 'irancell' (it's 'mtn')
        metavar="PROVIDER",
        help=f"<Required> one or more of: {', '.join(SCRAPERS)}",
        required=True,
    )
    args = parser.parse_args()
    compare(args.provider, args.budget)


if __name__ == "__main__":
    main()
