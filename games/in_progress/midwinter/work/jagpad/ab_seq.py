#!/usr/bin/env python3
"""mw1ab.py with ONE Hatari at a time (the stock tool runs base and patched concurrently).
  ab_seq.py --only ... --base ... [--snapshot ...] [--flips ...]"""
import sys
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/tools')
import mw1ab
from concurrent.futures import ThreadPoolExecutor as _T
mw1ab.ThreadPoolExecutor = lambda n: _T(1)
mw1ab.main()
