#!/usr/bin/env python3
"""Where does a cold boot get stuck?  Boots a floppy (or HD folder) and prints, every --step seconds, the VBL counter, pc, the stage 1/2 hand-over words,
the patch marker, the main-loop iteration and the floppy/FDC state; presses SPACE every 4 s like the harness (until the game proper runs) and saves a screenshot per step.

    python3 tools/pmdiag.py --disk build/reg/floppy/powermonger.st --machine tt --tos 3.06 --mem 4096 --out /tmp/diag_tt
    python3 tools/pmdiag.py --disk disks/protected.st --machine tt ...        # the unpatched original
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent.parent.parent / "tools"), str(HERE)]
import pmpatch  # noqa: E402
from pm import TOS  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disk")
    ap.add_argument("--hd")
    ap.add_argument("--acsi", action="store_true")
    ap.add_argument("--machine", default="tt")
    ap.add_argument("--tos", default="3.06")
    ap.add_argument("--mem", type=int, default=4096)
    ap.add_argument("--step", type=int, default=20)
    ap.add_argument("--steps", type=int, default=12)
    ap.add_argument("--out", default="/tmp/pmdiag")
    ap.add_argument("--opts", default="", help="extra Hatari options as ONE string, e.g. '--trace cpu_exception --trace-file /tmp/x.log'")
    ap.add_argument("--at", help="breakpoint expression (e.g. 'pc = $672'): at its first hit dump registers, memory $640..$6a0 and the stack to the log")
    ap.add_argument("--atlines", default="r;m $640 96;m $a7 48", help="debugger commands (';'-separated) run at the --at breakpoint")
    ap.add_argument("--regs", action="store_true", help="also print sr, the stack pointers, $466 and the VBL vector")
    ap.add_argument("--scale", type=int, default=0, help="experiment: multiply the six FDC time-out constants (`move.l #$40000/$60000,d0` before `btst #5,$fa01.w`; "
                    "stage 1 $57644 $576ea $5793c, stage 2 $db86 $dc2c $de7e) by this at each stage's hand-over (Hunter's ttfalcon.md lesson)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    h = pmpatch.make_pm(Path(a.disk).resolve() if a.disk else None, Path(a.hd).resolve() if a.hd else None, acsi=a.acsi,
                        machine=a.machine, tos=TOS[a.tos], memsize_kb=a.mem, extra=__import__('shlex').split(a.opts))
    try:
        if a.at:
            f = h.R / "at.txt"
            f.write_text(a.atlines.replace(";", "\n") + "\n")
            h.cmd(f"hatari-debug b {a.at} :trace :once :file {f}")
        if a.scale:
            for stage, base, first, addrs in ((1, 0x576, 0x4EB9, (0x57644, 0x576EA, 0x5793C)), (2, 0x10A6, 0x41F9, (0xDB86, 0xDC2C, 0xDE7E))):
                lines = []
                for ad, v in zip(addrs, (0x40000, 0x40000, 0x60000)):
                    b = (v * a.scale).to_bytes(4, "big")
                    lines.append(f"w ${ad:x} " + " ".join(f"${x:02x}" for x in b))
                f = h.R / f"scale{stage}.txt"
                f.write_text("\n".join(lines) + "\n")
                h.cmd(f"hatari-debug b pc = ${base:x} && (${base:x}).w = ${first:x} :trace :once :file {f}")
        for i in range(a.steps):
            t0 = time.time()
            try:
                while time.time() - t0 < a.step:
                    h.key("space")
                    time.sleep(4)
                txt = h.debug("e pc", 0.6) + h.debug("e VBL", 0.6)
                pc = re.findall(r"\$([0-9a-fA-F]+) \(hex\)", txt)
                a10a6 = h.peekw(0x10A6)
                mk = h.peekl(pmpatch.MARKER).to_bytes(4, "big")
                it = h.peekl(0x2DF70)
                print(f"[{(i + 1) * a.step:4d}s] e pc/VBL {pc}, $10a6={a10a6:04x}, MARKER {mk!r}, FLAGS {h.peekl(pmpatch.FLAGS):#x}, iter {it}", flush=True)
                if a.regs:
                    regs = re.findall(r"\$([0-9a-fA-F]+) \(hex\)", h.debug("e sr", 0.6) + h.debug("e a7", 0.6) + h.debug("e usp", 0.6) + h.debug("e ssp", 0.6)
                                      + h.debug("e (0x466).l", 0.6) + h.debug("e (0x70).l", 0.6) + h.debug("e (0x4ce).l", 0.6) + h.debug("e vbr", 0.6))
                    print(f"        sr a7 usp ssp $466 $70(vbl vector) $4ce(vblqueue) vbr = {regs}", flush=True)
                    sp = int(regs[1], 16)
                    print("        stack:", h.debug(f"m ${sp:x} 64", 0.8).strip().replace("\n", " | ")[:500], flush=True)
                shutil.copy(h.shot(), out / f"s{i:02d}.png")
            except Exception as e:  # noqa: BLE001
                print(f"[{(i + 1) * a.step:4d}s] debugger/screenshot failed: {e!r}", flush=True)
                try:
                    log = h._logtext()
                    print("--- log tail ---\n" + log[-1500:], flush=True)
                    import subprocess
                    subprocess.run(["import", "-display", h.env["DISPLAY"], "-window", "root", str(out / "root.png")], timeout=20, check=False)
                    print(f"root window screenshot (dialogs are only visible here): {out / 'root.png'}", flush=True)
                except Exception:  # noqa: BLE001
                    pass
                break
        if a.at:
            txt = h._logtext()
            i = txt.find("Reading debugger commands from")
            print("--- breakpoint dump ---\n" + (txt[i:i + 3500] if i >= 0 else "(never hit)"), flush=True)
    finally:
        h.close()


if __name__ == "__main__":
    main()
