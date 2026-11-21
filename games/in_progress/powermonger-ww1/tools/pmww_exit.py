#!/usr/bin/env python3
"""Exploratory: exit the doc displayer into the game."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pmww import PMWW  # noqa: E402

out = Path(tempfile.mkdtemp(prefix="pmww-exit-"))
h = PMWW()
try:
	for i in range(3):  # through the cracktro into the displayer
		h.key("space")
		time.sleep(2.5)
		h.shot(str(out / f"pre{i}.png"))
	for i, k in enumerate(("Escape", "Escape", "Return", "Escape", "space", "Return")):
		h.key(k)
		time.sleep(2.5)
		h.shot(str(out / f"x{i:02d}_{k}.png"))
		print(f"x{i:02d} {k} vbl={h.vbl()}")
finally:
	h.close()
print(f"shots in {out}")
