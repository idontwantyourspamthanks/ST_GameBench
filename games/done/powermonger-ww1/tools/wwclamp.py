#!/usr/bin/env python3
"""p4_clamp gate (master's pmbuserr / buserr.md): a corrupt IKBD packet position must not reach the pointer code.

    python3 tools/wwclamp.py --disk build/X/floppy.st --workdir DIR [--machine ste --tos 1.62 --mem 1024] [--tag NAME] [--control]

Cold boot to the map view.  1. (clamp builds) normal use: the hook's `.bad` path ($75c1e) is hit 0 times while the pointer is moved around for 20 s.
2. The debugger pokes a garbage position into the packet shadow ($1d2b2 = $0500 = 1280 > 319, $1d2b4 = $adfd) at the packet-complete branch $ed6 (the original's first
   instruction of the position copy; a lost IKBD byte makes exactly this) and reads $2edb2 / $2edb4 (the committed position the VBL pointer code uses) at $ef4 (the end of the copy):
   with the clamp they keep the last good position, without it (`--control`: the build has no p4_clamp) they become the garbage.  The game must keep running (counter ticking, no
   bus error in the log) for 6 s after the poke.
Output lines `GATE <tag> ...`.
"""
from __future__ import annotations
import argparse
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--disk", required=True)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--tag")
    ap.add_argument("--control", action="store_true", help="the build has NO p4_clamp: the garbage is EXPECTED to reach $2edb2 / $2edb4")
    a = ap.parse_args()
    tag = a.tag or Path(a.disk).parent.name
    ok = True

    def line(name, good, detail=""):
        nonlocal ok
        ok &= bool(good)
        print(f"GATE {tag}/{a.machine} {name} {'PASS' if good else 'FAIL'} {detail}", flush=True)

    h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir, machine=a.machine, tos=pmww.TOS[a.tos], memsize_kb=a.mem)
    try:
        h.boot_to_map(noprot=True, swap=False, log=lambda s: print("  " + s, flush=True))
        time.sleep(3)
        site = h.ram(0xED6, 10).hex()
        want = "4eb900075c004e714e71" if not a.control else "13f90001d2b10001d2af"
        line("site $ed6", site == want, f"{site} (want {want})")
        if not a.control:
            h.watch_pcs([0x75C1E])
            t = time.time()
            i = 0
            while time.time() - t < 20:
                h.goto_st(60 + 20 * (i % 10), 40 + 10 * (i % 7))
                i += 1
                time.sleep(0.5)
            hits = h.hits().get(0x75C1E, 0)
            line("normal use: the drop path is never taken", hits == 0, f"{hits} hit(s) of $75c1e in 20 s of pointer motion")
            h.debug("b all", 0.3)
        good = (h.peekw(0x2EDB2), h.peekw(0x2EDB4))
        (h.R / "poke.txt").write_text(f"w $1d2b2 $05 $00 $ad $fd\nb pc = $ef4 :trace :once :file {h.R / 'dump.txt'}\n")
        (h.R / "dump.txt").write_text("m $2edb2 4\nm $1d2b2 4\n")
        mark = len(h._logtext())
        h.cmd(f"hatari-debug b pc = $ed6 :trace :once :file {h.R / 'poke.txt'}")
        time.sleep(6)
        txt = h._logtext()[mark:]
        i = txt.find("> m $2edb2 4")
        print("  log after the poke: " + " | ".join(txt[txt.find("> w $1d2b2"):][:700].splitlines()), flush=True)
        m = re.search(r"\n0*2EDB2:\s+((?:[0-9A-Fa-f]{2} ){3}[0-9A-Fa-f]{2})", txt[i:], re.I) if i >= 0 else None
        words = None
        if m:
            b = bytes.fromhex(m.group(1).replace(" ", ""))
            words = (int.from_bytes(b[0:2], "big"), int.from_bytes(b[2:4], "big"))
        if a.control:
            line("control: the garbage position reaches $2edb2 / $2edb4 (the gate can fail)", words == (0x0500, 0xADFD), f"{words and tuple(hex(x) for x in words)}")
        else:
            line("clamp: the garbage position is dropped, $2edb2 / $2edb4 keep the last good position", words is not None and words[0] <= 319 and words[1] <= 199 and words != (0x0500, 0xADFD),
                 f"after the poke {words and tuple(hex(x) for x in words)}, before {tuple(hex(x) for x in good)}")
        err = re.findall(r"(?i)(bus error|address error|illegal instruction|double bus)[^\n]*", txt)
        tick = h.ticking(2.0)
        if a.control:
            line("control: the unclamped garbage hurts the game (bus error, or it stops)", bool(err) or not tick, f"errors {err[:2]}, ticking {tick}")
        else:
            line("the game runs on: no CPU exception, counter ticking", not err and tick, f"errors {err[:2]}, ticking {tick}")
        print(f"CELL DONE {tag}/{a.machine}: {'OK' if ok else 'FAIL'}", flush=True)
        return 0 if ok else 2
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
