#!/usr/bin/env python3
"""The Amiga panel across the game's screens (snapshot + live install as tools/pnl_gate.py): log book, item table, drone map,
game options, pause, radar, weapons; one screenshot per state -> /tmp/pn/scr_<name>.png and a line with the screen mode ($13e) and the split state."""
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pnl_gate as pg
from pnl_gate import *
from PIL import Image

snap = sys.argv[1] if len(sys.argv) > 1 else "1mb_foot_stand"
pg.ensure_bin()
h = Hunter(snapshot=str(SNAP / f"{snap}.sav"))
try:
    time.sleep(1)
    names, cfg, inst = pg.VARIANTS["amiga"]
    apply_live(h, mklive(names + ["key_item"], "pg_scr", samples=True), [f"w ${CFG:x} ${cfg:02x}", f"loadbin {pg.PAN_BIN} $3682c", f"w ${VAR + 15:x} $01", f"w ${VAR + 6:x} $ff $ff"])
    time.sleep(2)
    def shot(name, note=""):
        out = f"/tmp/pn/scr_{name}.png"
        Image.open(h.shot(str(h.R / "s.png"))).convert("RGB").crop((96, 58, 736, 458)).save(out)
        v = var(h)
        mode = int.from_bytes(h.peek(A5 + 0x13E, 2), "big")
        print(f"{name:12s} mode={mode} H={v['H']} pneed={v['pneed']} V_PAN={h.peek(VAR+15,1)[0]} flags93={h.peek(A5+0x93-0x806+0x806,1).hex()} {note}", flush=True)
    shot("start")
    h.rel(0, -250, steps=10); time.sleep(1.5)       # the mouse at the top edge opens the item table
    shot("itemtable")
    h.rel(0, 250, steps=10); time.sleep(1.5)
    shot("itemtable_closed")
    for k, nm in (("r", "radar"), ("c", "clock"), ("f", "flare"), ("question", "overlaymap"), ("l", "logbook"), ("a", "drone")):
        h.key(k, 0.3); time.sleep(2.5)
        shot(nm)
        if nm in ("overlaymap", "logbook", "drone"):
            h.key("Escape", 0.3); time.sleep(1.5)
            shot(nm + "_esc")
            if nm != "drone":
                h.key("Escape", 0.3); time.sleep(1.5)
    h.key("p", 0.3); time.sleep(1.5)
    shot("pause")
    h.key("p", 0.3); time.sleep(1.0)
finally:
    h.close()
