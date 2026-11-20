"""Scratch helpers for the timing study (private copy; does not touch tools/msr*.py)."""
import re, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
sys.path.insert(0, str(GAME / "tools")); sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
from msr import Moonshine
SNAP = GAME / "work/snapshots"
CYC = 160256

def open_snap(name, mhz=8, settle=3):
    h = Moonshine(snapshot=str(SNAP / name))
    time.sleep(settle)
    if mhz: h.set_cpuclock(mhz)
    return h

def chain(h, pcs, extra, total_wait, tag="ch"):
    """Chain of `b pc = X :once :file` breakpoints cycling through `pcs`; each stage logs `e VBL`, `e FrameCycles`
    and the debugger commands in `extra` (list of str). Returns raw log text."""
    for i, pc in enumerate(pcs):
        nxt = pcs[(i + 1) % len(pcs)]
        lines = ["e VBL", "e FrameCycles"] + extra + [f"b pc = ${nxt:x} :trace :once :file {h.R}/{tag}_{nxt:x}.txt"]
        (h.R / f"{tag}_{pc:x}.txt").write_text("\n".join(lines) + "\n")
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${pcs[0]:x} :trace :once :file {h.R}/{tag}_{pcs[0]:x}.txt")
    time.sleep(total_wait)
    h.debug("b all", 0.5)
    return h._logtext()[n0:]

def parse_chain(log, nextra):
    """-> list of (pc, [values...]) ; values = ints of `e` results (hex/dec lines '#N (dec)') in order"""
    out = []; cur = None; vals = []
    for ln in log.splitlines():
        m = re.match(r"\tpc = \$([0-9a-f]+) :once :trace", ln)
        if m:
            if cur is not None: out.append((cur, vals))
            cur = int(m.group(1), 16); vals = []; continue
        if cur is None: continue
        m = re.search(r"#(\d+) \(dec\)", ln)
        if m: vals.append(("e", int(m.group(1)))); continue
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m: vals.append(("m", int(m.group(1), 16), bytes.fromhex(m.group(2).replace(" ", "")[:64])))
    if cur is not None: out.append((cur, vals))
    return out
