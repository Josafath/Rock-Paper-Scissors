"""Rock Paper Scissors v2: a CPU that learns how you play."""

import sys

# Checked here, the first module Python loads, so older versions get a clear
# message instead of a confusing error somewhere else.
if sys.version_info < (3, 10):
    sys.exit("This game needs Python 3.10 or newer (you have %d.%d)." % sys.version_info[:2])

__version__ = "2.0.0"
