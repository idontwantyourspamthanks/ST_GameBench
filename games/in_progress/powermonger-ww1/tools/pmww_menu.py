#!/usr/bin/env python3
"""Exploratory: skip the cracktro, reach the PP106 menu and launch the game."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pmww import PMWW  # noqa: E402

out = Path(tempfile.mkdtemp(prefix="pmww-menu-"))
h = PMWW()
try:
	# cracktro: press space / fire a few times
	for i in range(6):
		h.key("space")
		time.sleep(3)
		h.shot(str(out / f"k{i:02d}.png"))
		print(f"k{i:02d} vbl={h.vbl()}")
	# try a click too (menus are often mouse-driven)
	h.click(hold=0.3)
	time.sleep(3)
	h.shot(str(out / "click0.png"))
	for i in range(6, 12):
		h.key("space")
		time.sleep(2)
		h.key("Return")
		time.sleep(2)
		h.shot(str(out / f"k{i:02d}.png"))
		print(f"k{i:02d} vbl={h.vbl()}")
finally:
	h.close()
print(f"shots in {out}")
