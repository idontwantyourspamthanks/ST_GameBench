#!/usr/bin/env python3
"""Catch the write that breaks the map view's scroll phase, then the crash itself.

Symptom (reproduced from the user's report, `tools/soak.py --build ...`):

    WARN : Address Error reading at address $9dd, PC=$956
    WARN : Address Error writing at address $1bebc25f, PC=$e09598

The first fault is the VBL handler's map-scroll pointer blit. At runtime `$954` it does
`move.w (a3)+,d0` with `a3 = $9da + ($2cfde)`, so `$2cfde` (the table phase) held **3** —
a value that must only ever be 0, `$a0`, `$140`, `$1e0`, `$280` or `$320`. Every later
fault is fallout.

`$2cfde` is BSS and the game has exactly one writer (`move.w d0,$2cfde` at `$946`), which
only ever stores the previous phase, the previous phase + `$a0`, or `$a0`. So the 3 comes
from a **stray write outside the game's own code path** — this tool stops on it and prints
the PC, the registers and the instruction.

    python3 tools/crash_trace.py [--build DIR] [--minutes 8]
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))

from pmww import PMWW, TOS  # noqa: E402

TICK = 0x2ED90
PHASE = 0x2CFDE
VALID = (0x0, 0xA0, 0x140, 0x1E0, 0x280, 0x320)


def read(h, addr: int, n: int = 4) -> bytes | None:
	for _ in range(3):
		s = h.debug(f"m ${addr:x} {n}", wait=0.35)
		toks = []
		for line in s.splitlines():
			if re.match(r"^[0-9A-F]{8}:", line):
				toks += [t for t in line.split(':', 1)[1].split()
				         if len(t) == 2 and all(c in "0123456789ABCDEFabcdef" for c in t)]
		if len(toks) >= n:
			return bytes(int(t, 16) for t in toks[:n])
		time.sleep(0.25)
	return None


def word(h, addr: int) -> int:
	b = read(h, addr, 2)
	return int.from_bytes(b, 'big') if b else -1


def to_map(h) -> bool:
	for _ in range(3):
		try:
			_navigate(h)
			return True
		except RuntimeError as e:
			print(f"  navigation: {e}", flush=True)
			time.sleep(3)
	return False


def _navigate(h) -> None:
	time.sleep(6)
	t = time.time()
	while not h.at_gate("name"):
		if time.time() - t > 180:
			raise RuntimeError("name prompt not reached")
		h.key("space")
		time.sleep(2.5)
	for ch in "TRACE":
		h.key(ch)
		time.sleep(0.4)
	h.key("Return")
	t = time.time()
	while not h.at_gate("opt"):
		if time.time() - t > 45:
			raise RuntimeError("options screen not reached")
		h.key("space")
		time.sleep(2.2)
	h.debug("w $5a84e 0 1", wait=0.5)
	h.poke_click(112, 72)
	time.sleep(3)
	h.poke_click(130, 88)
	time.sleep(16)
	for _ in range(10):
		h.poke_click(60, 20)
		time.sleep(10)
		a = int.from_bytes(read(h, TICK) or b"\0\0\0\0", 'big')
		time.sleep(1.5)
		if int.from_bytes(read(h, TICK) or b"\0\0\0\0", 'big') > a > 0:
			return
	raise RuntimeError("map view not reached")


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--build", type=Path, default=GAME / "build" / "soak-pat2")
	ap.add_argument("--minutes", type=float, default=8.0)
	args = ap.parse_args()

	h = PMWW(disk=None, no_floppy=True, autorun_f="C:\\WW1.PRG", files_from=args.build,
	         machine="ste", tos=TOS["1.62"])
	try:
		if not to_map(h):
			raise SystemExit("navigation failed")
		w = int.from_bytes(read(h, TICK) or b"\0\0\0\0", 'big')
		print(f"at the map, world {w}, phase ${word(h, PHASE):04x}", flush=True)

		# Stop the CPU whenever $2cfde changes to something the game never writes.
		bad = " & ".join(f"($2cfde).w != ${v:x}" for v in VALID)
		cond = f"b ($2cfde).w ! ($2cfde).w {bad}"
		n = len(h._logtext())
		h.cmd(f"hatari-debug {cond}")
		time.sleep(1.5)
		print("armed:", [l for l in h._logtext()[n:].splitlines() if 'cfde' in l.lower()][:3], flush=True)

		deadline = time.time() + args.minutes * 60
		while time.time() < deadline:
			time.sleep(3)
			txt = h._logtext()[n:]
			if "matched" in txt:
				vals = [l.strip() for l in txt.splitlines() if '$2cfde =' in l]
				print(f"\n=== the bad write: {vals[-2:]}", flush=True)
				r = h.debug("r", wait=0.9)
				pc = re.search(r"Next PC: (\S+)", r)
				regs = " ".join(l.strip() for l in r.splitlines()
				                if re.match(r"^\s*(D[0-7]|A[0-7]|USP|SR)\s", l))
				print("  PC:", pc.group(1) if pc else "?", flush=True)
				print("  ", regs[:600], flush=True)
				if pc:
					a = int(pc.group(1).lstrip('$'), 16)
					d = h.debug(f"d ${a - 16:x}", wait=0.9)
					print("  around the PC:", flush=True)
					for line in d.splitlines()[:8]:
						print("   ", line, flush=True)
				print("  phase now:", hex(word(h, PHASE)), " world:", int.from_bytes(read(h, TICK), 'big'), flush=True)
				return
			if "Address Error" in txt or "Bus Error" in txt:
				print("  crash before the guard fired; log tail:", flush=True)
				print("\n".join(txt.splitlines()[-6:]), flush=True)
				return
		print(f"no bad write in {args.minutes:.0f} min; phase ${word(h, PHASE):04x} "
		      f"world {int.from_bytes(read(h, TICK) or b'\\0\\0\\0\\0', 'big')}", flush=True)
	finally:
		h.close()


if __name__ == "__main__":
	main()
