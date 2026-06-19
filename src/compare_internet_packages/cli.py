import argparse

from .ranking import compare


def main():
    parser = argparse.ArgumentParser(description="compare internet packages")
    parser.add_argument(
        "-b", "--budget", type=int, help="<Required> max budget", required=True
    )
    parser.add_argument(
        "-p", "--provider", nargs="+", help="<Required> Set provider", required=True
    )
    args = parser.parse_args()
    compare(args.provider, args.budget)


if __name__ == "__main__":
    main()
