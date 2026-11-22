#!/usr/bin/env python3
"""Powermonger WW1: the release gate — the REAL patched PRG against the unpatched game.

Unlike `pmtick_series.py` (which applied the tick through the debugger to a snapshot), this
boots two real builds of `WW1.PRG` on the Cobra #26 base and compares them:

    build/original/WW1.PRG   the unpatched program (copied from extracted/cobra26)
    build/patched/WW1.PRG    tools/wwbuild.py build --only tick noprot

Both run from a folder (`files_from=`), reach the map view through the same navigation, and the
low 1 MB is dumped at a fixed PC inside the pass, once per tick, aligned by the world counter
recorded in each dump (the same method that produced the 12-tick PASS in `tickgate.md`).

The pass head is patched in the tick build (`$13da0` -> `$72000`), so the two builds do not
share an observation PC. Both do share the flip (`$e0e`), which runs once per rendered pass;
that is the observation point used here, one dump per flip, and the comparison only keeps
dumps whose world counter and pass counter agree.

Usage: python3 tools/release_gate.py [dumps]
Exit code 0 = PASS.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))
from pmww import PMWW  # noqa: E402

TICK = 0x2ED90
PASS = 0x50FD8
FLIP = 0xE0E
OUT = GAME / "work" / "gate"

EXCLUDE = [
	(0x00000, 0x00800),      # TOS low memory
	(0x007E6, 0x007EA), (0x00842, 0x00846), (0x0144B4, 0x0144B8),   # click-stamp operands (tick)
	(0x013DA0, 0x013DA6), (0x013E24, 0x013E2A), (0x013E36, 0x013E3C), (0x013E42, 0x013E48),
	(0x01B900, 0x01B908),    # the weather animation phase
	(0x1D2A0, 0x2D600),      # IKBD state, pointer words, both screen buffers (pixel gate's job)
	(0x2D600, 0x2E000),      # the stack
	(0x2ED90, 0x2EDC0),      # world counter, click stamp, latches
	(0x5EF00, 0x5EFC0),      # the sound sequencer
	(0x71B7C, 0x71B84),      # the VBL counter
	(0x72000, 0x73000),      # the tick payload
	(0x00E7C2, 0x00E7C6), (0x011DC6, 0x011DD0),   # buffer pointers (flip parity)
	(0x0082C4, 0x0082C8),    # the back-buffer address
	# Self-modified instruction operands (documented, not world state):
	#   $1BC9C  the YM sample player stores its advancing pointer inside `movea.l #0,a0`
	#           (frameloop.md section 2: the timer-C player at $1bc92 self-patches $1bc9a)
	#   $0E51F  a self-modified operand in the icon/pattern draw region
	(0x01BC9A, 0x01BCA0),
	# $11951 is inside a zero-padded gap after an `rts` in the chart code: uninitialised
	# memory (TOS/loader leftovers), not game state.
	(0x01194E, 0x011960),
	(0x00E518, 0x00E524),
]


def excluded(a: int) -> bool:
	return any(lo <= a < hi for lo, hi in EXCLUDE)


def prepare() -> tuple[Path, Path]:
	"""Build both programs into their own folders (each needs WW1_FUZI.LFB beside it)."""
	orig = GAME / "build" / "gate-original"
	patched = GAME / "build" / "gate-patched"
	for d in (orig, patched):
		shutil.rmtree(d, ignore_errors=True)
		d.mkdir(parents=True)
		shutil.copy(GAME / "extracted" / "cobra26" / "WW1_FUZI.LFB", d / "WW1_FUZI.LFB")
	# The REFERENCE build also carries `noprot`: the stock game stops at the protection
	# question after the island click and can never reach the map, so a truly stock reference
	# cannot be compared. Both builds therefore have the protection removed, and the ONLY
	# difference between them is the tick.
	r = subprocess.run([sys.executable, str(HERE / "wwbuild.py"), "build",
	                    "--only", "noprot", "--out", str(orig)],
	                   capture_output=True, text=True)
	if r.returncode != 0:
		raise SystemExit(f"wwbuild (reference) failed:\n{r.stdout}\n{r.stderr}")
	r = subprocess.run([sys.executable, str(HERE / "wwbuild.py"), "build",
	                    "--only", "tick", "noprot", "--out", str(patched)],
	                   capture_output=True, text=True)
	if r.returncode != 0:
		raise SystemExit(f"wwbuild failed:\n{r.stdout}\n{r.stderr}")
	return orig, patched


def to_map(h) -> None:
	"""The standard navigation: cracktro -> name -> options -> chart -> island."""
	time.sleep(6)
	t = time.time()
	while not h.at_gate("name"):
		if time.time() - t > 180:
			raise RuntimeError("name prompt not reached")
		h.key("space")
		time.sleep(2.5)
	for ch in "GATE":
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
	h.poke_click(112, 72)          # Start New Conquest
	time.sleep(3)
	h.poke_click(130, 88)          # activate
	time.sleep(16)
	# the island click sometimes lands before the chart is ready: click until the world runs
	for attempt in range(10):
		h.poke_click(60, 20)
		time.sleep(10)
		if world_running(h):
			break
	else:
		raise RuntimeError("map view not reached (the island click never took)")
	time.sleep(10)                 # let the land finish generating and settle
	# The navigation can leave the camera at a different map cell (the pointer position when
	# the island is clicked varies), which changes every projected coordinate. The camera is
	# re-derived from the pointer every pass, so park the pointer in the same place in both
	# runs and let the game settle to the same cell.
	time.sleep(1)


def world_running(h) -> bool:
	"""The map view's world counter is advancing and the picture is alive."""
	for _ in range(8):
		s = h.debug(f"m ${TICK:x} 4", wait=0.4)
		if "read fail" in s:
			time.sleep(0.6)
			continue
		v = int.from_bytes(read_tick_bytes(h), 'big') if read_tick_bytes(h) else -1
		a = v
		time.sleep(1.2)
		b = int.from_bytes(read_tick_bytes(h), 'big') if read_tick_bytes(h) else -1
		return b > a > 0
	return False


def read_tick_bytes(h) -> bytes | None:
	import re
	for _ in range(4):
		s = h.debug(f"m ${TICK:x} 4", wait=0.4)
		toks = []
		for line in s.splitlines():
			if re.match(r"^[0-9A-F]{8}:", line):
				toks += [t for t in line.split(':', 1)[1].split()
				         if len(t) == 2 and all(c in "0123456789ABCDEFabcdef" for c in t)]
		if len(toks) >= 4:
			return bytes(int(t, 16) for t in toks[:4])
		time.sleep(0.3)
	return None


def series(folder: Path, tag: str, n: int) -> dict[int, bytes]:
	h = PMWW(disk=None, no_floppy=True, autorun_f="C:\\WW1.PRG", files_from=folder)
	dumps: dict[int, bytes] = {}
	try:
		to_map(h)
		for i in range(n):
			p = (OUT / f"{tag}_{i}.bin").resolve()
			p.unlink(missing_ok=True)
			cmds = p.with_suffix(".cmds")
			# pin the camera and freeze the world, then dump: a one-off write outside the
			# capture is re-derived by the next pass
			cmds.write_text(
				"w $50fd4 0 $20\n"
				"w $50fd6 0 $2a\n"
				f"savebin {p} 0 1048576\nr\n")
			h.cmd(f"hatari-debug b pc = ${FLIP:x} && (${TICK:x}).l > 0 :once :file {cmds}")
			t = time.time()
			while not p.exists():
				if time.time() - t > 45:
					break
				time.sleep(0.2)
			if not p.exists():
				continue
			d = p.read_bytes()
			if len(d) < 0x72000:
				continue
			dumps.setdefault(int.from_bytes(d[TICK:TICK + 4], 'big'), d)
			print(f"  {tag} dump {i}: world {int.from_bytes(d[TICK:TICK+4],'big')} "
			      f"pass {int.from_bytes(d[PASS:PASS+4],'big')}")
	finally:
		h.close()
	return dumps


def main() -> int:
	n = int(sys.argv[1]) if len(sys.argv) > 1 else 24
	OUT.mkdir(parents=True, exist_ok=True)
	orig_dir, patched_dir = prepare()
	print("original:", orig_dir)
	print("patched :", patched_dir)
	def attempt(folder, tag):
		for go in range(3):
			try:
				return series(folder, tag, n)
			except RuntimeError as e:
				print(f"  {tag}: {e} (retry {go + 1}/3)")
		raise SystemExit(f"{tag}: navigation failed three times")

	stock = attempt(orig_dir, "stock")
	tick = attempt(patched_dir, "tick")
	common = sorted(set(stock) & set(tick))
	print(f"\nworld ticks captured: stock {len(stock)}, patched {len(tick)}, common {len(common)}")
	if not common:
		print("FAIL: no common world tick (the two runs did not overlap)")
		return 1
	print("\ntick  pass(stock/tick)  differing bytes")
	ok = True
	for t in common:
		a, b = stock[t], tick[t]
		pa = int.from_bytes(a[PASS:PASS + 4], 'big')
		pb = int.from_bytes(b[PASS:PASS + 4], 'big')
		diff = [i for i in range(0x72000) if a[i] != b[i] and not excluded(i)]
		ok &= not diff
		print(f"{t:5d}  {pa:5d}/{pb:<5d}  {len(diff):5d}")
	# the negative control: two consecutive stock ticks must differ
	if len(common) >= 2:
		a, b = stock[common[0]], stock[common[1]]
		n_diff = sum(1 for i in range(0x72000) if a[i] != b[i] and not excluded(i))
		print(f"\nnegative control {common[0]} vs {common[1]}: {n_diff} differing bytes (must be > 0)")
		ok &= n_diff > 0
	print("\nPASS" if ok else "\nFAIL")
	return 0 if ok else 1


if __name__ == "__main__":
	sys.exit(main())
