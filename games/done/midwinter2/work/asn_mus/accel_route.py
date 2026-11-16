#!/usr/bin/env python3
"""Accelerated-time (Auto Route) run from a 3D-view snapshot, sampling the music state at least 2x per emulated second.

    python3 work/asn_mus/accel_route.py SNAP TAG [--wp x,y ...]   (SNAP = a .sav path; TAG names the output dir work/asn_mus/accel/TAG)

Steps (screenshot coordinates): F5 -> map (wait for the scroll-in) -> hover the key (140,415) -> click the 6th icon (waypoint mode, $40b6 != 0)
-> for each waypoint: move there + SPACE (appends to the list at $10d5e) -> hover the key -> click the far-left icon ($31116: starts the
route, $37922 sets $40b8) -> wait until $40b6 == 0 again (route end, $37658 clears it).
Sampling: breakpoint `b pc = $262c2 :25 :trace :file samp.txt` (the game's VBL handler, every 25th VBL) dumps the state; WAV via recsound.
"""
import argparse, os, re, shutil, struct, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import asn_live
from mw2harness import Hatari

ap = argparse.ArgumentParser()
ap.add_argument("snap"); ap.add_argument("tag")
ap.add_argument("--wp", nargs="*", default=["660,150", "560,330", "680,435", "470,440"])
ap.add_argument("--max-wall", type=int, default=2400)
ap.add_argument("--exact", action="store_true", help="exact VBLs of every tune request / start / park / 3D-tick restore (extra breakpoints), stop 6 s after tune 5 ended")
a = ap.parse_args()
OUT = ROOT / "work/asn_mus/accel" / a.tag
OUT.mkdir(parents=True, exist_ok=True)
asn_live.setup_home(); os.environ["HOME"] = str(asn_live.HOME); os.environ["SDL_AUDIODRIVER"] = "dummy"
h = Hatari(snapshot=str(ROOT / a.snap) if not a.snap.startswith("/") else a.snap, machine="ste", memsize_kb=1024, extra=["--sound", "50066"])
LOG = []
def L(*x):
    s = " ".join(str(v) for v in x); LOG.append(s); print(s, flush=True)

def rd(addr, n):
    nn = len(h._logtext()); h.cmd(f"hatari-debug m ${addr:x} {n}"); time.sleep(0.6)
    out = h._logtext()[nn:]; got = {}
    for mm in re.finditer(r"^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", out, re.M | re.I):
        a0 = int(mm.group(1), 16)
        for i, x in enumerate(mm.group(2).split()): got[a0 + i] = int(x, 16)
    return bytes(got.get(addr + i, 0) for i in range(n))

def w16(addr): return int.from_bytes(rd(addr, 2), "big")
def shot(name): h.shot(OUT / f"{a.tag}_{name}.png")

CMDS = ["e VBL", "m $5138 4", "m $7626 2", "m $b96 4", "m $b9a 1", "m $ba2 2", "m $bbe00 24", "m $bbed0 4", "m $ff8901 1", "m $ff8909 3", "m $ff8921 1",
        "m $6220 2", "m $700a 2", "m $40b6 4", "m $bc0 16", "m $6888 2"]
cf = h.R / "samp.txt"; cf.write_text("\n".join(CMDS) + "\n")

try:
    L("snapshot VBL", h.vbl(), "$6220", hex(w16(0x6220)), "$5138", rd(0x5138, 4).hex(), "$7626", hex(w16(0x7626)))
    shot("00_start")
    h.debug("b all", 0.4)
    h.cmd(f"hatari-debug b pc = $262c2 :25 :trace :file {cf}")
    if a.exact:
        for nm, pc, extra in (("req321fe", 0x321fe, "r"), ("park33870", 0x33870, ""), ("rest338c2", 0x338c2, ""), ("ymstart_c6c", 0xc6c, ""), ("asn_mstart", 0xbf824, ""), ("setvec3225c", 0x3225c, "")):
            (h.R / f"{nm}.txt").write_text(f"e VBL\nm $7626 2\nm $b96 4\nm $5138 4\n{extra}\n")
            h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {h.R / (nm + '.txt')}"); time.sleep(0.4)
    mark = len(h._logtext())
    h.key("F5"); time.sleep(8)
    t0 = time.time()
    while time.time() - t0 < 120:                    # the map scroll-in is slow while the music mixer takes 30 % of the CPU
        time.sleep(3)
        if w16(0x5138 + 0) == 0 and False: pass
        if rd(0x5138, 4).hex() == "000bf81e" and time.time() - t0 > 22: break
    time.sleep(6); shot("01_map")
    h.goto(140, 415); time.sleep(2.5); shot("02_row")
    h.rel(390, 0, 10); time.sleep(1.2); h.click(); time.sleep(5)
    L("waypoint mode: $40b6 =", hex(w16(0x40b6)), "list", rd(0x10d5e, 8).hex())
    for i, p in enumerate(a.wp):
        x, y = map(int, p.split(","))
        h.goto(x, y); time.sleep(1.5); h.key("space"); time.sleep(2.0)
        L(f"waypoint {i} {p}: list", rd(0x10d5e, 24).hex())
        if i == 0: shot("03_wp0")
    shot("04_wps")
    h.goto(140, 415); time.sleep(2.5); shot("05_row2")
    h.cmd("hatari-shortcut recsound")                # (re)start the capture: the file starts here; asn_live.CAP is the config path
    time.sleep(0.5)
    v_go = h.vbl()
    L("click far-left icon at VBL", v_go)
    h.click(); t_go = time.time()
    nshot = 0
    quiet_since = None                                 # sustained "$40b6 == 0 with the 3D tick": the route is over (an island change clears it for ~3 s while the world reloads)
    while time.time() - t_go < a.max_wall:
        time.sleep(5)
        el = time.time() - t_go
        # latest complete sample block from the log (no fifo traffic of our own while the sampler runs)
        blks = [b for b in h._logtext()[mark:].split("> e VBL\n")[1:] if "> m $6888 2" in b and "Changed back" in b]
        if blks:
            b = blks[-1]
            m40 = re.search(r"^000040B6:\s+(\w\w) (\w\w)", b, re.M); m51 = re.search(r"^00005138:\s+(\w\w) (\w\w) (\w\w) (\w\w)", b, re.M)
            b6 = int(m40.group(1) + m40.group(2), 16) if m40 else -1; p5 = "".join(m51.groups()) if m51 else ""
        else:
            b6, p5 = -1, ""
        if int(el // 30) >= nshot:
            nshot += 1; shot(f"06_t{int(el):04d}")
        if a.exact and el > 30 and "> m $7626 2\n00007626: 00 05" in h._logtext()[mark:] and p5 == "00018f92":
            time.sleep(6); break
        if b6 == 0 and p5 == "00018f92" and el > 30:
            quiet_since = quiet_since or el
            if el - quiet_since > 25: break
        else:
            quiet_since = None
    L("route end (40b6 == 0 for 25+ s): wall", round(time.time() - t_go), "s; $40b6", hex(w16(0x40b6)), "$5138", rd(0x5138, 4).hex(), "VBL", h.vbl())
    shot("09_end")
    h.cmd("hatari-shortcut recsound"); time.sleep(1.0)
    if asn_live.CAP.exists():
        shutil.copy(asn_live.CAP, OUT / f"{a.tag}.wav"); L("wav", OUT / f"{a.tag}.wav", asn_live.CAP.stat().st_size)
    (OUT / "samples.log").write_text(h._logtext()[mark:])
    (OUT / "run.txt").write_text("\n".join(LOG) + f"\nVBL_GO {v_go}\n")
finally:
    h.close()
