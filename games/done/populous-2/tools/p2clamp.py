#!/usr/bin/env python3
"""Proof for pop2_clamp (work/notes/display.md section 5): a lost IKBD byte makes the game's pointer position garbage and the pointer
draw crash; with the clamp the packet is dropped and the game plays on.

    python3 tools/p2clamp.py [--snapshot busy1] [--vbls 400] [--blits 1]

Both runs restore the snapshot and apply, at the first flip after an absolute VBL, the live set `test_hog` (+ `pop2_clamp` in run B):
test_hog starts HOGN 32,000-byte blitter copies in HOG mode at the top of every pass (about 128,000 cycles = 12 IKBD byte times of bus
hold per blit), so the keyboard ACIA overruns (it holds one byte) and the 6-byte `$f7 btn xh xl yh yl` mouse reply loses a byte.
Run A (no clamp) watches the packet-complete copy `$1cd0` (`move.w $2026.l,$393fa.l`): a hit with `$2026` > 319 or `$2028` > 199
is a garbage position, and the run is searched for Hatari's "Bus Error" line.  Run B (clamp) reads pop2_clamp's DROPS counter and
checks that the world turn is still advancing at the end.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE)]
from p2abtest import APPLYPC, NUM, Populous2, WORK, apply_cmds, make_live, snap_path  # noqa: E402

HOGN = 0x86F20
DROPS = 0x86F10


def run(label: str, snap: Path, names: list[str], vbls: int, blits: int) -> dict:
    live = make_live(names)
    h = Populous2(snapshot=snap)
    out = {"label": label}
    try:
        R = h.R
        time.sleep(1.0)
        at = (h.vbl() // 100 + 3) * 100
        cmds = apply_cmds(live) + [f"w ${HOGN:x} $00 ${blits:02x}"]
        (R / "bad.txt").write_text("e ($2026).w\ne ($2028).w\ne ($393fa).w\ne ($393fc).w\ne ($3979c).w\ne VBL\n")
        cmds.append(f"b pc = $1cd0 && ($2026).w > 319 :trace :file {R / 'bad.txt'}")
        cmds.append(f"b pc = $1cd0 && ($2028).w > 199 :trace :file {R / 'bad.txt'}")
        (R / "end.txt").write_text(f"b all\nsavebin {R}/end.flag $0 2\ne ($3979c).w\ne VBL\ne (${DROPS:x}).l\n")
        cmds.append(f"b VBL > {at + vbls} :trace :once :file {R / 'end.txt'}")
        (R / "apply.txt").write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${APPLYPC:x} :trace :once :file {R / 'apply.txt'}")
        time.sleep(0.3)
        h.cmd("hatari-option --fast-forward on")
        t = time.time()
        while not (R / "end.flag").exists() and time.time() - t < 600:
            if "Bus Error" in h._logtext()[start:]:
                time.sleep(2)
                break
            time.sleep(0.5)
        time.sleep(1.0)
        text = h._logtext()[start:]
    finally:
        h.close()
    blocks = text.split("CPU breakpoint condition(s) matched")[1:]
    bad = []
    for b in blocks:
        if "bad.txt" in b:
            m = [int(v) for v in NUM.findall(b)]
            if len(m) >= 6:
                bad.append(dict(pkt_x=m[0], pkt_y=m[1], x=m[2], y=m[3], turn=m[4], vbl=m[5]))
    out["garbage_packets"] = bad
    out["bus_error"] = [ln for ln in text.splitlines() if "bus error" in ln.lower()][:3]
    out["ended"] = "end.flag" in text and "Wrote 0x2 bytes" in text
    tail = text[text.rfind("Wrote 0x2 bytes"):] if out["ended"] else ""
    out["end_numbers"] = [int(v) for v in NUM.findall(tail)]
    out["log_tail"] = "\n".join(text.splitlines()[-6:])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", default="busy1")
    ap.add_argument("--vbls", type=int, default=400)
    ap.add_argument("--blits", type=int, default=1)
    a = ap.parse_args()
    WORK.mkdir(exist_ok=True)
    sp = snap_path(a.snapshot)
    for label, names in (("A: test_hog, NO clamp", ["test_hog"]), ("B: test_hog + pop2_clamp", ["test_hog", "pop2_clamp"])):
        r = run(label, sp, names, a.vbls, a.blits)
        print(f"== {label}")
        print(f"   garbage packets seen at $1cd0 (packet x/y words out of range): {len(r['garbage_packets'])}; first: {r['garbage_packets'][:3]}")
        print(f"   Bus Error lines: {r['bus_error']}")
        print(f"   run reached its end: {r['ended']}; end numbers (turn.w, VBL, DROPS): {r['end_numbers']}")
        if not r["ended"]:
            print("   log tail:\n" + r["log_tail"])


if __name__ == "__main__":
    main()
