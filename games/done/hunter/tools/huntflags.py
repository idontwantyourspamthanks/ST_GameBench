#!/usr/bin/env python3
"""FLAGS bit 3 (Falcon) and the DMA sound on STE / TT / Falcon cold boots (work/notes/jagpad.md section 8).

    python3 tools/huntflags.py CELL --kind hd|floppy --machine ste|tt|falcon [--game build/game | --disk1 build/floppy/HUNTER_disk1.st] [--secs 6]

Boots the build, prints MARKER, FLAGS, TOS's cookie jar pointer ($5a0) and the jar as it is after the boot, the payload's sound state (SV: mode, v_fal), the
DMA registers, injects an explosion (as snd_test.py coldboot does), records 6 s of the DMA stream (Hatari WAV capture) and counts CPU exceptions 2 (bus error)
and 3 (address error) in Hatari's `--trace cpu_exception` log.  TT: --mmu true, 4 MB, ACSI + HDDRIVER; Falcon: 4 MB, floppy.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
import snd_test  # noqa: E402  (sets up the per-process WAV capture HOME)
import hunter  # noqa: E402
from stharness import MACHINE_TOS  # noqa: E402

SV = snd_test.SV


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cell")
    ap.add_argument("--kind", default="hd", choices=["hd", "floppy"])
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--game", default="build/game")
    ap.add_argument("--disk1", default="build/floppy/HUNTER_disk1.st")
    ap.add_argument("--secs", type=float, default=6)
    a = ap.parse_args()
    snd_test.setup_home()
    os.environ["HOME"] = str(snd_test.HOME)
    os.environ["SDL_AUDIODRIVER"] = "dummy"
    extra = ["--sound", "50066", "--trace", "cpu_exception"] + (["--mmu", "true"] if a.machine == "tt" else [])
    mem = 1024 if a.machine == "ste" else 4096
    tos = MACHINE_TOS[a.machine]
    orig = hunter.build_hd
    h = None
    try:
        if a.kind == "hd":
            hunter.build_hd = lambda img, **k: orig(img, game=GAME / a.game, **k)
            h = hunter.Hunter(machine=a.machine, tos=tos, memsize_kb=mem, extra=extra)
        else:
            from huntfloppy import HunterFloppy
            h = HunterFloppy(GAME / a.disk1, None, drives=1, machine=a.machine, tos=tos, memsize_kb=mem, extra=["--joy1", "none"] + extra, fastfdc="no")
        stage = h._stage
        h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
        if a.kind == "floppy":
            ok = h.boot_floppy("none", blind=False, pb_key_at=35 if a.machine != "ste" else 12)
        elif a.machine == "ste":
            ok = h.boot_to_game()
        else:                                            # TT: the same stage-gated flow as hunt_ttf.boot_hd
            time.sleep(10)
            h.keypress(57)
            time.sleep(3)
            assert h.wait_stage("title2", 150, 2)
            time.sleep(1.5)
            h.key("space", 0.3)
            assert h.wait_stage("main", 40, 2)
            h.goto(*h.START_XY, home_xy=h.HOME_XY)
            h.click()
            assert h.wait_stage("games", 30, 2)
            h.goto(*h.ACTION_XY, home_xy=h.HOME_XY)
            h.click()
            assert h.wait_stage("name", 30, 2)
            for c in "bench":
                h.key(c, 0.15)
                time.sleep(0.3)
            h.click()
            assert h.wait_stage("mission", 30, 2)
            h.click()
            assert h.wait_stage("game", 60, 2)
            time.sleep(1.0)
            ok = h.in_game()
        time.sleep(1.0)
        fl = h.peek(0x8BFF0, 4)
        jp = int.from_bytes(h.peek(0x5A0, 4), "big")
        jar = h.peek(jp, 24) if 0 < jp < 0xF00000 else b""
        mch = None
        for i in range(0, len(jar) - 7, 8):
            if jar[i:i + 4] == b"_MCH":
                mch = jar[i + 4:i + 8].hex()
        sv = snd_test.pk(h, SV, 0x10)
        print(f"[{a.cell}] {a.kind} {a.machine} {mem}K in_game={ok} MARKER={h.peek(0x8BFF8, 4)!r} FLAGS={fl.hex()}  $5a0 -> ${jp:x} jar_MCH={mch}")
        print(f"[{a.cell}]   payload SV: mode={sv[0]} in3d={sv[1]} dma_on={sv[2]}   (mode 2 = DMA samples, 1 = original YM)")
        if snd_test.CAP.exists():
            snd_test.CAP.unlink()
        h.cmd("hatari-shortcut recsound")
        t0 = time.time()
        time.sleep(0.5)
        snd_test.inject(h, 3, 1, 12)
        time.sleep(0.5)
        regs = snd_test.pk(h, 0xFF8900, 0x24)
        print(f"[{a.cell}]   after the injected explosion: $ff8901={regs[1]:02x} (DMA control) $ff8921={regs[0x21]:02x} (mode: 80 = 6258 Hz, 81 = 12517 Hz)  "
              f"SV mode={snd_test.pk(h, SV, 8)[0]}")
        while time.time() - t0 < a.secs:
            time.sleep(0.1)
        h.cmd("hatari-shortcut recsound")
        time.sleep(1.0)
        import numpy as np
        out = GAME / "work" / "snd" / f"flags_{a.cell}.wav"
        out.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(snd_test.CAP, out)
        x, sr = snd_test.load_wav(out)
        print(f"[{a.cell}]   WAV {out.name}: {len(x) / sr:.1f} s, rms {x.std():.0f}, peak {np.abs(x).max():.0f}")
        txt = h._logtext()
        from collections import Counter
        be = Counter((m.group(1), m.group(2), m.group(3)) for m in re.finditer(r"Bus error (reading|writing) at address \$([0-9a-f]+) PC=\$([0-9a-f]+)", txt))
        print(f"[{a.cell}]   Hatari trace log: {len(txt.splitlines())} lines, {sum(be.values())} bus error(s): (access, address, PC) x count")
        for (rw, ad, pc), n in sorted(be.items(), key=lambda kv: int(kv[0][2], 16)):
            where = "TOS ROM" if int(pc, 16) >= 0xE00000 else ("payload $8ba00-$aefff" if 0x8BA00 <= int(pc, 16) < 0xAF000 else "game RAM")
            print(f"        {rw} ${ad} at PC=${pc} ({where}) x{n}")
        return 0
    finally:
        hunter.build_hd = orig
        if h:
            h.close()


if __name__ == "__main__":
    sys.exit(main())
