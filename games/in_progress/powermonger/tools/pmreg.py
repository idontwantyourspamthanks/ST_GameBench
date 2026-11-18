#!/usr/bin/env python3
"""One regression cell for the release build (work/notes/regression.md): cold boot -> map view -> get_men, with
marker/FLAGS, protection, tooltip, sound and fps / world ticks per second.

    python3 tools/pmreg.py --disk build/reg/floppy/powermonger.st --machine ste --tos 1.62 --mem 1024
    python3 tools/pmreg.py --hd build/reg/hd --acsi --saveload --machine megaste --tos 2.06 --mem 4096 --mhz 8 16
    python3 tools/pmreg.py --disk disks/protected.st --original ...        # the unpatched floppy (no marker, no tick patch)

Every measurement prints one `RESULT ...` line (raw numbers); `CELL ...` lines summarise the checks.  Windows are
--vbls VBLs long; emulated seconds = VBLs / refresh (the refresh is read from the shifter sync mode $ff820a, bit 1 = 50 Hz).
"""
from __future__ import annotations

import argparse
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent.parent.parent / "tools"), str(HERE)]
import pmpatch  # noqa: E402
import pmtick  # noqa: E402
from pm import TOS, GETMEN_XY  # noqa: E402


def rdb(h, addr):
    return pmtick.rd(h, addr, 1)[0]


def flips_over(h, vbls):
    """(flips, VBLs) counted by changes of $ff8201 over `vbls` VBLs (Hatari.fps() assumes 50 Hz, so only the counts are used)."""
    r = h.fps(vbls)
    return r["flips"], r["vbls"]


def measure(h, tag, vbls, patched):
    sync = rdb(h, 0xFF820A)
    hz = 50 if sync & 2 else 60
    flips, dv_f = flips_over(h, vbls)
    ex = ["VBL", "CycleCounter", f"(${pmtick.TICKCNT:x}).l", f"(${pmtick.ITER:x}).l"]
    s0 = pmtick.sample_at(h, h.vbl() + 40, ex)
    s1 = pmtick.sample_at(h, s0["VBL"] + vbls, ex)
    dv = s1["VBL"] - s0["VBL"]
    secs = dv / hz
    cyc = ((s1["CycleCounter"] - s0["CycleCounter"]) & 0xFFFFFFFF) / dv
    t = s1[ex[2]] - s0[ex[2]]
    it = s1[ex[3]] - s0[ex[3]]
    print(f"RESULT {tag}: sync ${sync:02x} ({hz} Hz), fps {flips / (dv_f / hz):.2f} ({flips} flips / {dv_f} VBL), "
          f"{dv} VBL = {secs:.1f} s, {cyc:.0f} cycles/VBL, world ticks {t} = {t / secs:.3f}/s, loop passes {it} = {it / secs:.2f}/s", flush=True)
    return dict(tag=tag, hz=hz, fps=round(flips / (dv_f / hz), 2), ticks=round(t / secs, 3), cyc=round(cyc))


def sample_sound(h, flags, n=40):
    """DMA sound: FLAGS bit0, plus how often the DMA control register $ff8901 bit0 (play) was seen set while the game ran
    (STE class); plain ST: timer A control $fa19 (the YM sample IRQ) and the player's busy flag $2c993."""
    dma = busy = ta = 0
    for _ in range(n):
        if flags & 1:
            dma += rdb(h, 0xFF8901) & 1
        else:
            ta += 1 if (rdb(h, 0xFA19) & 7) else 0
        busy += 1 if rdb(h, 0x2C993) else 0
        time.sleep(0.25)
    print(f"RESULT sound: FLAGS={flags:#x} (bit0 DMA {flags & 1}), samples {n}: $ff8901 bit0 set {dma}, timer A running {ta}, player busy flag {busy}", flush=True)
    return dict(dma=dma, ta=ta, busy=busy)


def tooltip(h):
    """Pointer away from every icon vs on the Get Men icon: pixels that change in the top bar's free area (ST x 112..319, rows 0..5)."""
    from PIL import Image, ImageChops
    h.goto_st(150, 100)
    time.sleep(1.5)
    a = Image.open(h.shot()).convert("RGB")
    ox, oy = {832: (96, 58), 640: (0, 0), 648: (2, 64)}.get(a.width, (96, 58))
    box = (ox + 2 * 112, oy, ox + 2 * 320, oy + 2 * 6)
    h.goto_st(*GETMEN_XY)
    time.sleep(2.0)
    b = Image.open(h.shot()).convert("RGB")
    n = sum(1 for p in ImageChops.difference(a.crop(box), b.crop(box)).convert("L").getdata() if p > 40)
    nb = sum(1 for p in b.crop(box).convert("L").getdata() if p > 40)
    print(f"RESULT tooltip: image {a.width}x{a.height} box {box}; changed pixels {n}, bright pixels with the pointer on Get Men {nb}", flush=True)
    b.crop((ox, oy, ox + 640, oy + 40)).save(h.R / "tooltip.png")
    import shutil
    shutil.copy(h.R / "tooltip.png", f"/tmp/pmreg_tooltip_{h.R.name}.png")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--disk")
    ap.add_argument("--hd")
    ap.add_argument("--acsi", action="store_true")
    ap.add_argument("--original", action="store_true", help="unpatched floppy: no marker/tick checks")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--mhz", type=int, nargs="*", default=[], help="CPU clocks to measure at (default: the machine's own)")
    ap.add_argument("--vbls", type=int, default=1000)
    ap.add_argument("--saveload", action="store_true")
    ap.add_argument("--shots")
    ap.add_argument("--hopts", default="", help="extra Hatari options as one string (Falcon: '--borders false' gives the 640x436 screenshot the harness gates expect)")
    ap.add_argument("--bp", help="experiment: debugger breakpoint expression armed right after the start, e.g. 'pc = $508' (the game's stage-0 stub)")
    ap.add_argument("--bp-lines", default="r cacr=$0", help="debugger commands (';'-separated) run at the --bp breakpoint")
    a = ap.parse_args()
    name = f"{'HD' + ('-acsi' if a.acsi else '-gemdos') if a.hd else 'floppy'}{' ORIGINAL' if a.original else ''} {a.machine} TOS {a.tos} {a.mem} KB"
    print(f"CELL {name}", flush=True)
    h = None
    ok = True
    try:
        h = pmpatch.make_pm(Path(a.disk).resolve() if a.disk else None, Path(a.hd).resolve() if a.hd else None, acsi=a.acsi,
                            machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=__import__('shlex').split(a.hopts))
        if a.bp:
            f = h.R / "bp.txt"
            f.write_text(a.bp_lines.replace(";", "\n") + "\n")
            h.cmd(f"hatari-debug b {a.bp} :trace :once :file {f}")
            print(f"EXPERIMENT: at the first hit of `{a.bp}` run: {a.bp_lines}", flush=True)
        t0 = time.time()
        h.boot_to_game()
        marker = h.peekl(pmpatch.MARKER).to_bytes(4, "big")
        flags = h.peekl(pmpatch.FLAGS)
        sync = rdb(h, 0xFF820A)
        print(f"RESULT boot: {time.time() - t0:.0f} s, in_game {h.in_game()}, MARKER {marker!r} FLAGS {flags:#x}, protection flag removed {h.protection_removed()} "
              f"(boot_to_game raises if the question box shows), sync ${sync:02x}", flush=True)
        patched = not a.original
        if patched:
            ok &= marker == b"PMPO"
            tooltip(h)
            sample_sound(h, flags)
        clocks = a.mhz or [0]
        res = []
        for mhz in clocks:
            if mhz:
                h.set_cpuclock(mhz)
                time.sleep(2)
            res.append(measure(h, f"map view{f' {mhz} MHz' if mhz else ''}", a.vbls, patched))
        n = h.scenario_get_men()
        print(f"RESULT get_men: {n} people moving", flush=True)
        for mhz in clocks:
            if mhz:
                h.set_cpuclock(mhz)
                time.sleep(2)
            res.append(measure(h, f"get_men{f' {mhz} MHz' if mhz else ''}", a.vbls, patched))
        if patched:
            sample_sound(h, flags)
        print(f"RESULT after: in_game {h.in_game()} MARKER {h.peekl(pmpatch.MARKER).to_bytes(4, 'big')!r}", flush=True)
        if a.saveload:
            ok &= pmpatch.run_saveload(h, a.acsi)
        if a.shots:
            Path(a.shots).mkdir(parents=True, exist_ok=True)
            h.shot(str(Path(a.shots) / f"{a.machine}_{a.tos}_{a.mem}_{'hd' if a.hd else 'fl'}.png"))
        print(f"CELL DONE {name}: {'OK' if ok else 'CHECK'}", flush=True)
        return 0 if ok else 2
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        print(f"CELL FAILED {name}: {e!r}", flush=True)
        if h is not None:
            try:
                print(f"  MARKER={h.peekl(pmpatch.MARKER).to_bytes(4, 'big')!r} FLAGS={h.peekl(pmpatch.FLAGS):#x}", flush=True)
                d = Path(a.shots or "/tmp"); d.mkdir(parents=True, exist_ok=True)
                h.shot(str(d / f"fail_{a.machine}_{a.tos}_{a.mem}.png"))
            except Exception:  # noqa: BLE001
                pass
        return 1
    finally:
        if h is not None:
            h.close()


if __name__ == "__main__":
    sys.exit(main())
