#!/usr/bin/env python3
"""One line per cell from out/<cell>.txt: boot result, FLAGS, worst bank/code difference over all checkpoints, resets, Gamex copy extent, ring, DMA rate, fx anomalies.

    python3 work/audiocheck/summ.py [CELL ...]      (default: every out/*.txt that is not a t_* test)
"""
import re
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"


def summ(p: Path) -> str:
    t = p.read_text(errors="replace")
    name = p.stem
    boot = re.search(r"BOOT in_game=(\w+) MARKER=(\S+) FLAGS=(\w+)", t)
    cps = re.findall(r"\[(\w+)\s*\] bank (\d+) differ, bank-file tail\(panel\) (\d+), patch code (\d+)", t)
    worst_bank = max((int(c[1]) for c in cps), default=None)
    worst_tail = max((int(c[2]) for c in cps), default=None)
    reset = "RESET/CRASH" in t
    modes = set(re.findall(r"SV mode/in3d/dma/silent=(\w\w)", t))
    rates = set(re.findall(r"rate=(\w\w)", t))
    gx = re.search(r"Gamex TOS copy \[(\$\w+), (\$\w+)\).*overlap with bank (\d+) B, with payload (\d+) B", t)
    ring = re.search(r"RING .*?lead before top-up min (\d+) p5 (\d+) median (\d+) max (\d+).*?underrun resyncs (\d+)", t)
    fps = re.search(r"fps ([\d.]+) over", t)
    s = f"{name:12s} boot={'OK' if boot and boot.group(1) == 'True' else 'FAIL'} FLAGS={boot.group(3)[-2:] if boot else '?'} "
    s += f"cp={len(cps)} bank_diff_max={worst_bank} panel_diff_max={worst_tail} {'RESET! ' if reset else ''}"
    s += f"svmode={sorted(modes)} dmarate={sorted(rates)} "
    if gx:
        s += f"gamex[{gx.group(1)},{gx.group(2)}) ov_bank={gx.group(3)} ov_payload={gx.group(4)} "
    if ring:
        s += f"ring min/p5/med/max={'/'.join(ring.group(i) for i in range(1, 5))} underruns={ring.group(5)} "
    if fps:
        s += f"fps={fps.group(1)} "
    s += "SAVELOAD-FAIL " if "SAVE/LOAD FAILED" in t else ""
    s += "CELLFAIL " if "CELL FAILED" in t else ""
    return s


def main():
    names = sys.argv[1:]
    files = [OUT / f"{n}.txt" for n in names] if names else sorted(f for f in OUT.glob("*.txt") if not f.stem.startswith("t_"))
    for f in files:
        print(summ(f))


if __name__ == "__main__":
    main()
