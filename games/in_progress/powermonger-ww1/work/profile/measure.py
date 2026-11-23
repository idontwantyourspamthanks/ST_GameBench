"""measure.py GAME SNAP MHZ  -> /tmp/pmww1prof/res/<game>_<snap>_<mhz>.{json,txt,bin}
Everything in EMULATED time: fps = flips of $ff8201 per emulated VBL (50 Hz), cycles = Hatari's CycleCounter / profile cycles."""
import os, sys, json, re, time, shutil
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
from pathlib import Path
game, snap, mhz = sys.argv[1], sys.argv[2], int(sys.argv[3])
FPSV = int(os.environ.get("FPSV", 400)); PROFV = int(os.environ.get("PROFV", 300))
OUT = Path("/tmp/pmww1prof/res"); OUT.mkdir(exist_ok=True)
W = Path("/tmp/pmww1prof/w%s%d" % (game[0], mhz)); shutil.rmtree(W, ignore_errors=True)
NUM = re.compile(r"#(\d+)(?:/-?\d+)? \(dec\)")
if game == "pm":
    PMT = "/home/ryan/Code/AtariST/gamebench/games/done/powermonger"
    sys.path[:0] = [PMT + "/tools", "/home/ryan/Code/AtariST/gamebench/tools"]
    from pm import PM, LOOP_SITES
    h = PM(snapshot=f"{PMT}/work/snapshots/{snap}.sav", workdir=str(W), memsize_kb=1024)
    SITES = (0x13020,) + tuple(LOOP_SITES); VBLH = 0x1282
else:
    sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger-ww1/work/profile")
    from common import *
    h = open_snap(snap, W.name)
    SITES = (0x13da8,0x13db4,0x13dba,0x13dc0,0x13dc6,0x13e04,0x13e0a,0x13e18,0x13e1e,0x13e24,0x13e2a,0x13e30,0x13e36,0x13e3c,0x13e42,0x13e6a,0x13e70,0x145e2,0x145e8)
    VBLH = 0x774
base = OUT / f"{game}_{snap}_{mhz}"
try:
    time.sleep(1.0)
    if mhz != 8: h.set_cpuclock(mhz)
    h.debug("b all", 0.3)
    v = h.vbl(); s0 = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {v+60} :trace :once"); h._wait_removed(s0); h.debug("b all", 0.3)   # warm-up 60 VBL
    f = h.fps(FPSV)                      # flips over FPSV emulated VBL
    print("FPS", game, snap, mhz, f, flush=True)
    # phase 1: profile (no site breakpoints: every debugger stop resets the profiler in this Hatari build)
    endf = h.R / "prof_end.txt"; endf.write_text(f"profile save {base}.txt\nsavebin {base}.bin $0 $100000\nprofile off\nb all\n")
    h.debug("b all", 0.3)
    s0 = len(h._logtext()); v = h.vbl()
    h.cmd(f"hatari-debug b VBL > {v+PROFV+25} :trace :once :file {endf}")
    time.sleep(0.3); h.cmd("hatari-debug profile on")
    h._wait_removed(s0, timeout=3000); time.sleep(2.0)
    # phase 2: stage trace with CycleCounter at the loop call sites
    ctx = h.R / "cyc.txt"; ctx.write_text("e pc\ne CycleCounter\ne VBL\n")
    h.debug("b all", 0.3)
    s0 = len(h._logtext()); v = h.vbl()
    for pc in SITES:
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {ctx}"); time.sleep(0.1)
    h.cmd(f"hatari-debug b VBL > {v+PROFV} :trace :once")
    h._wait_removed(s0, timeout=3000); time.sleep(1.0)
    text = h._logtext()[s0:]
finally:
    h.close()
recs = []
for blk in text.split("CPU breakpoint condition(s) matched")[1:]:
    m = [int(x) for x in NUM.findall(blk)]
    if len(m) >= 3 and m[0] in SITES: recs.append(m[:3])
txt = Path(f"{base}.txt").read_text()
m = re.search(r"^%08x .*\((\d+), \d+, \d+, \d+\)$" % VBLH, txt, re.M)
json.dump(dict(game=game, snap=snap, mhz=mhz, fps=f, recs=recs, vblh=int(m.group(1)) if m else None, profv=PROFV), open(f"{base}.json", "w"))
print("DONE", base, "recs", len(recs), "vbl handler runs", m.group(1) if m else None, flush=True)
