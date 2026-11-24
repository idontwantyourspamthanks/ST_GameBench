#!/usr/bin/env python3
"""HD harness for the WW1 HD build (tools/wwpatch.py build --hd): the folder build/<x>/hd as drive C: of Hatari, either through Hatari's GEMDOS emulation (`--harddrive`)
or as a REAL ACSI disk with HDDRIVER (TOS's own GEMDOS + the resident driver, no GEMDOS emulation; gamebench/hd/ files, `hunter.build_hd` makes the image).
Master's HDPM (games/done/powermonger/tools/pmpatch.py) re-done for tools/pmww.py.

    h = wwhd.PMWHD(folder, acsi=False, workdir=..., machine='ste', tos=pmww.TOS['1.62'], memsize_kb=1024)
    h.boot_to_options(); h.options_to_map(noprot=True, swap=False); h.saveload_hd()
"""
from __future__ import annotations
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402
from pmww import PMW  # noqa: E402

BENCH = HERE.parent.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
from stharness import Hatari  # noqa: E402


class PMWHD(PMW):
    def __init__(self, folder: Path, acsi: bool = False, workdir: str | None = None, **kw):
        R = Path(workdir or tempfile.mkdtemp(prefix="strun-"))
        R.mkdir(parents=True, exist_ok=True)
        home = R / "home"
        (home / ".config/hatari").mkdir(parents=True, exist_ok=True)
        txt = (Path(os.environ["HOME"]) / ".config/hatari/hatari.cfg").read_text()
        txt = re.sub(r"(?m)^szMemoryCaptureFileName = .*$", f"szMemoryCaptureFileName = {R}/state.sav", txt)
        (home / ".config/hatari/hatari.cfg").write_text(txt)
        kw.setdefault("overlay", Path("/nonexistent"))
        kw.setdefault("autorun", None)
        extra = list(kw.pop("extra", []))
        self.acsi = acsi
        self.folder = Path(folder)
        if acsi:
            sys.path.insert(0, str(BENCH / "games" / "done" / "hunter" / "tools"))
            import hunter  # noqa: E402
            self.img = R / "hd.img"
            hunter.build_hd(self.img, game=self.folder, autorun="C:\\NONE.TOS")
            extra += ["--gemdos-drive", "skip", "--acsi", f"0={self.img}"]
            kw["files"] = []
        else:
            kw["files"] = [p.name for p in self.folder.iterdir()]
        old = os.environ["HOME"]
        os.environ["HOME"] = str(home)
        try:
            Hatari.__init__(self, game_dir=self.folder, workdir=str(R), extra=extra, **kw)
        finally:
            os.environ["HOME"] = old
        self.state = R / "state.sav"
        self.disk_copy = None

    def host_savedisk(self) -> bytes:
        """SAVEDISK.DAT as the host sees it (the GEMDOS drive folder, or read back out of the ACSI image with mcopy)."""
        if not self.acsi:
            return (self.R / "C" / "SAVEDISK.DAT").read_bytes()
        out = self.R / "sd_out.dat"
        out.unlink(missing_ok=True)
        ps = 2 * 512
        subprocess.run(["mcopy", "-n", "-i", f"{self.img}@@{ps}", "::SAVEDISK.DAT", str(out)], check=True, env=dict(os.environ, MTOOLS_SKIP_CHECK="1"))
        return out.read_bytes()

    def saveload_hd(self, log=print) -> dict:
        """Option -> FILE -> SAVE (slot A, SAVEDISK.DAT through hd_sector), let the world run, Option -> FILE -> LOAD.  Same captures as PMW.saveload: the state ($44c3e, $c6 sectors) at the
        write call ($1cbc2) and right after the read call returns ($1cb2a); SAVEDISK.DAT (flushed) is compared with the saved bytes."""
        out = self.R / "sl"
        out.mkdir(exist_ok=True)
        for f in out.glob("*.bin"):
            f.unlink()
        n = pmww.SAVE_LEN
        (out / "sv.txt").write_text(f"savebin {out}/save.bin ${pmww.SAVE_BASE:x} ${n:x}\n")
        (out / "ld.txt").write_text(f"savebin {out}/load.bin ${pmww.SAVE_BASE:x} ${n:x}\n")
        self.debug("b all", 0.3)
        self.cmd(f"hatari-debug b pc = ${pmww.SAVE_WRITE_CALL:x} :trace :once :file {out / 'sv.txt'}")
        self.click_st(*pmww.OPTION_XY, wait=2.0)
        self.click_st(*pmww.FILE_BTN_XY, wait=2.0)
        self.click_st(*pmww.SAVE_BTN_XY, wait=3.0)
        t = time.time()
        while not (out / "save.bin").exists() or (out / "save.bin").stat().st_size < n:
            if time.time() - t > 90:
                self.shot(str(self.R / "shots" / "saveload_hd_stuck.png"))
                raise RuntimeError(f"the save never reached the sector driver (window text: {self.wtext().strip()[:60]!r})")
            if "OVERWRITE" in self.wtext().upper() or "ALREADY" in self.wtext().upper():
                self.click_st(*pmww.REQ_OK_XY, wait=2.0)
            time.sleep(1)
        while time.time() - t < 240 and not (self.peekw(pmww.WINDOW_OPEN) == 0 and self.ticking(1.5)):
            time.sleep(2)
        time.sleep(6)
        self.debug(f"savebin {out}/pre.bin ${pmww.SAVE_BASE:x} ${n:x}", 3.0)
        self.debug("b all", 0.3)
        self.cmd(f"hatari-debug b pc = ${pmww.SAVE_READ_RET:x} :trace :once :file {out / 'ld.txt'}")
        self.click_st(*pmww.OPTION_XY, wait=2.0)
        self.click_st(*pmww.FILE_BTN_XY, wait=2.0)
        self.click_st(*pmww.LOAD_BTN_XY, wait=3.0)
        t = time.time()
        while not (out / "load.bin").exists() or (out / "load.bin").stat().st_size < n:
            if time.time() - t > 120:
                self.shot(str(self.R / "shots" / "load_stuck.png"))
                raise RuntimeError(f"the load never returned (window text: {self.wtext().strip()[:80]!r})")
            time.sleep(1)
        time.sleep(3)
        ok_run = self.ticking(2.0) and self.peekw(pmww.WINDOW_OPEN) == 0
        sv, pre, ld = ((out / f"{k}.bin").read_bytes() for k in ("save", "pre", "load"))
        time.sleep(1)
        disk = self.host_savedisk()
        return dict(n=n, d_saved_loaded=sum(a != b for a, b in zip(sv, ld)), d_saved_pre=sum(a != b for a, b in zip(sv, pre)),
                    disk_eq=disk[512:512 + n] == sv, disk_len=len(disk), slot_flag=disk[pmww.SLOT_FLAG_OFF], ticking=ok_run)
