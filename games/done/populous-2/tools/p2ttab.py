#!/usr/bin/env python3
"""p2tick.py ab with pop2_tooltip added to the patched set (the tick set + the tooltip): world by turn must still match the unpatched game.

    python3 tools/p2ttab.py ab SNAP MHZ TURNS [--spin N] [--hz 50|60] ...     (same arguments as p2tick.py ab)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import p2tick as TK  # noqa: E402

TK.TICKSET = TK.TICKSET + ["pop2_tooltip"]
if __name__ == "__main__":
    TK.main()
