#!/usr/bin/env python3
"""World rate at 8/16 MHz and 50/60 Hz, and the pause behaviour — the tick's release matrix.

Usage: python3 tools/rate_check.py
Prints one line per case; 4.00 ticks/s is the target everywhere, and 0 while paused.
"""
import re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))
from pmww import PMWW

TICK = 0x2ED90


def rb(h, a, n=4):
	for _ in range(6):
		s = h.debug(f"m ${a:x} {n}", wait=0.4)
		toks = []
		for line in s.splitlines():
			if re.match(r"^[0-9A-F]{8}:", line):
				toks += [t for t in line.split(':', 1)[1].split()
				         if len(t) == 2 and all(c in "0123456789ABCDEFabcdef" for c in t)]
		if len(toks) >= n:
			return bytes(int(t, 16) for t in toks[:n])
		time.sleep(0.3)
	return None


def rd(h, a):
	b = rb(h, a)
	return int.from_bytes(b, 'big') if b else -1


def rate(h, secs=10):
	a = rd(h, TICK); v1 = h.vbl()
	time.sleep(secs)
	b = rd(h, TICK); v2 = h.vbl()
	return (b - a) / ((v2 - v1) / 50.0)


def to_map(h):
	time.sleep(6)
	t = time.time()
	while not h.at_gate("name"):
		if time.time() - t > 180:
			raise RuntimeError("name")
		h.key("space"); time.sleep(2.5)
	for ch in "RATE":
		h.key(ch); time.sleep(0.4)
	h.key("Return")
	t = time.time()
	while not h.at_gate("opt"):
		if time.time() - t > 45:
			raise RuntimeError("options")
		h.key("space"); time.sleep(2.2)
	h.debug("w $5a84e 0 1", wait=0.5)
	h.poke_click(112, 72); time.sleep(3)
	h.poke_click(130, 88); time.sleep(16)
	for attempt in range(10):
		h.poke_click(60, 20); time.sleep(10)
		a = rd(h, TICK); time.sleep(1.5); b = rd(h, TICK)
		if b > a > 0:
			break
	else:
		raise RuntimeError("no map view")
	time.sleep(10)
	return h


def main():
	folder = GAME / "build" / "rate"
	subprocess.run([sys.executable, str(HERE / "wwbuild.py"), "build", "--only", "tick", "noprot",
	                "--out", str(folder)], check=True, capture_output=True)
	import shutil
	shutil.copy(GAME / "extracted" / "cobra26" / "WW1_FUZI.LFB", folder / "WW1_FUZI.LFB")

	for machine, tos, clock in (("ste", "1.62", 8), ("ste", "1.62", 16),
	                            ("megaste", "2.06", 8), ("megaste", "2.06", 16)):
		h = PMWW(disk=None, no_floppy=True, autorun_f="C:\\WW1.PRG", files_from=folder,
		         machine=machine, tos=__import__('pmww').TOS[tos])
		try:
			to_map(h)
			if clock != 8:
				h.set_cpuclock(clock); time.sleep(2)
			print(f"{machine:8s} {clock:2d} MHz: {rate(h):.2f} ticks/s")
		finally:
			h.close()
	print("done")


if __name__ == "__main__":
	main()
