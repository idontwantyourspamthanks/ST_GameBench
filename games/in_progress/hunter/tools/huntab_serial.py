#!/usr/bin/env python3
"""huntab.py with base and patched runs one after the other (only one Hatari at a time).  Same arguments as huntab.py."""
import concurrent.futures as cf
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import huntab  # noqa: E402


class Serial:
    def __init__(self, n):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def submit(self, fn, *a, **k):
        f = cf.Future()
        try:
            f.set_result(fn(*a, **k))
        except BaseException as e:  # noqa: BLE001
            f.set_exception(e)
        return f


huntab.ThreadPoolExecutor = Serial
sys.argv = ["huntab.py"] + sys.argv[1:]
huntab.main()
