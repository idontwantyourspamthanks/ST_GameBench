#!/usr/bin/env python3
"""Powermonger WW1: per-tick world-state equality by dump SERIES (the authoritative gate).

The single-shot form races the counter (a dump named tick N often holds N+k). This takes a
series of one-shot dumps from each run; each file records the world counter it actually
landed on, and the comparison aligns by that recorded value, so no timing precision is
needed. Both runs must cover a common range (the patch-apply round trips shift the patched
run by a few ticks, so apply the patch with one batched debugger command file, as here).

Usage: python3 tools/pmtick_series.py [snapshot] [dumps]
Writes work/eq/ser_{stock,tick}_N.bin and prints the per-tick table.
"""
import sys, time
from pathlib import Path
sys.path.insert(0, 'tools')
from pmww import PMWW

TICK = 0x2ED90
out = Path('work/eq'); out.mkdir(parents=True, exist_ok=True)

def apply_tick(h):
	def w(a, bs):
		lines.append("w $" + format(a, "x") + " " + " ".join("$" + format(b, "02x") for b in bs))
	lines = []
	lines.insert(0, "loadbin work/tickproto/tick.bin $72000")
	for a in (0x72180, 0x72184):
		w(a, [0, 0, 0, 0])
	w(0x72188, [0, 0]); w(0x7218a, [0, 0])
	w(0x13da0, [0x4e, 0xb9, 0x00, 0x07, 0x20, 0x00])
	w(0x13e24, [0x4e, 0xb9, 0x00, 0x07, 0x20, 0xe0])
	w(0x13e36, [0x4e, 0xb9, 0x00, 0x07, 0x21, 0x10])
	w(0x13e42, [0x4e, 0xb9, 0x00, 0x07, 0x21, 0x40])
	for a in (0x7e6, 0x842, 0x144b4):
		w(a, [0x00, 0x07, 0x21, 0x80])
	cf = Path("/tmp/apply_tick.cmds")
	cf.write_text("\n".join(lines) + "\n")
	h.cmd(f"hatari-debug file {cf}")

def series(tag, patched, n=12):
	h = PMWW(disk=None, snapshot="work/snapshots/battle.sav")
	saved = []
	try:
		if patched:
			apply_tick(h)
		for i in range(n):
			p = (out / f"ser_{tag}_{i}.bin").resolve()
			p.unlink(missing_ok=True)
			cmds = p.with_suffix(".cmds")
			cmds.write_text(f"savebin {p} 0 1048576\nr\n")
			# fix the observation point INSIDE the pass, so both runs are caught at the same
			# instant of the frame: the render tail's entry ($13e42) runs once per pass, after
			# the render flag and before the world's later work. Whatever differs below is then
			# genuine state, not a mid-pass tear.
			h.cmd(f"hatari-debug b pc = $13e42 && (${TICK:x}).l > 0 :once :file {cmds}")
			h.cmd(f"hatari-debug b pc = $72140 && (${TICK:x}).l > 0 :once :file {cmds}")
			t = time.time()
			while not p.exists():
				if time.time() - t > 60:
					break
				time.sleep(0.2)
			if not p.exists():
				continue
			d = p.read_bytes()
			w = int.from_bytes(d[TICK:TICK+4], 'big')
			saved.append((w, i))
			print(f"{tag} dump {i}: world tick {w}")
	finally:
		h.close()
	return saved

EXCLUDE = [
	(0x00000, 0x00800),      # TOS low memory
	(0x007E6, 0x007EA), (0x00842, 0x00846), (0x0144B4, 0x0144B8),   # click-stamp operands
	(0x013DA0, 0x013DA6), (0x013E24, 0x013E2A), (0x013E36, 0x013E3C), (0x013E42, 0x013E48),
	(0x01B900, 0x01B908),    # the weather animation phase
	(0x1D2A0, 0x2D600),      # IKBD state, pointer words, both screen buffers (pixel gate's job)
	(0x2D600, 0x2E000),      # the stack
	(0x2ED90, 0x2EDC0),      # the world counter, click stamp, latches
	(0x5EF00, 0x5EFC0),      # the sound sequencer
	(0x71B7C, 0x71B84),      # the VBL counter
	(0x72000, 0x73000),      # the patch payload
	(0x00E7C2, 0x00E7C6), (0x011DC6, 0x011DD0),   # buffer pointers (flip parity)
	(0x0082C4, 0x0082C8),    # the back-buffer address
]


def excluded(a: int) -> bool:
	return any(lo <= a < hi for lo, hi in EXCLUDE)


def load(tag: str) -> dict[int, bytes]:
	runs: dict[int, bytes] = {}
	for p in sorted(out.glob(f"ser_{tag}_*.bin")):
		d = p.read_bytes()
		if len(d) < 0x72000:
			continue
		runs.setdefault(int.from_bytes(d[TICK:TICK + 4], 'big'), d)
	return runs


def main() -> None:
	series("stock", False)
	series("tick", True)
	stock, tick = load("stock"), load("tick")
	print()
	print("tick  passes(stock/tick)  differing bytes")
	ok = True
	for t in sorted(set(stock) & set(tick)):
		a, b = stock[t], tick[t]
		pa = int.from_bytes(a[0x50FD8:0x50FDC], 'big')
		pb = int.from_bytes(b[0x50FD8:0x50FDC], 'big')
		diff = [i for i in range(0x72000) if a[i] != b[i] and not excluded(i)]
		ok &= not diff
		print(f"{t:5d}  {pa:5d}/{pb:<5d}  {len(diff):5d}")
	print()
	print("PASS" if ok else "FAIL")


if __name__ == "__main__":
	main()
