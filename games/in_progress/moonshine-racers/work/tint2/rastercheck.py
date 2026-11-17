"""Raster / blitter trace of the integrated build during a steered drive (STE 8 MHz).
python3 rastercheck.py VARIANT SNAP NVBL OUT.txt [trace=video_color|blitter|video_color,blitter] [zig=KEY] [skip=VBL]
VARIANT: A stock, X default (tb_blit on), NB = default without tb_blit* (same tick, same extras), NRB = default without ta_rb/ta_rb0 (stock Timer B list)
Hatari --trace <flags> to a log file; the window starts after the live apply and `skip` VBL; steering = zig (up/up+left/up/up+right, 15 passes each) as a pure function of $100e.
OUT.txt = the trace lines of the window (video_color: 'write col addr=ff82xx col=.. line_cyc_w=.. nHBL=.. pc=..', blitter: Hatari's blitter lines)."""
import sys, re, time, os
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2")
from mxlib_fin import *
variant, snap, nvbl, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
opt = {a.split("=")[0]: a.split("=", 1)[1] for a in sys.argv[5:] if "=" in a}
flags = opt.get("trace", "video_color")
KS = int(opt["zig"]) if "zig" in opt else None
skip = int(opt.get("skip", 20))
SETS["NB"] = [n for n in SETS["X"] if not n.startswith("tb_blit")]
SETS["NRB"] = [n for n in SETS["X"] if n not in ("ta_rb", "ta_rb0")]
h = Moonshine(snapshot=str(SNAPDIR / snap), extra=["--trace", flags])
try:
    time.sleep(2)
    nm = None if variant == "A" else SETS[variant]
    if nm: apply_names(h, nm, variant)
    time.sleep(1)
    h.debug("b all", 0.3)
    if KS is not None:
        for K in range(KS, KS + 1900):
            (h.R / f"z_{K}.txt").write_text(f"w $6105 ${[1, 5, 1, 9][((K - KS) // 15) % 4]:02x}\nb pc = $7a88 && ($100e).w = ${K + 1:x} :trace :once :file {h.R}/z_{K + 1}.txt\n")
        h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = ${KS:x} :trace :once :file {h.R}/z_{KS}.txt")
    v1 = h.vbl() + skip
    while h.vbl() < v1: time.sleep(0.5)
    n0 = len(h._logtext()); v0 = h.vbl(); t0 = time.time()
    while h.vbl() < v0 + nvbl and time.time() - t0 < 3000: time.sleep(1)
    lg = h._logtext()[n0:]
    p0 = h.peekw(0x100e)
    open(out, "w").write(lg)
    print(variant, snap, "VBL", h.vbl() - v0, "log bytes", len(lg), "$100e at end", p0, "BST $b5800", (h.debug("m $b5800 1", 0.6).strip().splitlines()[0][:24] if nm else "-"), flush=True)
finally:
    h.close()
