#!/usr/bin/env python3
"""Floppy save/load round trip with triple buffering on (HunterTB2; notes work/notes/triple.md section 6.4).

    python3 tools/hunttb_save.py [--disk1 build/tb2_fl/HUNTER_disk1.st] [--machine ste] [--tos 1.62] [--mem 1024] [--slot 2]

Cold boots the floppy build (tb_* in it), checks tb mode 1 and that page C is in use, walks, SAVES to the slot through the game's disk
menus (ESC -> Disk Operation -> Save, name, Return; tools/huntsave.py Menus), then makes Hatari write the disk image back
(insert another image in drive A and the scratch image again: Hatari writes a modified .st image on eject only), reports
which files of the disk changed, walks away, LOADS the slot and compares the player position and the saved RAM ranges
(huntsave.cmp_ranges), then walks again and re-checks the page rotation.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path[:0] = [str(GAME.parent.parent.parent / "tools"), str(HERE)]
from stharness import TOS  # noqa: E402
import huntsave as hs  # noqa: E402

NAMES = {0x23000: "A", 0x2AD00: "B", 0x81000: "C"}


def files(img: Path) -> dict[str, bytes]:
    out = {}
    names = subprocess.run(["mdir", "-b", "-i", str(img), "::"], capture_output=True, text=True).stdout.split()
    for n in names:
        n = n.split("/")[-1]
        r = subprocess.run(["mcopy", "-i", str(img), f"::{n}", "-"], capture_output=True)
        out[n] = r.stdout
    return out


def pages(h, n=60):
    c = Counter()
    for _ in range(n):
        b = h.peek(0x94A, 8)
        c[(NAMES.get(int.from_bytes(b[:4], "big"), "?"), NAMES.get(int.from_bytes(b[4:], "big"), "?"))] += 1
        time.sleep(0.05)
    return dict(c)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--disk1", default="build/tb2_fl/HUNTER_disk1.st")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--slot", type=int, default=2)
    ap.add_argument("--work", default="/tmp/tb2_sv")
    a = ap.parse_args()
    d = Path(a.work)
    d.mkdir(parents=True, exist_ok=True)
    src = GAME / a.disk1
    orig = files(src)
    print(f"original disk md5 {hashlib.md5(src.read_bytes()).hexdigest()}")
    h = hs.FloppyRig(src, machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem)
    ok = True
    try:
        h.boot()
        print("marker", h.peek(0x8BFF8, 4), "in game", h.in_game(), "| tb state", h.peek(0x8C1B2, 6).hex(), "(mode word = last 2 bytes: 0001 = on)")
        h.walk(2, "Up")
        print("pages before the save:", pages(h))
        p0 = h.save(a.slot, "tbsv", d / "A.bin")
        print("saved at", p0, "| tb state", h.peek(0x8C1B2, 6).hex(), "| pages after the save:", pages(h))
        dummy = h.R / "dummy.st"
        shutil.copy(h.d1, dummy)
        h.swap_a(dummy)                                     # eject: Hatari writes the modified image back
        time.sleep(4)
        mid = hashlib.md5(h.d1.read_bytes()).hexdigest()
        h.swap_a(h.d1)
        time.sleep(4)
        now = files(h.d1)
        ch = [n for n in sorted(set(orig) | set(now)) if orig.get(n) != now.get(n)]
        print(f"disk md5 after the eject {mid}  (changed: {mid != hashlib.md5(src.read_bytes()).hexdigest()}); files whose content changed: {ch}")
        ok &= bool(ch)
        keep = d / "after_save.st"
        shutil.copy(h.d1, keep)
        h.walk(3, "Up", "Left")
        p1 = hs.state(h)
        got = h.load(a.slot, d / "B.bin")
        print("player at the save", hs.pos_of((d / "A.bin").read_bytes()), "| moved to", p1, "| after the load", got)
        ok &= p1 != p0 and got == hs.pos_of((d / "A.bin").read_bytes())
        A, B = (d / "A.bin").read_bytes(), (d / "B.bin").read_bytes()
        ok &= hs.cmp_ranges(A, B, "RAM save-time vs RAM after-load")
        h.walk(3, "Up")
        print("after the load: in_game", h.in_game(), "| tb state", h.peek(0x8C1B2, 6).hex(), "| pages:", pages(h), "| pos", hs.state(h))
    finally:
        h.close()
    print("TBSAVE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
