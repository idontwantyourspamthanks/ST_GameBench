#!/usr/bin/env python3
"""Save and Load with the Amiga panel (HD build, 2 MB or more): tools/huntsave.py roundtrip plus the panel state before the save and
after the load (V_PAN, the master's first bytes, the shifter palette at the panel, a screenshot of each).

    python3 tools/pnl_save.py --game build/pnl_hd3 --machine ste --mem 2048
"""
from __future__ import annotations
import argparse, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import huntsave as hs      # noqa: E402
import huntvis as hv       # noqa: E402
import pnl_cold            # noqa: E402
from PIL import Image     # noqa: E402


def panel_state(h, tag):
    v = hv.var(h)
    m = h.peek(0x3682C, 8).hex()
    print(f"PANEL {tag}: V_PAN={h.peek(hv.VAR + 15, 1).hex()} cfg={v['cfg']:#04x} H={v['H']} pneed={v['pneed']} master[0:8]={m} state={hs.state(h)}", flush=True)
    Image.open(h.shot(str(h.R / "ps.png"))).convert("RGB").crop((96, 58, 736, 458)).save(f"/tmp/pn/save_{tag}.png")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="build/pnl_hd3")
    ap.add_argument("--machine", default="ste")
    ap.add_argument("--tos", default=None)
    ap.add_argument("--mem", type=int, default=2048)
    ap.add_argument("--slot", type=int, default=2)
    ap.add_argument("--work", default="/tmp/hsv_pnl")
    a = ap.parse_args()
    d = Path(a.work); d.mkdir(parents=True, exist_ok=True)
    h = hs.rig(a)
    h.STAGES = dict(h.STAGES)
    pnl_cold.harden(h)               # looser stage crops (palette), the HUD crop by the 3D-loop marker
    h.boot_to_game()
    try:
        m0 = panel_state(h, "before_save")
        h.walk(2.5, "Up")
        h.save(a.slot, "rt", d / "A.bin")
        m1 = panel_state(h, "after_save")
        h.walk(4, "Up", "Left")
        sb = h.load(a.slot, d / "B.bin")
        time.sleep(1.5)
        m2 = panel_state(h, "after_load")
        ok = m0 == m1 == m2 and m0 != "1fff1fffe000e000"
        print("loaded position", sb, "| ROUNDTRIP+PANEL", "PASS" if ok else "FAIL")
    finally:
        hs.settle_and_close(h) if h.proc.poll() is None else None


if __name__ == "__main__":
    main()
