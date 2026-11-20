#!/usr/bin/env python3
r"""PSG (YM port A/B direction) gate for the Hunter sound patch: strict Hatari + tools/psgcheck.py.  Notes: work/notes/psg.md.

    python3 tools/hunt_psg.py CELL --kind hd|floppy|floppy2 --src ZIP_OR_DIR --machine st|ste|megaste|tt [--mhz 8|16] [--save]

CELL is a label.  --src is a shipped zip (or an extracted dir: HUNTER/ for hd, the .st files for floppy).  Cold boots with sound ON, the YM
trace streamed into psgcheck, the strict Hatari build; the game is driven to the 3D view; floppy cells with --save also do the game's own
Save and Load (FDC write and read after the sound patch took over the YM).  Prints: boot result, psgcheck summary, every reg-7 data write
(value, pc; consecutive duplicates collapsed) and the FDC command count after the last reg-7 write.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
import snd_test  # noqa: E402
from stharness import TOS  # noqa: E402

CFG = {"st": ("1.04", 1024, []), "ste": ("1.62", 1024, []), "megaste": ("2.06", 4096, []),
       "tt": ("3.06", 4096, ["--mmu", "true", "--monitor", "vga", "--cpuclock", "32"])}


def unpack(src: Path, kind: str) -> Path:
    if src.suffix == ".st":                              # the unpatched Paper Bag floppy image (original-game control)
        d = Path(tempfile.mkdtemp(prefix="hpsg-src-"))
        shutil.copy(src, d / "HUNTER_disk1.st")
        return d
    if src.is_dir() and kind == "hd" and not (src / "HUNTER").is_dir():     # the unpatched original game folder (PP's files)
        d = Path(tempfile.mkdtemp(prefix="hpsg-src-"))
        (d / "HUNTER").symlink_to(src.resolve())
        return d
    if src.is_dir():
        return src
    d = Path(tempfile.mkdtemp(prefix="hpsg-src-"))
    zipfile.ZipFile(src).extractall(d)
    return d


def reg7(kept: Path):
    out, last, fdc_after, seen = [], None, 0, 0
    for ln in kept.read_text(errors="replace").splitlines():
        m = re.match(r"ym write data reg=0x7 val=0x([0-9a-f]+).*?pc=([0-9a-f]+)", ln)
        if m:
            k = (m.group(1), m.group(2))
            if k != last:
                out.append(k)
            last = k
            if 0x8E000 <= int(m.group(2), 16) <= 0x8EFFF:     # the sound patch's own write (snd_ymsilence): count the FDC commands after it
                seen += 1
        elif ln.startswith("fdc ") and seen:
            fdc_after += 1
    return out, fdc_after, seen


def drive(h, kind, machine, save):
    import huntvis_cold as vc
    import huntpatch
    if CFG[machine][1] >= 2048:                          # 2 MB+: the Amiga dashboard replaces the HUD the 'game' crop shows: gate on the 3D loop instead
        stage = h._stage

        def st(name, record, wait, timeout=120):
            if name != "game":
                return stage(name, record, wait, timeout)
            t = time.time()
            while time.time() - t < 400:
                if h.in_game():
                    return
                time.sleep(2)
            raise RuntimeError("3D loop not reached")
        h._stage = st
    if kind == "hd":
        if machine == "ste":
            vc.harden(h)
            h.boot_to_game()
        elif machine in ("st", "tt"):
            vc.harden(h)
            huntpatch.blind_boot(h)
        else:                                            # megaste: slow TOS 2.06 boot; STE crops, loose tolerance, long time-outs
            import test_hd_image as thi
            vc.harden(h)
            thi.wait_drive_c(h)
            h._stage("hw", False, 12, 400)
            h.keypress(57)
            h._stage("title1", False, 6, 400)
            h.keypress(57)
            h._stage("title2", False, 22, 400)
            time.sleep(1.5)
            h.key("space", 0.3)
            h._stage("main", False, 3, 400)
            h.goto(*h.START_XY, home_xy=h.HOME_XY)
            h.click()
            h._stage("games", False, 3, 400)
            h.goto(*h.ACTION_XY, home_xy=h.HOME_XY)
            h.click()
            h._stage("name", False, 3, 400)
            for c in "bench":
                h.key(c, 0.15)
                time.sleep(0.3)
            h.click()
            h._stage("mission", False, 4, 400)
            h.click()
            h._stage("game", False, 9, 400)
            time.sleep(1.0)
        ok = h.in_game()
    else:
        vc.harden(h)
        ok = h.boot_floppy("swap" if kind == "floppy2" and machine != "st" else "none", pb_key_at=12 if machine in ("st", "ste") else 120)
    print(f"BOOT in_game={ok} MARKER={h.peek(0x8BFF8, 4)!r} FLAGS={h.peek(0x8BFF0, 4).hex()}", flush=True)
    if ok:
        h.hold("Up")
        time.sleep(6)
        h.release("Up")
        if save and kind != "hd":
            h.walk(2, "Up")
            print("saving", flush=True)
            h.save(2, "psg")
            print("saved", flush=True)
            h.walk(2, "Up", "Left")
            try:
                h.load(2)
            except RuntimeError:                         # the click that leaves the mission page can be lost: click again
                h.click()
                h.wait_game(40)
            print(f"SAVE+LOAD done, in_game={h.in_game()}", flush=True)
        time.sleep(2)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cell")
    ap.add_argument("--kind", required=True, choices=["hd", "floppy", "floppy2"])
    ap.add_argument("--src", required=True)
    ap.add_argument("--machine", default="ste", choices=list(CFG))
    ap.add_argument("--mhz", type=int, default=0)
    ap.add_argument("--plain", action="store_true", help="control: sound ON only, stock Hatari, no trace (A/B for harness problems)")
    ap.add_argument("--title", type=int, default=0, help="only sit through the boot and the title tune for this many seconds (no navigation)")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--realfdc", action="store_true", help="real FDC timing (default --fastfdc yes: the Save/Load menus time out otherwise)")
    a = ap.parse_args()
    snd_test.setup_home()
    os.environ["HOME"] = str(snd_test.HOME)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    src = unpack(Path(a.src), a.kind)
    tos, mem, extra = CFG[a.machine]
    if a.mhz and a.machine == "megaste":
        extra = ["--cpuclock", str(a.mhz)]
    kw = dict(sound=True) if a.plain else dict(sound=True, trace_psg=True, strict=True)
    print(f"CELL {a.cell}: kind={a.kind} machine={a.machine} mhz={a.mhz or 'default'} src={a.src}", flush=True)
    h = None
    ok = False
    try:
        if a.kind == "hd":
            import hunter
            orig = hunter.build_hd
            hunter.build_hd = lambda img, **k: orig(img, game=src / "HUNTER", **k)
            try:
                h = hunter.Hunter(machine=a.machine, tos=TOS[tos], memsize_kb=mem, extra=extra, **kw)
            finally:
                hunter.build_hd = orig
        else:
            import huntsave
            d1 = src / "HUNTER_disk1.st"
            d2 = src / "HUNTER_disk2_sound.st" if a.kind == "floppy2" else None
            h = huntsave.FloppyRig(d1, disk2=d2, drives=1, machine=a.machine, tos=TOS[tos], memsize_kb=mem, extra=extra,
                                   fastfdc="no" if a.realfdc else "yes", **kw)
        if a.title:
            time.sleep(a.title)
            for _ in range(4):                       # SPACE ends the title tune (it stops the music: the reg-7 writes of the tune's end)
                h.key("space", 0.3)
                time.sleep(5)
            time.sleep(15)
            ok = True
        else:
            ok = drive(h, a.kind, a.machine, a.save)
    except Exception as e:  # noqa: BLE001
        print(f"DRIVE FAILED: {e!r}", flush=True)
        try:
            h.shot(f"/tmp/hpsg_fail_{a.cell}.png")
        except Exception:  # noqa: BLE001
            pass
    finally:
        if h:
            if hasattr(h, "d1"):                       # HunterFloppy.close() would delete the run dir (and the kept trace) with the disk copy
                scratch, h.d1 = h.d1.parent, Path("/nonexistent/hd1.st")
            h.close()
    res = h.psg_check() if h and not a.plain else None
    hist, fdc_after, nsil = reg7(h.psg_kept) if h and not a.plain else ([], 0, 0)
    if h and res:
        shutil.copy(h.psg_kept, GAME / "work" / "psg" / f"{a.cell}.kept")
    print("REG7 writes (val, pc):", " ".join(f"${v}@{p}" for v, p in hist[:40]))
    print(f"snd_ymsilence reg-7 writes (3D entries): {nsil}; FDC commands after the first one: {fdc_after}")
    print(f"RESULT {a.cell}: boot={'OK' if ok else 'FAIL'} psgcheck={'PASS' if res and res.ok else 'FAIL'}")
    if h and hasattr(h, "d1"):
        shutil.rmtree(scratch, ignore_errors=True)
    return 0 if ok and res and res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
