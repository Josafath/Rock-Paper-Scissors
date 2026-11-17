"""Entry point: `python -m rps`."""
import argparse
from pathlib import Path

from .stats import StatsStore


def main() -> None:
    parser = argparse.ArgumentParser(prog="rps", description="Rock Paper Scissors against a CPU that learns.")
    parser.add_argument("--stats-file", type=Path, help="where to keep your match history")
    args = parser.parse_args()
    from .gui import run  # imported late so --help works without Tk installed

    run(StatsStore(args.stats_file))


if __name__ == "__main__":
    main()
