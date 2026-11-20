#!/usr/bin/env python3
"""1 MB gate (machine ste | megaste, TOS default): cold boots of v1.0 and the campaign build b3, then
  1. marker, IB+4 flag, the campaign sites' bytes, $2dc/$42e/HAGA+$83 in the b3 RAM (list 2 must NOT be applied);
  2. F10 at the title behaves as any key (the game starts), then execution breakpoints over every campaign code range during ~40 s of driving: no hit;
  3. per-pass STATE A/B from the v1.0 race memstate: v1.0 as is vs v1.0 + the b3 payload image loaded (gate closed = no campaign site written) over N passes.
env.sh python3 ab1mb.py --machine ste [--passes 150]"""
import argparse, re, sys, time, shutil, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cplib import *
ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--passes", type=int, default=150); ap.add_argument("--skip-cold", action="store_true")
a = ap.parse_args()
M = a.machine
SITES = [(0x72c4, 6), (0x77da, 12), (0xfda2, 6), (0x731e, 6), (0x7252, 6), (0x74fe, 6), (0x8418, 6)]
RANGES = [(0xb8022, 0xb8070 + 0x52), (0xb8220, 0xb8260), (0xb9f00, 0xbab00)]   # campaign code (hooks, menu/reader)
STATE = [(0x1000, 0x400), (0x29C8, 0xB38), (0x4500, 0xB00), (0xDAE6, 4)]

def race_ready(h, tries=16):
    for k in range(tries):
        if h.peekl(0x23c0) != 0 and h.peekw(0x100e) > 30 and h.peekb(0x1021) == 2: return True
        h.keypress(57); time.sleep(6)
    return False

def cold(game, name, f10=False):
    h = Moonshine(machine=M, memsize_kb=1024, game_dir=str(game))
    try:
        ok = h.boot_to_race(log=lambda *x: None)           # true on the title
        log(f"[{name}] title reached {ok} vbl {h.vbl()} $23c0 {h.peekl(0x23c0):#x}")
        info = {"marker": mem(h, 0xb2700, 8).hex(), "2dc": h.peekl(0x2dc), "42e": h.peekl(0x42e), "haga83": mem(h, h.peekl(0x2dc) + 0x83, 1).hex()}
        info["sites"] = {hex(ad): mem(h, ad, n).hex() for ad, n in SITES}
        log(f"[{name}] {info}")
        if name == "b4":
            for i, (lo, hi) in enumerate(RANGES):
                h.cmd(f"hatari-debug b pc >= ${lo:x} && pc < ${hi:x} :trace")
            time.sleep(0.5)
            n0 = len(h._logtext())
        if f10:
            h.keypress(0x44); time.sleep(4)
            log(f"[{name}] after F10 at the title: $1021 {h.peekb(0x1021):#x} $100e {h.peekw(0x100e)} (menu would have drawn it)"); h.shot(str(HERE / f"snap/ab1m_{M}_{name}_f10.png"))
        ok = race_ready(h)
        log(f"[{name}] race ready {ok} vbl {h.vbl()}")
        h.debug("w $6105 $01", 0.3)
        v = h.vbl()
        while h.vbl() < v + 2000: time.sleep(2)
        log(f"[{name}] driving: $5ff8 {h.peekw(0x5ff8)} $130c {h.peekw(0x130c)} $100e {h.peekw(0x100e)}")
        if name == "b4":
            hits = [l for l in h._logtext()[n0:].splitlines() if "pc =" in l and ":trace" in l]
            h.debug("b all", 0.3)
            log(f"[{name}] EXEC BREAKPOINT HITS in the campaign code ranges (title incl. F10, race, 2000 VBL driving): {len(hits)}")
        h.debug("w $6105 $00", 0.3)
        if name == "v10":
            time.sleep(1); h.state = Path(__import__('os').environ["HOME"]) / ".config/hatari/hatari.sav"; h.state.unlink(missing_ok=True)
            h.savemem(str(HERE / f"snap/v10_{M}1m_race.sav")); h.state.unlink(missing_ok=True)
    finally:
        h.close()

def state_run(snap, image, npass):
    gd = HERE / "run_ab1m"; shutil.rmtree(gd, ignore_errors=True); shutil.copytree(Path("/tmp/camphd_v10/MOONSHR"), gd)
    h = Moonshine(snapshot=str(snap), game_dir=str(gd), machine=M, memsize_kb=1024)
    try:
        time.sleep(1.5)
        if image:
            h.debug(f"loadbin {image} $b2700", 1.5)
        f = h.R / "state.txt"
        f.write_text("e VBL\n" + "".join(f"m ${a_:x} {n}\n" for a_, n in STATE))
        h.debug("b all", 0.3); n0 = len(h._logtext())
        h.cmd(f"hatari-debug b pc = $7b86 :trace :file {f}")
        t0 = time.time()
        while h._logtext()[n0:].count("> e VBL") < npass + 2 and time.time() - t0 < 1500: time.sleep(1)
        h.debug("b all", 0.5); lg = h._logtext()[n0:]
    finally:
        h.close()
    res = {}
    for ht in lg.split("> e VBL")[1:]:
        d = {}
        for ln in ht.splitlines():
            m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
            if m:
                ad = int(m.group(1), 16)
                for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): d[ad + i] = x
        if 0x100E in d: res[(d[0x100E] << 8) | d[0x100F]] = d
    return res

if not a.skip_cold:
    cold(Path("/tmp/camphd_v10/MOONSHR"), "v10")
    cold(HERE / "b4", "b4", f10=True)
# full b3 payload image (what the new build's RAM holds at $B2700), gate closed: no site written
sel, fsel = P.default_selection(P.load_patches(), P.load_file_patches(), False)
img, _ = P.build_image(sel, fnames=[p.name for p in fsel])
(HERE / "b4_image.bin").write_bytes(img)
snap = HERE / f"snap/v10_{M}1m_race.sav"
A = state_run(snap, None, a.passes); B = state_run(snap, HERE / "b4_image.bin", a.passes)
common = sorted(set(A) & set(B)); diff = 0; cmp_ = 0
for k in common:
    for ad, x in A[k].items():
        if ad in B[k]:
            cmp_ += 1; diff += B[k][ad] != x
log(f"STATE A/B ({M} 1 MB): passes A {len(A)} B {len(B)} common {len(common)}  bytes compared {cmp_}  different {diff}  -> {'IDENTICAL' if diff == 0 and len(common) >= a.passes * 0.9 else 'DIFFER/INSUFFICIENT'}")
