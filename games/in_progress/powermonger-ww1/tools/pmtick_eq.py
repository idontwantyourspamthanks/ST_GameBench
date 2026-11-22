#!/usr/bin/env python3
"""Powermonger WW1: per-tick world-state equality — patched (fixed tick) vs unpatched.

The 1990 method (../../done/powermonger/tools/pmtick.py, work/notes/timing.md): both runs
start from the same snapshot and the world state is compared at the same WORLD TICK (the
game's own counter $2ed90), over the whole low RAM, with a negative control (tick N vs
N+1 must differ).

The dump is taken by a Hatari value breakpoint on the counter itself, so both runs are
captured exactly at $2ed90 == N (polling cannot hit an exact tick). The patched build's
counter bumps once per TICK, the unpatched one once per pass; both are the world clock, so
the same N means "after N world steps" in both. Ranges excluded: the patch sites, TOS low
memory, the VBL counter/flag, the click stamp, the IKBD parser and pointer words, the
stack, the sound sequencer state, the patch payload.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from pmww import PMWW  # noqa: E402

TICK = 0x2ED90

EXCLUDE = [
	(0x00000, 0x00800),      # TOS low memory
	(0x01B900, 0x01B908),    # the weather animation phase (advanced by R passes)
	(0x0007E6, 0x0007EA),    # patch site: the click stamp operand (right latch)
	(0x000842, 0x000846),    # patch site: the click stamp operand (left latch)
	(0x0144B4, 0x0144B8),    # patch site: the expiry read
	(0x013DA0, 0x013DA6),    # patch site: the pass head
	(0x013E24, 0x013E2A),    # patch site: the weather wrapper
	(0x013E36, 0x013E3C),    # patch site: the men wrapper
	(0x013E42, 0x013E48),    # patch site: the terrain wrapper
	(0x1D2A0, 0x1D2C0),      # IKBD parser state + pointer words
	(0x1D2C0, 0x1D500),      # the pointer/sprite under-save scratch
	(0x1D500, 0x2D600),      # the two screen buffers (the pixel gate covers them)
	(0x2D600, 0x2E000),      # the stack
	(0x2ED90, 0x2EDC0),      # the world counter + the click stamp + the latches
	(0x2EDA4, 0x2EDA8),      # the RNG seed
	(0x5EF00, 0x5EFC0),      # the sound sequencer state
	(0x71B7C, 0x71B80),      # the VBL counter
	(0x72000, 0x73000),      # the patch payload
	(0x00E7C2, 0x00E7C6),    # the draw pointer (which buffer: parity of the flip)
	(0x011DC6, 0x011DD0),    # a copy of the buffer pointer
	(0x2ED90, 0x2EDA0),      # the screen-buffer pair + the world counter
]

# the value-breakpoint's command file: dump the low 1 MB (savebin length is decimal)
DUMP = "savebin {path} 0 1048576\nr\n"


def excluded(a: int) -> bool:
	return any(lo <= a < hi for lo, hi in EXCLUDE)


def dump_at_tick(h, target: int, path: Path, timeout: float = 180) -> None:
	cmds = path.with_suffix(".cmds")
	cmds.write_text(DUMP.format(path=str(Path(path).resolve())))
	h.cmd(f"hatari-debug b ($2ed90).l > ${target - 1:x} :once :file {cmds}")
	t = time.time()
	while not path.exists():
		if time.time() - t > timeout:
			raise RuntimeError(f"tick {target}: no dump (breakpoint never hit)")
		time.sleep(0.4)
	if path.stat().st_size < 0x72000:
		raise RuntimeError(f"tick {target}: short dump {path.stat().st_size}")


def apply_tick(h) -> None:
	"""The tick prototype's live patch (work/tickproto/tick.s / tick.bin)."""
	def w(addr, bs):
		h.debug("w $" + format(addr, "x") + " " + " ".join("$" + format(b, "02x") for b in bs), wait=0.25)
	h.debug("loadbin work/tickproto/tick.bin $72000", wait=0.8)
	for a in (0x72180, 0x72184):
		w(a, [0, 0, 0, 0])
	w(0x72188, [0, 0])
	w(0x7218a, [0, 0])
	w(0x13da0, [0x4e, 0xb9, 0x00, 0x07, 0x20, 0x00])
	w(0x13e24, [0x4e, 0xb9, 0x00, 0x07, 0x20, 0xe0])
	w(0x13e36, [0x4e, 0xb9, 0x00, 0x07, 0x21, 0x10])
	w(0x13e42, [0x4e, 0xb9, 0x00, 0x07, 0x21, 0x40])
	for a in (0x7e6, 0x842, 0x144b4):
		w(a, [0x00, 0x07, 0x21, 0x80])


def read_tick(h) -> int:
	import re
	for _ in range(6):
		s = h.debug(f"m ${TICK:x} 4", wait=0.4)
		toks = []
		for line in s.splitlines():
			if re.match(r"^[0-9A-F]{8}:", line):
				toks += [t for t in line.split(':', 1)[1].split()
				         if len(t) == 2 and all(c in "0123456789ABCDEFabcdef" for c in t)]
		if len(toks) >= 4:
			return int.from_bytes(bytes(int(t, 16) for t in toks[:4]), 'big')
		time.sleep(0.3)
	raise RuntimeError("tick read failed")


def capture(snapshot: str, deltas: list[int], tag: str, patched: bool, out: Path) -> dict[int, bytes]:
	h = PMWW(disk=None, snapshot=snapshot)
	dumps: dict[int, bytes] = {}
	try:
		# the targets are ABSOLUTE world ticks: read the counter at once (the snapshot already
		# holds a fixed tick), so both runs compare the same point of the simulation
		base = read_tick(h)
		if patched:
			apply_tick(h)
		print(f"{tag}: base tick {base}, targets {[base + d for d in deltas]}")
		for t in (base + d for d in deltas):
			path = out / f"{tag}_{t}.bin"
			if path.exists():
				path.unlink()          # never accept a stale dump
			dump_at_tick(h, t, path)
			data = path.read_bytes()
			if len(data) < 0x72000:
				raise RuntimeError(f"tick {t}: short dump {len(data)} bytes")
			dumps[t] = data
			print(f"{tag} tick {t}: dumped {len(data)} bytes")
	finally:
		h.close()
	return dumps


def main() -> None:
	snapshot = sys.argv[1] if len(sys.argv) > 1 else "work/snapshots/battle.sav"
	deltas = [int(x) for x in (sys.argv[2].split(',') if len(sys.argv) > 2 else ["6", "7"])]
	out = Path("work/eq")
	out.mkdir(parents=True, exist_ok=True)
	stock = capture(snapshot, deltas, "stock", False, out)
	tick = capture(snapshot, deltas, "tick", True, out)
	n = 0x72000
	key = sorted(stock)[0]
	a, b = stock[key], tick[key]
	diffs = [i for i in range(n) if a[i] != b[i] and not excluded(i)]
	print(f"state equality at tick {key}: {len(diffs)} differing bytes outside the excluded ranges")
	clusters: list[list[int]] = []
	for i in diffs:
		if clusters and i - clusters[-1][-1] <= 16:
			clusters[-1].append(i)
		else:
			clusters.append([i])
	for c in clusters[:15]:
		print(f"  ${c[0]:05x}-${c[-1]:05x} ({len(c)} bytes)  stock {a[c[0]:c[0]+8].hex()} tick {b[c[0]:c[0]+8].hex()}")
	if len(stock) > 1:
		neg = sorted(stock)[1]
		ndiff = sum(1 for i in range(n) if a[i] != stock[neg][i] and not excluded(i))
		print(f"negative control stock {key} vs {neg}: {ndiff} differing bytes (must be > 0)")
	print("PASS" if not diffs else "FAIL")


if __name__ == "__main__":
	main()
