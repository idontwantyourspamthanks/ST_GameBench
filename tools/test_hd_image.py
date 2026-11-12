#!/usr/bin/env python3
r"""Boot one game from the all-games hard-disk image (tools/make_hd_image.py) in Hatari: ACSI + HDDRIVER, the real boot path.

    python3 tools/test_hd_image.py IMG GAME [--machine ste|megaste|tt|st] [--tos 1.62] [--mem 1024] [--saveload]
        GAME = mw1 | mw2 | hunter | pm

The image is never touched: a scratch copy gets a DESKTOP.INF with a `#Z` autorun line for the game (the shipped image has none), and, for
mw2, the created campaign disk from games/in_progress/midwinter2/work/disk_overlay as FILES\FFD (the shipped one is the blank campaign disk).  Then the
game's own harness navigates to its in-game view and the patch marker is read (MWPO / HNPO / PMPO).  Prints one `RESULT` line (raw).
--saveload (pm): saves and loads through the game's own menu and compares POWERMON\SAVEDISK.DAT on the image.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
class _Games:
    """`GAMES / "midwinter"` finds a game in whichever stage folder it lives (in_progress, done, queue)."""
    def __truediv__(self, name: str) -> Path:
        for stage in ("in_progress", "done", "queue"):
            p = ROOT / "games" / stage / name
            if p.is_dir():
                return p
        return ROOT / "games" / "in_progress" / name


GAMES = _Games()
sys.path.insert(0, str(ROOT / "tools"))
from stharness import Hatari, TOS  # noqa: E402
import make_hd_image as mk  # noqa: E402

AUTORUN = {"mw1": "C:\\MIDWINTR\\RUNME.TOS", "mw2": "C:\\MIDWINT2\\RUNME.TOS", "hunter": "C:\\HUNTER\\START.TOS", "pm": None}      # pm: started from the AUTO-folder boot prompt (press P), no autorun line
ENV = dict(os.environ, MTOOLS_SKIP_CHECK="1")
FIRST = mk.FIRST_LBA * mk.SECTOR


def autorun_inf(autorun: str) -> bytes:
    """The DESKTOP.INF that hunter.py build_hd uses (works with TOS 1.62 and 2.06 in Hatari): `#Z` = program run at desktop start."""
    return (("#a000000\r\n#b000000\r\n#c" + "7" * 65 + "\r\n#d\r\n#E 9B 01\r\n#W 00 00 10 01 4A 16 0F 0A C:\\*.*@\r\n"
             "#M 00 00 00 FF C HARD DISK@ @\r\n#T 00 00 03 FF   TRASH@ @\r\n" f"#Z 01 {autorun}@ @\r\n").encode("ascii"))


def test_image(src: Path, dst: Path, game: str, original: bool = False) -> Path:
    shutil.copy(src, dst)
    tgt = f"{dst}@@{FIRST}"
    inf = dst.with_suffix(".inf")
    if AUTORUN[game]:
        inf.write_bytes(autorun_inf(AUTORUN[game]))
        subprocess.run(["mcopy", "-o", "-i", tgt, str(inf), "::DESKTOP.INF"], check=True, env=ENV)
        inf.unlink()
    if original and game in ("mw1", "mw2"):       # the unpatched PP files in place of the patched RUNME.TOS + HAGA (to tell game limits from patch bugs)
        gd, folder = (GAMES / "midwinter", "MIDWINTR") if game == "mw1" else (GAMES / "midwinter2", "MIDWINT2")
        for f in ("RUNME.TOS", "HAGA"):
            subprocess.run(["mcopy", "-o", "-i", tgt, str(gd / f), f"::{folder}/{f}"], check=True, env=ENV)
    if game == "mw2":
        ffd = GAMES / "midwinter2" / "work" / "disk_overlay" / "FILES" / "FFD"
        subprocess.run(["mcopy", "-o", "-i", tgt, str(ffd), "::MIDWINT2/FILES/FFD"], check=True, env=ENV)
    return dst


def hunter_tt_boot(h):
    """The TT/Falcon boot screens differ from the STE crops the harness gates on `hw`/`title1`: same sequence as
    games/in_progress/hunter/tools/hunt_ttf.py (key at the HW screen, then gate on the animated title)."""
    wait_drive_c(h)
    time.sleep(3)
    h.keypress(57)
    time.sleep(3)
    for stage, wait, key in (("title2", 150, None), ("main", 40, "space"), ("games", 30, "start"), ("name", 30, "action"), ("mission", 30, "type"),
                             ("game", 60, "click")):
        if key == "space":
            time.sleep(1.5)
            h.key("space", 0.3)
        elif key == "start":
            h.goto(*h.START_XY, home_xy=h.HOME_XY)
            h.click()
        elif key == "action":
            h.goto(*h.ACTION_XY, home_xy=h.HOME_XY)
            h.click()
        elif key == "type":
            for c in "bench":
                h.key(c, 0.15)
                time.sleep(0.3)
            h.click()
        elif key == "click":
            h.click()
        if not h.wait_stage(stage, wait, 2):
            raise RuntimeError(f"screen {stage} not reached")
    time.sleep(1.0)
    if not h.in_game():
        raise RuntimeError("HUD matched but the 3D loop is not running")


def wait_drive_c(h, limit: float = 400):
    """Wait until HDDRIVER has installed drive C (_drvbits $4c2 bit 2).  Keys sent earlier (during the TOS 2.06 / 3.06 memory test)
    killed Hatari ("CPU halted", bombs on screen), so the navigation of every game starts only after this."""
    t = time.time()
    while time.time() - t < limit:
        try:
            if h.peekl(0x4C2) & 4:
                return time.time() - t
        except Exception:  # noqa: BLE001
            pass
        time.sleep(1)
    raise RuntimeError("drive C never appeared (HDDRIVER not booted?)")


def hd_args(R: Path):
    return ["--gemdos-drive", "skip", "--acsi", f"0={R / 'hd.img'}"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("img")
    ap.add_argument("game", choices=list(AUTORUN))
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--saveload", action="store_true")
    ap.add_argument("--original", action="store_true", help="mw1/mw2: run PP's unpatched RUNME.TOS + HAGA from the game dir instead of the patched ones")
    ap.add_argument("--keep", action="store_true", help="keep the scratch dir")
    a = ap.parse_args()
    R = Path(tempfile.mkdtemp(prefix="strun-"))
    SRC = test_image(Path(a.img), Path(tempfile.mkdtemp(prefix="hdsrc-")) / "test.img", a.game, a.original)
    if a.game in ("mw1", "mw2"):
        shutil.copy(SRC, R / "hd.img")
    kw = dict(machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem)
    mmu = ["--mmu", "true"] if a.machine == "tt" else []     # PP's HAGA on TOS 3.x needs the PMMU (dist/run_tt.sh)
    h = None
    tag = f"{a.game}{' UNPATCHED' if a.original else ''} {a.machine} TOS {a.tos} {a.mem}K"
    t0 = time.time()
    try:
        if a.game == "hunter":
            sys.path.insert(0, str(GAMES / "hunter" / "tools"))
            import hunter
            hunter.build_hd = lambda img, **k: shutil.copy(SRC, img)
            h = hunter.Hunter(workdir=str(R), **kw)
            stage = h._stage
            h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
            if a.machine == "st":
                import huntpatch
                huntpatch.blind_boot(h)
            elif a.machine in ("tt", "falcon"):
                hunter_tt_boot(h)
            else:
                h.boot_to_game()
            res = f"in_game={h.in_game()} MARKER={h.peek(0x8BFF8, 4)!r} FLAGS={h.peek(0x8BFF0, 4).hex()}"
        elif a.game == "mw1":
            sys.path.insert(0, str(GAMES / "midwinter" / "tools"))
            from mw1 import MW1
            h = MW1(workdir=str(R), files=[], autorun="", extra=hd_args(R) + mmu, **kw)
            wait_drive_c(h)
            h.boot_to_game("M")
            res = f"in_ski={h.in_ski()} MARKER={h.peek(0xB2FF8, 4)!r} state={h.gstate()}"
        elif a.game == "mw2":
            sys.path.insert(0, str(GAMES / "midwinter2" / "tools"))
            import mw2harness

            class MW2(Hatari):
                boot_to_game = mw2harness.Hatari.boot_to_game

            h = MW2(game_dir=GAMES / "midwinter2", workdir=str(R), files=[], overlay=Path("/nonexistent"), autorun="", extra=hd_args(R) + mmu, **kw)
            wait_drive_c(h)
            h.boot_to_game("M")
            res = (f"$6220={h.peekw(0x6220):#x} $700a={h.peekw(0x700A):#x} MARKER="
                   f"{(h.peekw(0xB2FF8).to_bytes(2, 'big') + h.peekw(0xB2FFA).to_bytes(2, 'big'))!r}")
        else:
            sys.path.insert(0, str(GAMES / "hunter" / "tools"))
            sys.path.insert(0, str(GAMES / "powermonger" / "tools"))
            import hunter
            import pmpatch
            hunter.build_hd = lambda img, **k: shutil.copy(SRC, img)     # pmpatch's ACSI mode asks hunter.build_hd for its image
            h = pmpatch.make_pm(None, GAMES / "powermonger" / "work", acsi=True, **kw)
            R = h.R
            # AUTO\\PMBOOT.PRG asks "Powermonger? P = start, else desktop" (waits 3 s; keys pressed earlier sit in TOS's buffer).
            # Keys sent during the TOS 2.06 memory test killed Hatari ("CPU halted"), so wait until HDDRIVER has installed drive C
            # (_drvbits $4c2 bit 2), then press P every second until the game's hd_core has taken TOS's snapshot (RAM $BC000 = 'HDSW').
            wait_drive_c(h)
            t = time.time()
            while time.time() - t < 60:
                h.key("p")
                time.sleep(1)
                try:
                    if h.peekl(0xBC000) == int.from_bytes(b"HDSW", "big"):
                        break
                except Exception:  # noqa: BLE001
                    pass
            else:
                raise RuntimeError("Powermonger was never started from the boot prompt")
            print(f"  game started from the AUTO prompt after {time.time() - t:.0f} s", flush=True)
            h.boot_to_game()
            mk_ = h.peekl(pmpatch.MARKER).to_bytes(4, "big")
            res = f"in_game={h.in_game()} MARKER={mk_!r} FLAGS={h.peekl(pmpatch.FLAGS):#x}"
            if a.saveload:
                ok = pmpatch.run_saveload(h, True)
                res += f" (run_saveload verdict {ok}: its SAVEDISK.DAT check looks in the root, ours is below)"
                sd = subprocess.run(["mcopy", "-i", f"{R / 'hd.img'}@@{FIRST}", "::POWERMON/SAVEDISK.DAT", str(R / "sd.dat")], capture_output=True, env=ENV)
                disk = (R / "sd.dat").read_bytes() if sd.returncode == 0 else b""
                sv = (R / "sl" / "save.bin").read_bytes()
                res += f" POWERMON\\SAVEDISK.DAT {len(disk)} B, slot A == saved state: {disk[512:512 + len(sv)] == sv}, sector 0 {disk[:4]!r}"
        print(f"RESULT {tag} OK {time.time() - t0:.0f}s {res}", flush=True)
        shots = ROOT / "dist" / "_shots"
        shots.mkdir(exist_ok=True, parents=True)
        h.shot(str(shots / f"{a.game}_{a.machine}_{a.tos}_{a.mem}.png"))
        return 0
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        print(f"RESULT {tag} FAILED {time.time() - t0:.0f}s {e!r}", flush=True)
        if h is not None:
            try:
                shots = ROOT / "dist" / "_shots"
                shots.mkdir(exist_ok=True, parents=True)
                h.shot(str(shots / f"FAIL_{a.game}_{a.machine}_{a.tos}_{a.mem}.png"))
            except Exception:  # noqa: BLE001
                pass
        return 1
    finally:
        if h is not None:
            h.close()
        shutil.rmtree(SRC.parent, ignore_errors=True)
        if not a.keep:
            shutil.rmtree(R, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
