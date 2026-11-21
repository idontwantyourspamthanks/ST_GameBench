#!/usr/bin/env python3
"""Find the docs displayer's input loop: sit in it, sample the PC, dump RAM around it."""
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pmww import PMWW  # noqa: E402

out = Path(tempfile.mkdtemp(prefix="pmww-loop-"))
h = PMWW(disk=None)
try:
	time.sleep(10)
	for i in range(6):
		h.key("space")
		time.sleep(1.6)
	# now in the displayer; sample PCs
	pcs = []
	for i in range(8):
		r = h.debug("r", wait=1.2)
		for line in r.splitlines():
			if line.startswith("PC:"):
				pcs.append(line.strip())
		time.sleep(0.4)
	print("PC samples:")
	for p in pcs:
		print("  ", p)
finally:
	h.close()
