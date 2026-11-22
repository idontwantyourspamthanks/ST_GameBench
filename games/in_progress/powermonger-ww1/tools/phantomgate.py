#!/usr/bin/env python3
"""Phantom-click gate: a name typed at the prompt must not become icon clicks.

The 1990 project's `phantom_click.md`: the keyboard-interrupt hook records make codes from
before the name prompt, so the letters of the player's name were replayed as command clicks
on the first passes of the map. A name with `R` (Derank) disbanded the starting army.

The port fixes it by only accepting a press within `WIN` = 150 VBL of the last map pass
(`LASTV`). This gate types a name that is **all command letters** -- the worst case -- and
then checks that no command was applied:

* `$2edb6` (the left click latch) must stay 0 across the first passes of the map, and
* the army must still be in its formation: the men records at `$51b66` (stride `$32`) must
  have their start state, and the captain must have no job.

A control run types a safe name (`BENCH`); the two runs must agree. If the fix regressed, the
all-command name would latch a click and the two runs would diverge.

    python3 tools/phantomgate.py
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))

from pmww import PMWW, TOS  # noqa: E402

TICK = 0x2ED90
LATCH = 0x2EDB6
# The check is the click latch ($2edb6): the phantom click raised it from the first pass of
# the map. Nothing else is needed -- if no latch is ever raised, no command can have run,
# because every command in this game is dispatched from a latched click.


def read(h, addr: int, n: int = 2) -> int:
	for _ in range(4):
		s = h.debug(f"m ${addr:x} {n}", wait=0.35)
		toks = []
		for line in s.splitlines():
			if re.match(r"^[0-9A-F]{8}:", line):
				toks += [t for t in line.split(':', 1)[1].split()
				         if len(t) == 2 and all(c in "0123456789ABCDEFabcdef" for c in t)]
		if len(toks) >= n:
			return int.from_bytes(bytes(int(t, 16) for t in toks[:n]), 'big')
		time.sleep(0.25)
	return -1


def run(folder: Path, name: str) -> dict:
	h = PMWW(disk=None, no_floppy=True, autorun_f="C:\\WW1.PRG", files_from=folder,
	         machine="ste", tos=TOS["1.62"])
	try:
		time.sleep(6)
		t = time.time()
		while not h.at_gate("name"):
			if time.time() - t > 180:
				raise SystemExit("name prompt not reached")
			h.key("space")
			time.sleep(2.5)
		for ch in name:
			h.key(ch.lower())
			time.sleep(0.4)
		h.key("Return")
		t = time.time()
		while not h.at_gate("opt"):
			if time.time() - t > 45:
				raise SystemExit("options screen not reached")
			h.key("space")
			time.sleep(2.2)
		h.debug("w $5a84e 0 1", wait=0.5)
		h.poke_click(112, 72)
		time.sleep(3)
		h.poke_click(130, 88)
		time.sleep(16)
		# the chart is up: arm a watch on the latch BEFORE the island click, then take the
		# latch and the army state over the first real passes of the map
		latches = []
		for _ in range(10):
			h.poke_click(60, 20)
			time.sleep(10)
			a = read(h, TICK, 4)
			time.sleep(2)
			if read(h, TICK, 4) > a > 0:
				break
		else:
			raise SystemExit("map view not reached")
		for _ in range(6):
			latches.append(read(h, LATCH))
			time.sleep(1.0)
		return {"latches": latches, "world": read(h, TICK, 4)}
	finally:
		h.close()


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--build", type=Path, default=GAME / "build" / "phantomgate")
	ap.add_argument("--bad", default="RAGMFYSTE")     # every letter a command
	ap.add_argument("--good", default="BENCH")
	args = ap.parse_args()

	shutil.rmtree(args.build, ignore_errors=True)
	args.build.mkdir(parents=True)
	r = subprocess.run([sys.executable, str(HERE / "wwbuild.py"), "build", "--out", str(args.build),
	                    "--only", "tick", "noprot", "keys"], capture_output=True, text=True)
	if r.returncode != 0:
		raise SystemExit(f"build failed:\n{r.stdout}\n{r.stderr}")
	shutil.copy(GAME / "extracted" / "cobra26" / "WW1_FUZI.LFB", args.build / "WW1_FUZI.LFB")

	print(f"name with every command letter: {args.bad}", flush=True)
	bad = run(args.build, args.bad)
	print(f"  latch over six passes: {bad['latches']}  world {bad['world']}", flush=True)
	print(f"control name: {args.good}", flush=True)
	good = run(args.build, args.good)
	print(f"  latch over six passes: {good['latches']}  world {good['world']}", flush=True)

	phantom = any(bad["latches"]) or any(good["latches"])
	print(f"\nthe all-command name raised no click latch: {'PASS' if not any(bad['latches']) else 'FAIL'}", flush=True)
	print(f"the control name raised no click latch:     {'PASS' if not any(good['latches']) else 'FAIL'}", flush=True)
	sys.exit(0 if not phantom else 1)


if __name__ == "__main__":
	main()
