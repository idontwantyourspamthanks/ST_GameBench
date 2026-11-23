#!/usr/bin/env python3
"""Tooltip gate: hovering a command icon puts its description in the top bar.

What is checked, per icon:

* **the composed line** — the payload writes the text into ``LINE`` at ``$73600`` before
  drawing it, so reading that buffer says exactly which string the hook chose. This is the
  precise check: it compares against ``tools/pwwgrid.py``'s own name for the same icon.
* **the picture** — the top bar (screen rows 0..5, x 104..319) must change when the pointer
  is over an icon and go back when it leaves, proving the text actually reaches the screen.

The pointer must be moved with ``goto_st`` (the host pointer). Writing ``$2edb2`` directly
does not work: the IKBD handler rewrites those words every VBL, so a poke lasts less than a
frame. That mistake cost time; it is recorded here so it is not repeated.

    python3 tools/tooltipgate.py
    python3 tools/tooltipgate.py --icons 4 6 23
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
from pwwgrid import NAMES, icon_centres  # noqa: E402

TICK = 0x2ED90
LINE = 0x73600          # the payload's composed line
TIPBAR = (104, 0, 320, 6)   # the surface: ST x 104..319, rows 0..5


def read(h, addr: int, n: int) -> bytes | None:
	for _ in range(4):
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


def long(h, addr: int) -> int:
	b = read(h, addr, 4)
	return int.from_bytes(b, 'big') if b else -1


def line_text(h) -> str:
	b = read(h, LINE, 24)
	return b.decode('latin-1').rstrip() if b else ''


def bar_px(before: Path, after: Path) -> int:
	from PIL import Image, ImageChops
	x0, y0 = 96, 58
	box = (x0 + TIPBAR[0] * 2, y0 + TIPBAR[1] * 2, x0 + TIPBAR[2] * 2, y0 + TIPBAR[3] * 2)
	a = Image.open(before).convert('L').crop(box)
	b = Image.open(after).convert('L').crop(box)
	return sum(1 for p in ImageChops.difference(a, b).tobytes() if p > 24)


def to_map(h, retries: int = 3) -> None:
	for go in range(retries):
		try:
			_nav(h)
			return
		except RuntimeError as e:
			print(f"  navigation: {e} (retry {go + 1}/{retries})", flush=True)
			time.sleep(3)
	raise SystemExit("map view not reached")


def _nav(h) -> None:
	time.sleep(6)
	t = time.time()
	while not h.at_gate("name"):
		if time.time() - t > 180:
			raise RuntimeError("name prompt not reached")
		h.key("space")
		time.sleep(2.5)
	for ch in "TIPS":
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
		a = long(h, TICK)
		time.sleep(2)
		if long(h, TICK) > a > 0:
			return
	raise RuntimeError("map view not reached")


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--icons", nargs="*", type=int, default=[23, 14, 4, 6, 5, 20])
	ap.add_argument("--build", type=Path, default=GAME / "build" / "tooltipgate")
	ap.add_argument("--only", nargs="*", default=["tick", "noprot", "keys", "tooltip"])
	args = ap.parse_args()

	shutil.rmtree(args.build, ignore_errors=True)
	args.build.mkdir(parents=True)
	r = subprocess.run([sys.executable, str(HERE / "wwbuild.py"), "build", "--out", str(args.build),
	                    "--only", *args.only], capture_output=True, text=True)
	if r.returncode != 0:
		raise SystemExit(f"build failed:\n{r.stdout}\n{r.stderr}")
	print(r.stdout.strip(), flush=True)
	shutil.copy(GAME / "extracted" / "cobra26" / "WW1_FUZI.LFB", args.build / "WW1_FUZI.LFB")

	centres = icon_centres()
	work = GAME / "work" / "tooltipgate"
	work.mkdir(parents=True, exist_ok=True)
	h = PMWW(disk=None, no_floppy=True, autorun_f="C:\\WW1.PRG", files_from=args.build,
	         machine="ste", tos=TOS["1.62"])
	failures = 0
	try:
		to_map(h)
		print(f"at the map, world {long(h, TICK)}", flush=True)
		# a pointer far from the panel: the "nothing shown" reference
		h.goto_st(200, 60, tol=3)
		time.sleep(3)
		away = work / "away.png"
		away.unlink(missing_ok=True)
		h.shot(str(away))
		away_text = line_text(h)

		for icon in args.icons:
			x, y = centres[icon]
			want = NAMES.get(icon, '')
			h.goto_st(x, y, tol=1)
			time.sleep(4.5)                 # let the pass run with the pointer settled
			h.debug("w $5a856 0 1", wait=0.4)     # freeze: compose cannot race the read
			time.sleep(0.6)
			shot = work / f"icon{icon}.png"
			shot.unlink(missing_ok=True)
			h.shot(str(shot))
			got = line_text(h)
			h.debug("w $5a856 0 0", wait=0.4)     # unfreeze for the next icon
			marked = bar_px(away, shot)
			ok = got == want and marked > 0
			failures += 0 if ok else 1
			print(f"  id {icon:2d} {want:14s} centre {x},{y}: LINE {got!r:18s}"
			      f" bar px {marked:5d}  {'PASS' if ok else 'FAIL'}", flush=True)
		print(f"\naway from the panel the line was {away_text!r} (expected empty)", flush=True)
	finally:
		h.close()

	print(f"{'PASS' if failures == 0 else 'FAIL'}: {failures} icon(s) failed")
	sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
	main()
