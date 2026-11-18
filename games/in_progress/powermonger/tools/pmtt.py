#!/usr/bin/env python3
"""Powermonger on the user's TT setup (dist/run_tt.sh options, headless): boot the all-games HD image, press P at the PMBOOT prompt.
    from pmtt import TT;  h = TT(img); h.start_game(); h.shot('x.png'); h.close()
The image is copied first (Powermonger writes its save file into it)."""
from __future__ import annotations
import shutil, sys, tempfile, time, os, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pm  # noqa: E402
from stharness import Hatari  # noqa: E402

IMG = HERE.parent.parent.parent.parent / "dist" / "AtariST_enhanced_games_2026-11-10.vhd"


class TT(pm.PM):          # PM's navigation methods; PM.__init__ is bypassed (the disk is the HD image)
    def __init__(self, img=IMG, machine="tt", tos="3.06", mem=4096, mhz=32, monitor="vga", sound=True, extra=(), fast_boot=False, **kw):
        R = Path(tempfile.mkdtemp(prefix="strun-"))
        home = R / "home"
        (home / ".config/hatari").mkdir(parents=True, exist_ok=True)
        txt = (Path.home() / ".config/hatari/hatari.cfg").read_text()
        txt = re.sub(r"(?m)^szMemoryCaptureFileName = .*$", f"szMemoryCaptureFileName = {R}/state.sav", txt)
        (home / ".config/hatari/hatari.cfg").write_text(txt)
        disk = R / "hd.img"
        shutil.copy(img, disk)
        ex = ["--monitor", monitor, "--gemdos-drive", "skip", "--acsi", f"0={disk}", "--fast-boot", "yes" if fast_boot else "no"]
        if machine in ("tt", "falcon") and mhz:
            ex += ["--cpuclock", str(mhz)]
        if sound:
            ex += ["--sound", "44100"]
        ex += list(extra)
        old = os.environ.get("HOME")
        os.environ["HOME"] = str(home)
        os.environ["SDL_AUDIODRIVER"] = "dummy"      # emulate the sound hardware, never play it on the host
        try:
            Hatari.__init__(self, game_dir=pm.GAME, workdir=str(R), extra=ex, machine=machine, tos=pm.TOS[tos] if tos in pm.TOS else Path(tos),
                            memsize_kb=mem, files=[], overlay=Path("/nonexistent"), autorun=None, **kw)
        finally:
            os.environ["HOME"] = old
        self.state = R / "state.sav"
        self.t0 = time.time()
        self.R_ = R

    def key(self, keysym, hold=0.15):
        # a key byte right after the game's ACIA reset deadlocks the keyboard (loading.md section 8): no space once stage 2 runs
        if keysym == "space" and self.peekw(0x10A6) == 0x41F9:
            return
        super().key(keysym, hold)

    def prompt_up(self) -> bool:
        """The HDDRIVER banner + PMBOOT line: white screen (>95 %) with 2..4 % dark text (any machine / screenshot size)."""
        from PIL import Image
        im = Image.open(self.shot()).convert("L")
        w, h = im.size
        a = list(im.crop((0, 0, w, h - 45)).getdata())
        return sum(1 for p in a if p > 200) > 0.95 * len(a) and sum(1 for p in a if p < 100) > 0.02 * len(a)

    def start_game(self, log=print, key="p", repeat=1):
        """Wait for the PMBOOT prompt (3 s window) and press P."""
        t = time.time()
        while not self.prompt_up():
            if time.time() - t > 120:
                raise RuntimeError("PMBOOT prompt never seen")
            time.sleep(0.1)
        for _ in range(repeat):           # the prompt is up for ~3 s; on some machines the first look is a false positive
            self.key(key)
            time.sleep(0.4)
        log(f"P pressed at VBL {self.vbl()}")

    def to_map(self, log=print, **kw):
        """PMBOOT -> P -> intro (skipped with space) -> name -> options -> chart -> island -> 3D map view."""
        self.start_game(log)
        return self.boot_to_game(log=log, **kw)


if __name__ == "__main__":
    print(pm.TOS.keys())
