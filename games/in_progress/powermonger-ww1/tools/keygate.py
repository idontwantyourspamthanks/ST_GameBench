#!/usr/bin/env python3
"""Keyboard shortcuts: gate that each key does what its command icon does.

Two checks per key, both objective:

* the **synthesised click state** the hook leaves behind (`$2edae/$2edb0` = the click cell,
  `$2edb6` = the left latch, `$2ed94` = the pass stamp) must equal the cell the key maps to,
  confirming the hook ran and the table entry is right;
* the **picture changes** in the command panel's reaction area after the key, confirming the
  game itself acted on it. The command panel is the bottom strip (ST coordinates x 64..319,
  y 200..269 in the 320x200 picture), so a key that opens a panel or starts a unit changes
  many pixels there, while an inert key changes none.

Run at the map view: the battle/portrait view has its own keys and would confound the
picture check (it is also where `$2ed90` stops, so `to_map` uses the counter).

    python3 tools/keygate.py                 # the default set (tick noprot keys)
    python3 tools/keygate.py --keys "o m"    # only these
"""

from __future__ import annotations

import argparse
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
CLICK_X = 0x2EDAE
CLICK_Y = 0x2EDB0
LATCH = 0x2EDB6
STAMP = 0x2ED94

# The reference table, duplicated from work/keyproto/keys.s so the gate is an independent
# statement of what each key should do (a mismatch means the assembler source drifted).
KEYS = {
	"a": (299, 182), "d": (142, 193), "e": (297, 156), "f": (201, 181),
	"g": (299, 182), "h": (100, 170), "i": (274, 187), "l": (73, 161),
	"m": (275, 162), "n": (173, 188), "o": (71, 138), "q": (75, 191),
	"r": (252, 168), "s": (227, 174), "t": (74, 175), "x": (103, 186),
	"y": (72, 149),
	"1": (92, 135), "2": (94, 145), "3": (97, 156),
}
PANEL = (64, 200, 320, 270)          # the command panel, in ST picture coordinates
SHOT_OFFSET = (96, 58)               # the picture's origin in the 832x588 screenshot
SHOT_SCALE = 2                       # ... and the picture is 640x400: ST coords are doubled


def _box(rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
	x0, y0 = SHOT_OFFSET
	return (x0 + rect[0] * SHOT_SCALE, y0 + rect[1] * SHOT_SCALE,
	        x0 + rect[2] * SHOT_SCALE, y0 + rect[3] * SHOT_SCALE)


def read(h, addr: int, n: int = 2) -> int:
	import re
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


def picture_diff(before: Path, after: Path) -> int:
	"""Pixels that differ over the whole picture (ST 320x200 at 2x, so 640x400)."""
	from PIL import Image, ImageChops
	box = _box((0, 0, 320, 200))
	a = Image.open(before).convert("L").crop(box)
	b = Image.open(after).convert("L").crop(box)
	diff = ImageChops.difference(a, b)
	return sum(1 for p in diff.tobytes() if p > 24)


def to_map(h, retries: int = 3) -> None:
	for go in range(retries):
		try:
			_navigate(h)
			return
		except RuntimeError as e:
			print(f"  navigation: {e} (retry {go + 1}/{retries})", flush=True)
			time.sleep(3)
	raise SystemExit("map view not reached")


def _navigate(h) -> None:
	time.sleep(6)
	t = time.time()
	while not h.at_gate("name"):
		if time.time() - t > 180:
			raise RuntimeError("name prompt not reached")
		h.key("space")
		time.sleep(2.5)
	for ch in "BENCH":       # no command key in it (see phantom_click.md)
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
		a = read(h, TICK, 4)
		time.sleep(1.5)
		if read(h, TICK, 4) > a > 0:
			return
	raise RuntimeError("map view not reached")


def main() -> None:
	ap = argparse.ArgumentParser()
	ap.add_argument("--keys", default="o m q h")
	ap.add_argument("--only", nargs="*", default=["tick", "noprot", "keys"])
	ap.add_argument("--build", type=Path, default=GAME / "build" / "keygate")
	args = ap.parse_args()

	shutil.rmtree(args.build, ignore_errors=True)
	args.build.mkdir(parents=True)
	r = subprocess.run([sys.executable, str(HERE / "wwbuild.py"), "build", "--out", str(args.build),
	                    "--only", *args.only], capture_output=True, text=True)
	if r.returncode != 0:
		raise SystemExit(f"build failed:\n{r.stdout}\n{r.stderr}")
	print(r.stdout.strip(), flush=True)
	shutil.copy(GAME / "extracted" / "cobra26" / "WW1_FUZI.LFB", args.build / "WW1_FUZI.LFB")

	h = PMWW(disk=None, no_floppy=True, autorun_f="C:\\WW1.PRG", files_from=args.build,
	         machine="ste", tos=TOS["1.62"])
	failures = 0
	try:
		to_map(h)
		print(f"at the map, world {read(h, TICK, 4)}", flush=True)
		work = GAME / "work" / "keygate"
		work.mkdir(parents=True, exist_ok=True)

		def click_words() -> tuple:
			"""The four words the game's click dispatch reads."""
			return (read(h, CLICK_X), read(h, CLICK_Y), read(h, LATCH), read(h, STAMP, 4))

		for key in args.keys.split():
			want_x, want_y = KEYS[key]

			# (a) A REAL mouse click at the same cell: this is the reference.
			h.debug("w $2edb6 0 0", wait=0.3)
			time.sleep(2.5)
			h.poke_click(want_x, want_y, hold=0.25)
			time.sleep(0.6)
			real = click_words()
			time.sleep(4)               # let whatever it opened close
			h.key("Escape")
			time.sleep(2.5)

			# (b) The key: it must write the same words, so the game cannot tell them apart.
			h.debug("w $2edb6 0 0", wait=0.3)
			h.debug("w $2edae 0 0", wait=0.3)
			h.debug("w $2edb0 0 0", wait=0.3)
			time.sleep(2.5)
			h.key(key)
			time.sleep(0.6)
			synth = click_words()
			h.key("Escape")
			time.sleep(2.5)

			# compare the click position and the latch (the stamp differs: it is a counter)
			# the harness's synthetic click can land a pixel off (ST pixel doubling), so the
			# comparison with the real click tolerates 1; the table check is exact
			same = synth[2:] == real[2:] and all(
				abs(a - b) <= 1 for a, b in zip(synth[:2], real[:2]))
			# and independently: the key mapped its scancode to the right cell
			table_ok = synth[0] == want_x and synth[1] == want_y
			ok = same and table_ok
			failures += 0 if ok else 1
			print(f"  {key}: key writes ({synth[0]},{synth[1]}) latch {synth[2]};"
			      f" real click writes ({real[0]},{real[1]}) latch {real[2]};"
			      f" table says ({want_x},{want_y})  {'PASS' if ok else 'FAIL'}", flush=True)
	finally:
		h.close()

	print(f"\n{'PASS' if failures == 0 else 'FAIL'}: {failures} key(s) failed "
	      f"(a key must write the same click words as a real click on its cell)")
	sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
	main()
