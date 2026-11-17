"""Entry point: `python -m rps` (or `rps` once installed)."""
import argparse
import sys
from pathlib import Path

from .stats import StatsStore

# How to get Tkinter on each OS, shown when it's missing instead of a traceback.
TK_HELP = {
    "win32": "Re-run the python.org installer, choose 'Modify' and tick 'tcl/tk and IDLE'.",
    "darwin": "Install Python from python.org (includes Tk), or with Homebrew: brew install python-tk",
    "linux": "Install it with your package manager, e.g. sudo apt install python3-tk",
}


def main() -> None:
    parser = argparse.ArgumentParser(prog="rps", description="Rock Paper Scissors against a CPU that learns.")
    parser.add_argument("--stats-file", type=Path, help="where to keep your match history")
    args = parser.parse_args()
    try:
        from .gui import run  # imported late so --help works without Tk installed
    except ImportError:
        hint = TK_HELP.get(sys.platform, TK_HELP["linux"])
        # sys.exit with a message prints it and exits with an error code.
        sys.exit(f"This game needs Tkinter, which isn't available in this Python.\n{hint}")

    run(StatsStore(args.stats_file))


if __name__ == "__main__":
    main()
