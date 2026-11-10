#!/usr/bin/env python3
"""Gate tool for patches/hn_credit.s (the version line on the Hunter title screen).

    python3 tools/huntcredit.py capture hd     build/game   orig        # a build whose START.TOS/FILES/P are unpatched, or the game dir
    python3 tools/huntcredit.py capture hd     build/game   patched
    python3 tools/huntcredit.py capture floppy build/floppy/HUNTER_disk1.st patched
    python3 tools/huntcredit.py capture floppy "alt/floppy/Hunter (1991)(Activision)[cr Paper Bag].st" orig
    python3 tools/huntcredit.py capture hd     build/game   patched st   # plain ST, TOS 1.04 (fixed waits); files credit_<kind>_<tag>_st.*
    python3 tools/huntcredit.py compare hd orig patched                  # pixel diff of the title bitmap, confined to the text rect?

`capture` cold-boots STE/TOS 1.62/1 MB in Hatari to the title and writes, under work/shots/ (git-ignored):
  credit_<kind>_<tag>.bmp.bin   the 32000-byte title bitmap at $23000 right after the game decoded it (breakpoint at $d622, the return of
                                the IFF decode; identical moment in the original and the patched run, so the diff is exactly our text)
  credit_<kind>_<tag>.png       screenshot of the settled title (icons animating)
  credit_<kind>_<tag>.pal.bin   palette registers $ff8240..
"""
from __future__ import annotations

import struct
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(GAME.parent.parent / "tools"))
sys.path.insert(0, str(HERE))
SHOTS = GAME / "work" / "shots"
RECT = dict(x0=100, x1=218, y0=194, y1=199)         # the text for "v1.0 enhanced by dad_prg" (len 24: x = (321 - 120) / 2 = 100 .. 100 + 119)


def decode(buf: bytes):
    """32000-byte ST low-res bitmap -> 200 rows of 320 colour indices."""
    rows = []
    for y in range(200):
        row = []
        for xb in range(20):
            p = struct.unpack(">4H", buf[y * 160 + xb * 8:y * 160 + xb * 8 + 8])
            for b in range(16):
                row.append(sum(((p[k] >> (15 - b)) & 1) << k for k in range(4)))
        rows.append(row)
    return rows


def capture(kind: str, target: str, tag: str, machine: str = "ste", tos: str = "1.62", mem: int = 1024):
    from stharness import TOS
    import hunter
    SHOTS.mkdir(parents=True, exist_ok=True)
    stem = f"credit_{kind}_{tag}" + ("" if machine == "ste" else f"_{machine}")
    raw = f"/tmp/{stem}.bin"
    Path(raw).unlink(missing_ok=True)
    t = Path(target)
    if not t.is_absolute():
        t = GAME / t
    orig_build = hunter.build_hd
    if kind == "hd":
        hunter.build_hd = lambda img, **k: orig_build(img, game=t, **k)
        h = hunter.Hunter(machine=machine, tos=TOS[tos], memsize_kb=mem)
    else:
        import huntfloppy
        h = huntfloppy.HunterFloppy(t, machine=machine, tos=TOS[tos], memsize_kb=mem, drives=1)
    try:
        cf = h.R / "cap.txt"
        cf.write_text(f"savebin {raw} $23000 32000\n")
        h.debug("b all", 0.3)
        h.cmd(f"hatari-debug b pc = $d622 && ($1e4e).l = $23000 :trace :once :file {cf}")
        blind = machine == "st"                              # the reference crops are STE pictures: fixed waits on a plain ST
        if kind == "hd":
            if blind:
                time.sleep(14)
            else:
                h._stage("hw", False, 12, 90)
            h.keypress(57)
            if blind:
                time.sleep(10)
            else:
                h._stage("title1", False, 6)
            h.keypress(57)
        else:
            time.sleep(12)
            h.keypress(57)
        if blind:
            time.sleep(50)
        else:
            h._stage("title2", False, 22, 240)
        time.sleep(3)
        pal = h.debug("m $ff8240 32")
        (SHOTS / f"{stem}.pal.bin").write_text(pal)
        h.shot(str(SHOTS / f"{stem}.png"))
        if not Path(raw).exists():
            raise SystemExit("the $d622 breakpoint did not fire (no bitmap saved)")
        (SHOTS / f"{stem}.bmp.bin").write_bytes(Path(raw).read_bytes())
        print(f"captured {stem}: {len(Path(raw).read_bytes())} bytes")
    finally:
        hunter.build_hd = orig_build
        h.close()


def compare(kind: str, a: str, b: str) -> int:
    ba = (SHOTS / f"credit_{kind}_{a}.bmp.bin").read_bytes()
    bb = (SHOTS / f"credit_{kind}_{b}.bmp.bin").read_bytes()
    ra, rb = decode(ba), decode(bb)
    diffs = [(x, y, ra[y][x], rb[y][x]) for y in range(200) for x in range(320) if ra[y][x] != rb[y][x]]
    print(f"{kind}: {len(diffs)} pixels differ ({a} -> {b})")
    if diffs:
        xs, ys = [d[0] for d in diffs], [d[1] for d in diffs]
        print(f"  bounding box x {min(xs)}..{max(xs)}  y {min(ys)}..{max(ys)}   text rect x {RECT['x0']}..{RECT['x1']} y {RECT['y0']}..{RECT['y1']}")
        print(f"  original colours under the text: {sorted({d[2] for d in diffs})}; new colours: {sorted({d[3] for d in diffs})}")
        inside = all(RECT["x0"] <= x <= RECT["x1"] and RECT["y0"] <= y <= RECT["y1"] for x, y, _o, _n in diffs)
        print(f"  all differences inside the text rect: {inside}")
        for y in range(RECT["y0"] - 1, min(RECT["y1"] + 2, 200)):
            print("  " + "".join("#" if rb[y][x] == 10 and ra[y][x] != 10 else ("+" if ra[y][x] else ".") for x in range(RECT["x0"] - 4, RECT["x1"] + 5)))
        return 0 if inside and sorted({d[2] for d in diffs}) == [0] and sorted({d[3] for d in diffs}) == [10] else 1
    return 1


def main():
    a = sys.argv[1:]
    if a and a[0] == "capture":
        mc = a[4] if len(a) > 4 else "ste"
        capture(a[1], a[2], a[3], mc, "1.04" if mc == "st" else "1.62")
    elif a and a[0] == "compare":
        sys.exit(compare(a[1], a[2], a[3]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
