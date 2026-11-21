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
FILES = GAME / "extracted" / "pp106"       # the disk's files as a folder (GEMDOS C:)
SNAP = GAME / "work" / "snapshots"
REF = GAME / "work" / "ref"


class PMWW(Hatari):
	def __init__(self, snapshot: str | None = None, workdir: str | None = None, disk: Path | None = DISK,
	             cpuclock: int | None = None, **kw):
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
			for src in sorted(FILES.iterdir()):
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
		"""Title/option-screen pointer words ($1d2b2/$1d2b4, ST pixels)."""
		for _ in range(3):
			try:
				f = self.debug("m $1d2b2 4", wait=0.7).strip().splitlines()[-1].split(':')[1].split()
				return int.from_bytes(bytes.fromhex(f[0] + f[1]), 'big'), int.from_bytes(bytes.fromhex(f[2] + f[3]), 'big')
			except (IndexError, ValueError):
				time.sleep(0.3)
		raise RuntimeError("mpos: no memory dump from the debugger")

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

	def poke_click(self, x: int, y: int, hold: float = 0.4):
		"""Deterministic click through the game's own input path.

		Hatari only delivers absolute-mouse button packets together with movement, but this
		game re-programs the IKBD position every VBL, so a stationary host click never
		reaches it. Move the host pointer to the target first (the game tracks it through its
		own position-forcing feedback), then write the buttons byte the packet parser would
		have written: $1d2af = 4 (left down). The VBL dispatch ($79a table) then runs the
		game's own latch code ($81e: $2edb6 = 1, click pos $2edae/$2edb0 = the tracked words).
		10 is the release event ($856: clears the down-seen flags), 0 the idle poll path.
		"""
		self.goto_st(x, y)
		self.debug("w $1d2af 4", wait=hold)
		self.debug("w $1d2af 10", wait=0.3)
		self.debug("w $1d2af 0", wait=0.3)

	for f in (mpos, goto_st, poke_click):
		setattr(PMWW, f.__name__, f)

_methods()

