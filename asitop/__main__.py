"""Entry point for running asitop as a module (python -m asitop)."""

import sys

from .asitop import main
from .utils import cleanup_powermetrics

if __name__ == "__main__":
    powermetrics_process, timecode = main()
    cleanup_powermetrics(powermetrics_process, timecode)
    sys.exit(0)
