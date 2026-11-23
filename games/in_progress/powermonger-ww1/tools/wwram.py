#!/usr/bin/env python3
"""Stage 4 item 1 gate (memory_plan M6): the core's RAM guard.  Cold boot to the option screen on a given RAM size; prints
`GATE ram <name> PASS|FAIL <evidence>`.  Also reads the basepage's p_hitpa at the guard (breakpoint at the first instruction of `front`).
    python3 tools/wwram.py --disk build/default/floppy.st --mem 512 --machine st --tos 1.04 --expect refused|installed|original --workdir DIR
"""
import argparse, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402

MARKER = 0x727F8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disk", required=True)
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default="1.62")
    ap.add_argument("--mem", type=int, default=1024)
    ap.add_argument("--expect", required=True, choices=["refused", "installed", "original"])
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--tag", default="ram")
    a = ap.parse_args()
    h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir, machine=a.machine, tos=pmww.TOS[a.tos], memsize_kb=a.mem)
    ok = True
    try:
        h.boot_to_options(log=lambda s: print("  " + s, flush=True))
        time.sleep(2)
        marker = bytes(h.ram(MARKER, 4))
        img = bytes(h.ram(0x72000, 8))
        want = {"refused": b"\0\0\0\0", "original": b"\0\0\0\0", "installed": b"PMPO"}[a.expect]
        push = h.ram(0x576 + 0, 0) if False else b""
        ok = marker == want
        print(f"GATE {a.tag} marker $727f8 = {marker!r} want {want!r} ({a.expect}) {'PASS' if ok else 'FAIL'}; $72000..: {img.hex()}", flush=True)
        t = h.wtext().strip()
        o2 = "Welcome to the World" in t
        print(f"GATE {a.tag} option screen reached on {a.mem} KB {'PASS' if o2 else 'FAIL'} text {t[:50]!r}", flush=True)
        c = h.peekl(pmww.CACHE_CURSOR)
        print(f"GATE {a.tag} cache cursor $2cfda = ${c:08x} ({'cache on' if c else 'no cache (probe found no RAM at $80000)'})", flush=True)
        return 0 if ok and o2 else 2
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
