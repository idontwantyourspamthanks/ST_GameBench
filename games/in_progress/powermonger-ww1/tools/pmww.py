#!/usr/bin/env python3
"""Powermonger WW1 Edition (Pompey Pirates #106, disks/pp106.st) navigation + state access
on top of tools/stharness.Hatari.

    import sys; sys.path.insert(0, '<gamebench>/tools'); sys.path.insert(0, '<game>/tools')
    from pmww import PMWW
    h = PMWW(); h.boot_to_game(); h.savemem(...); h.close()
"""

from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
BENCH = GAME.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
from stharness import Hatari, TOS, retarget_snapshot  # noqa: E402,F401

DISK = GAME / "disks" / "pp106.st"
# The two releases are the same engine at a constant offset (work/notes/cobra26.md):
# the Cobra #26 / Fuzion build's code and its runtime variables sit +$12686 from the Pompey
# build's. A few things do NOT shift: the IKBD packet buffer/pointer words ($1d2a0-$1d2c0,
# in the fixed IO page) and the file tables. `delta` selects the build.
# NB: the code shifts, the *variables* do not (the code references them absolutely).
DELTA = {"pp106": 0, "cobra26": 0}
FILES = GAME / "extracted" / "pp106"       # the disk's files as a folder (GEMDOS C:)
SNAP = GAME / "work" / "snapshots"
REF = GAME / "work" / "ref"

# gates: (reference crop in work/ref, box in 832x588 screenshot coordinates)
GATES = {
	"name": ("name_gate.png", (316, 276, 514, 304)),     # "Please enter your name"
	"opt": ("opt_gate.png", (326, 178, 514, 206)),       # "Please select option."
}


class PMWW(Hatari):
	def __init__(self, snapshot: str | None = None, workdir: str | None = None, disk: Path | None = DISK,
	             cpuclock: int | None = None, no_floppy: bool = False,
	             files_from: Path | None = None, **kw):
		R = Path(workdir or tempfile.mkdtemp(prefix="strun-"))
		R.mkdir(parents=True, exist_ok=True)
		home = R / "home"
		(home / ".config/hatari").mkdir(parents=True, exist_ok=True)
		txt = (Path.home() / ".config/hatari/hatari.cfg").read_text()
		txt = re.sub(r"(?m)^szMemoryCaptureFileName = .*$", f"szMemoryCaptureFileName = {R}/state.sav", txt)
		(home / ".config/hatari/hatari.cfg").write_text(txt)
		kw.setdefault("overlay", Path("/nonexistent"))
		kw.setdefault("autorun", None)
		if disk is None:
			# GEMDOS folder run: the disk's files as C:, the single-parted game autorun.
			# Pre-create the scratch drive (the harness only populates a missing one).
			# The game's own loader drives the FDC directly: put the real disk in A: too
			# (`extra=['--disk-a', ...]`) unless disk_b_none is set.
			drive = R / "C"
			drive.mkdir(parents=True, exist_ok=True)
			for src in sorted((files_from or FILES).iterdir()):
				if src.name == "AUTO":     # the PP menu hijacks any TOS boot (AUTO folder); run the game directly
					continue
				dst = drive / src.name
				if dst.exists():
					continue
				if src.is_dir():
					shutil.copytree(src, dst)
				else:
					shutil.copy(src, dst)
			kw.setdefault("files", [])
			kw["autorun"] = kw.pop("autorun_f", "C:\\WWIEDITN.PRG")
			if no_floppy:
				extra = list(kw.pop("extra", []))
			else:
				extra = ["--disk-a", str(R / "a.st"), "--protect-floppy", "off"] + list(kw.pop("extra", []))
				# the game's territory load goes through TOS's own GEMDOS/FDC and reads drive A:
				# (the PP crack only preloads the save-disk check file). Copy the real disk but
				# kill its boot sector so TOS keeps booting from C: and our --auto runs.
				raw = bytearray((FILES.parent.parent / "disks" / "pp106.st").read_bytes())
				raw[0:2] = b"\x00\x00"
				(R / "a.st").write_bytes(raw)
		else:
			a = R / "a.st"
			shutil.copy(disk, a)
			kw.setdefault("files", [])
			extra = ["--disk-a", str(a), "--protect-floppy", "off"] + list(kw.pop("extra", []))
		if snapshot:
			snap_in = R / "snap_in.sav"
			retarget_snapshot(snapshot, snap_in, R)
			snapshot = str(snap_in)
		old_home = os.environ.get("HOME")
		self.delta = DELTA.get(disk.stem, 0) if disk is not None else kw.pop("delta", 0)
		os.environ["HOME"] = str(home)
		try:
			super().__init__(game_dir=GAME, snapshot=snapshot, workdir=str(R), extra=extra, **kw)
		finally:
			os.environ["HOME"] = old_home
		if not snapshot:
			self.state = R / "state.sav"
		if cpuclock:
			self.set_cpuclock(cpuclock)


if __name__ == "__main__":
	# exploratory boot: folder run of the single-parted game by default, the PP menu floppy with --disk
	folder = "--disk" not in sys.argv
	out = Path(sys.argv[-1]) if not sys.argv[-1].startswith("--") else Path(tempfile.mkdtemp(prefix="pmww-boot-"))
	out = Path(out)
	out.mkdir(parents=True, exist_ok=True)
	h = PMWW(disk=None) if folder else PMWW()
	try:
		for i in range(24):
			time.sleep(5)
			h.shot(str(out / f"t{i:02d}.png"))
			print(f"t{i:02d} vbl={h.vbl()}")
	finally:
		h.close()
	print(f"shots in {out}")


def _methods():
	def mpos(self):
		"""Title/option-screen pointer words ($1d2b2/$1d2b4, ST pixels; fixed page, no delta)."""
		for _ in range(3):
			try:
				f = self.debug("m $1d2b2 4", wait=0.7).strip().splitlines()[-1].split(':')[1].split()
				return int.from_bytes(bytes.fromhex(f[0] + f[1]), 'big'), int.from_bytes(bytes.fromhex(f[2] + f[3]), 'big')
			except (IndexError, ValueError):
				time.sleep(0.3)
		raise RuntimeError("mpos: no memory dump from the debugger")

	def at_gate(self, gate: str, tol: float = 10.0) -> bool:
		"""Screenshot gates in 832x588 ST-screenshot coordinates (picture at (96,58))."""
		ref, box = GATES[gate]
		return self.screen_matches(REF / ref, box, tol)

	def boot_to_options(self, name: str = "BENCH", log=print, t_name: float = 120):
		"""Cold boot to the options screen (only reliable WITHOUT a floppy in A: the Alien's
		doc displayer hangs on a disk present at boot — run with no_floppy=True).

		Every stage is gated by its screenshot: the intro/docs (a burst of spaces to page past
		the crack intro, then silence — the docs exit on their own timing, extra presses reset
		it), then the name prompt: type `name` + Return -> the options screen -> poke the
		game's own mouse-enable word ($5a84e, its region-195 toggle action).
		"""
		t0 = time.time()
		stamp = lambda s: log(f"[{time.time() - t0:5.0f}s vbl {self.vbl()}] {s}")
		time.sleep(10)
		for _ in range(8):                   # page past the intro + the first docs pages
			self.key("space")
			time.sleep(1.4)
		t = time.time()
		while not self.at_gate("name"):
			if time.time() - t > t_name:
				raise RuntimeError("name prompt not reached")
			time.sleep(2.5)                   # silence: the docs exit on their own timer
		stamp("name prompt")
		for ch in name:
			self.key(ch)
			time.sleep(0.4)
		self.key("Return")
		t = time.time()
		while not self.at_gate("opt"):
			if time.time() - t > 40:
				raise RuntimeError("options screen not reached")
			self.key("Return")
			time.sleep(2.5)
		stamp("options screen")
		# the game's own mouse-toggle region action, applied directly (region 195 -> $14446)
		self.debug("w $5a84e 0 1", wait=0.5)
		return True

	def boot_to_map(self, log=print):
		"""From the options-screen snapshot to the 3D map view (the two-stage flow).

		Select Start New Conquest: poke-click the select box (112,72), then the row's
		activate spot (130,88); the chart comes up after ~6 s (a dim, live-rendered map
		screen). Click the island at (60,20) (the first territory, top left); the game
		generates the land in RAM (the Alien's ramdisk: no disk access on this path) and
		the 3D view appears after ~10 s more.
		"""
		t0 = time.time()
		stamp = lambda s: log(f"[{time.time() - t0:5.0f}s] {s}")
		time.sleep(2)
		self.poke_click(112, 72)                  # select "Start New Conquest"
		time.sleep(2.0)
		self.poke_click(130, 88)                   # activate it -> the chart
		stamp("chart loading")
		time.sleep(10)
		self.poke_click(60, 20)                    # the island territory (top left)
		stamp("island clicked; land generation")
		time.sleep(14)
		stamp("3D map view")
		return True

	def in_game(self) -> bool:
		"""The 3D view's render loop is running: the picture changes between frames."""
		a = self.shot()
		time.sleep(1.6)
		b = self.shot()
		from PIL import Image, ImageChops
		d = ImageChops.difference(Image.open(a).convert("L"), Image.open(b).convert("L"))
		bbox = d.getbbox()
		return bbox is not None and (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) > 2000

	def goto_st(self, x: int, y: int, tol: int = 1):
		"""Home the host pointer, then close the loop on the game's pointer words ($1d2b2/$1d2b4).

		The game re-programs the IKBD position every VBL from its own tracked position, and
		Hatari echoes that back as an absolute-position packet, so the tracked words are
		stable at wherever the host mouse last moved: normal h.rel() motion works.
		"""
		self.home()
		time.sleep(0.5)
		for _ in range(8):
			cx, cy = self.mpos()
			dx, dy = x - cx, y - cy
			if abs(dx) <= tol and abs(dy) <= tol:
				break
			self.rel(dx * 2, dy * 2, max(2, min(12, (abs(dx) + abs(dy)) // 4 + 1)))
			time.sleep(0.4)
		return self.mpos()

	def poke_click(self, x: int, y: int, hold: float = 0.3):
		"""Deterministic click through the game's own input path.

		Hatari only delivers absolute-mouse button packets together with movement, but this
		game re-programs the IKBD position every VBL, so a stationary host click never
		reaches it. Move the host pointer to the target first (the game tracks it through its
		position-forcing feedback: the tracked words hold the target while idle). Then write
		the buttons byte the packet parser would have written: $1d2af = 4 (left down). The
		VBL dispatch ($79a table) runs the game's own latch code ($81e: $2edb6 = 1, click
		pos $2edae/$2edb0 = the tracked words, down-seen $2edbc). The forcing feedback
		packets overwrite the poke within ~1 VBL, so re-arm it until the down-seen word
		proves the latch ran; 10 is the release event ($856: clears the down-seen flags),
		0 the idle poll path.
		"""
		d = self.delta
		self.goto_st(x, y)
		fired = False
		for _ in range(24):
			self.debug(f"w ${0x1d2af | 0:x} 4" if d == 0 else f"w ${0x1d2af + d:x} 4",
			           wait=hold if not fired else 0.12)
			f = self.debug(f"m ${0x2edbc + d:x} 2", wait=0.25).strip().splitlines()[-1].split(':')[1].split()
			if f[0] != "00" or f[1] != "00":      # the word $2edbc is set: the latch ran
				fired = True
				break
		self.debug(f"w ${0x1d2af + d:x} 10", wait=0.3)
		self.debug(f"w ${0x1d2af + d:x} 0", wait=0.3)
		if not fired:
			raise RuntimeError("poke_click: the game's latch never consumed the button event")

	for f in (mpos, at_gate, boot_to_options, boot_to_map, in_game, goto_st, poke_click):
		setattr(PMWW, f.__name__, f)

_methods()

