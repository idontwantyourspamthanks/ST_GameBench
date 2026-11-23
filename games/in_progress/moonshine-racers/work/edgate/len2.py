#!/usr/bin/env python3
"""WP-B gate: a race length per track (MSTRACKS.TRK version 2) and the v1 A/B.  cp_len (hook $B8260 at $7926) + cp_fetch (V_RLEN = CPV+16).
   envab.sh python3 len2.py --kind hd|fl --machine ste|megaste|st --mem 2048 --build DIR --camp FILE.trk [--track K] [--mode to|drive|info] [--tag X]
Cold boot of the built release, load the campaign through the F10 menu (HD: FILES\\MSTRACKS.TRK; floppy: a campaign disk made with msrtrack.py disk, in drive A), play from track K (Down x K, Return).
  info   race start state: $57890, $10d2, $102c, $10ce (raw line) and the prediction of work/notes/editor_design.md 17.9 for the entry's word
  to     stand still: breakpoints at $792c (the end of the race setup) and $117be (the game sets the time-up flag): `$100e` (the pass counter) at both = the passes the time bar allowed; fast-forward
  drive  joystick up (debugger write of $6105) flat out until the race is over; the finish state ($1226 time-up flag, $1027 time-out count, clock high word, $100e, $5ff8)
Prediction: rate_stock = (100 + $102c) * Lb / 200 + (10 - $edcc[$102c]) * 200; Tb = $ff0000 // rate_stock; P = (Tb - 100) * L // Lb + 100; rate = $ff0000 // P (0xffff when P < 255);
a word 0 / a v1 track keeps rate_stock, $57890 = Lb.  The game flags time-up when the clock's high word has reached $ff: ceil($ff0000 / rate) passes counted on $100e from the setup end (the first logs of this gate predicted that +1; every measured value, stock and v1 controls included, was exactly one less)."""
import argparse, sys, struct, time, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "campgate"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from cg import *
import msrtrack as M

ap = argparse.ArgumentParser()
ap.add_argument("--kind", default="hd"); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--build", required=True); ap.add_argument("--camp", required=True); ap.add_argument("--track", type=int, default=0)
ap.add_argument("--mode", default="info", help="info | to | drive | seq (race the whole campaign: every race flat out to the BAR through the real shop; checks each race's state)"); ap.add_argument("--tag"); ap.add_argument("--noff", action="store_true")
a = ap.parse_args()
KIND = a.kind
camp_path = Path(a.camp)
ents = M.parse_campaign(camp_path.read_bytes())
ent = ents[a.track]
short = {'ste': 'ste', 'megaste': 'mste', 'st': 'st', 'megast': 'mst'}[a.machine] + str(a.mem // 1024) + "m"
tag = a.tag or f"len2_{KIND}_{camp_path.stem}_t{a.track}_{a.mode}_{short}"
logopen(tag)
EDCC = (8, 10, 6, 7, 5, 6, 5, 5, 5, 1, 4, 5, 1, 14, 5)
def predict(e):
    """-> (base, word, Lb, rate_stock, Tb, P, rate, $57890, passes to the time-up flag)"""
    base, word = e["base"], e["race"]
    Lb = M.LEVELS[base][M.LEV_LEN]
    rate_stock = ((100 + base) * Lb // 200 + (10 - EDCC[base]) * 200) & 0xFFFF
    Tb = 0xff0000 // rate_stock
    if word:
        P = (Tb - 100) * word // Lb + 100
        rate = 0xff0000 // P if P >= 255 else 0xffff
        exp_len = word
    else:
        P, rate, exp_len = Tb, rate_stock, Lb
    return base, word, Lb, rate_stock, Tb, P, rate, exp_len, -(-0xff0000 // rate)
base, word, Lb, rate_stock, Tb, P, rate, exp_len, passes = predict(ent)
log(f"== {tag}: {KIND} {MACH[a.machine]} {a.mem // 1024} MB build {a.build}  campaign {camp_path} (v{ent['version']}) track {a.track} '{ent['name']}' base {base} word {word} Lb {Lb}")
log(f"PREDICT: rate_stock {rate_stock}  Tb {Tb}  P {P}  rate {rate:#06x}={rate}  $57890 {exp_len}  time-up flag after {passes} passes ($100e from the setup end)")

build = a.build
disk_a = Path(build) / "disk_a.st" if KIND == "fl" else None
d2 = Path(build) / "disk_b.st" if KIND == "fl" else None
camp_disk = None
if KIND == "fl":
    import tempfile
    camp_disk = Path(tempfile.mkdtemp(prefix="len2disk_", dir=os.environ.get("CG_TMP", "/tmp")) ) / "camp.st"
    camp_disk.write_bytes(M.build_disk(camp_path.read_bytes()))
r = Run(KIND, a.machine, a.mem, tag, build=build, camp_hd=camp_path if KIND == "hd" else None, disk_a=disk_a, d2=d2, noff=a.noff)
ITEM = 1 if KIND == "hd" else 1     # HD: LOAD FROM HARD DISK = item 1; floppy: LOAD FROM DRIVE A = item 1

def goto_item(n):
    for _ in range(8):
        s = r.w(0x100406)
        if s == n: return True
        r.key(0x50 if s < n else 0x48); time.sleep(0.6)
    return r.w(0x100406) == n

def load(wait=120):
    goto_item(ITEM)
    if KIND == "fl": r.insert("a", camp_disk)
    r.key(0x1c); t0 = time.time(); time.sleep(1)
    while time.time() - t0 < wait:
        if r.b(V["loaded"]): break
        if r.menu_msg(): break
        time.sleep(0.4)
    return r.b(V["loaded"]) != 0

def raw():
    return (f"vbl={r.vbl()} $102c={r.w(0x102c):#06x} $57890={r.w(0x57890)} $10d2={r.w(0x10d2)} $10ce={r.l(0x10ce):#010x} $100e={r.w(0x100e)} $5ff8={r.w(0x5ff8)} "
            f"$1024={r.b(0x1024):#04x} $1226={r.b(0x1226):#04x} $1027={r.b(0x1027):#04x} V_RLEN={r.w(0xb8e10)} $23c0={r.l(0x23c0):#x}")

def arm(spec):
    """breakpoints (pc -> [(addr, n)]) whose hit dumps the memory; returns (events fn)"""
    r.h.debug("b all", 0.3)
    for pc, mm in spec.items():
        f = r.h.R / f"dump_{pc:x}.txt"; f.write_text("".join(f"m ${ad:x} {n}\n" for ad, n in mm))
        r.h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {f}"); time.sleep(0.2)
    n0 = len(r.h._logtext())
    def events():
        txt = r.h._logtext()[n0:]
        out = []
        parts = re.split(r"pc = \$([0-9a-f]+) :trace", txt)
        for i in range(1, len(parts), 2):
            pc = int(parts[i], 16); body = parts[i + 1]; vals = {}
            for ad, n in spec[pc]:
                m = re.search(rf"^\s*{ad:08x}:\s+((?:[0-9a-fA-F]{{2}} ?)+)", body, re.I | re.M)
                if m: vals[ad] = bytes.fromhex(m.group(1).replace(" ", ""))[:n]
            out.append((pc, vals))
        return out
    return events

try:
    r.ff(False)
    if not r.boot_title(): log("BOOT FAILED"); sys.exit(2)
    r.menu_open()
    ok = load(); check("campaign loaded", ok)
    cv = r.mem(V["act"], 12); log(f"loaded: act={cv[0]:#x} loaded={cv[1]:#x} count={W(cv, 2)}")
    check("campaign file version seen by the loader's validator: accepted", ok and W(cv, 2) == len(ents), f"count={W(cv, 2)} expect {len(ents)}")
    time.sleep(1); r.shot("list")
    if a.mode == "seq":
        DUMPS = [(0x100e, 2), (0x10ce, 4), (0x10d2, 2), (0x57890, 2), (0x5ff8, 2), (0x1027, 1)]
        ev = arm({0x117be: DUMPS})
        r.key(0x1c)
        for i, e in enumerate(ents):
            base_, word_, Lb_, rs_, Tb_, P_, rate_, exp_, passes_ = predict(e)
            res = r.wait_race(tmo=400)
            check(f"race {i} '{e['name']}' started", res is not None)
            if res is None: break
            ln, c102c, p23c0, pos_ = res
            rt = r.w(0x10d2)
            log(f"START race {i} (base {base_}, word {word_}): " + raw())
            check(f"race {i}: $102c = base {base_}, $57890 = {exp_} ({'own' if word_ else 'base level'}), $10d2 = {rate_}, V_RLEN = {word_}",
                  c102c == base_ and ln == exp_ and rt == rate_ and r.w(0xb8e10) == word_, f"$102c={c102c:#x} $57890={ln} $10d2={rt} V_RLEN={r.w(0xb8e10)}")
            r.poke(0x6105, 0x01)
            if not a.noff: r.ff(True)
            t0 = time.time(); state = None; n0 = len(ev())
            while time.time() - t0 < 400:
                time.sleep(0.3)
                if len(ev()) > n0: state = "timed out"; break
                if r.b(0x1024) == 0xff: state = "BAR reached"; break
            r.ff(False); r.poke(0x6105, 0x00); time.sleep(0.5)
            clk = r.l(0x10ce)
            log(f"RACE {i} ended: {state}; clock {clk:#010x} = {clk / rate_:.0f} of {0xff0000 / rate_:.0f} passes; $5ff8={r.w(0x5ff8)}; " + raw())
            check(f"race {i}: the BAR ended it before the time bar ran out", state == "BAR reached", f"state={state}")
            if state != "BAR reached": break
        log(f"Bus/Address error lines: {r.errlines()}")
        raise SystemExit(0 if not FAILS else 1)
    for _ in range(a.track): r.key(0x50); time.sleep(0.6)
    pos = r.w(0x100406); log(f"list selection {pos} (expect {a.track})")
    DUMP = [(0x100e, 2), (0x10ce, 4), (0x10d2, 2), (0x57890, 2), (0x5ff8, 2), (0x1027, 1)]
    ev = arm({0x792c: DUMP, 0x117be: DUMP})
    r.key(0x1c)                                                       # play from the selected track
    res = r.wait_race(tmo=400)
    check("race started", res is not None)
    if res is None: raise SystemExit(1)
    ln, c102c, p23c0, pos_ = res
    log("START " + raw())
    check(f"$102c = base level {base}", c102c == base, f"$102c={c102c:#x}")
    check(f"$57890 = {exp_len} ({'the track' + chr(39) + 's own length' if word else 'the base level' + chr(39) + 's'})", ln == exp_len, f"$57890={ln}")
    rt = r.w(0x10d2)
    check(f"time bar rate $10d2 = {rate} (prediction)", rt == rate, f"$10d2={rt}")
    log(f"RATE passes allowed by the bar: $ff0000/{rt} = {0xff0000 / rt:.2f}")
    if a.mode == "to":
        r.poke(0x6105, 0x00)
        t0 = time.time(); r.ff(True)
        while time.time() - t0 < 600:
            time.sleep(1.0)
            if any(pc == 0x117be for pc, _ in ev()): break
        r.ff(False); time.sleep(1)
        evs = ev(); log("EVENTS", [(hex(pc), {hex(k): v.hex() for k, v in d.items()}) for pc, d in evs])
        setup = [d for pc, d in evs if pc == 0x792c]; up = [d for pc, d in evs if pc == 0x117be]
        if setup and up:
            p0 = struct.unpack(">H", setup[-1][0x100e])[0]; p1 = struct.unpack(">H", up[0][0x100e])[0]
            n = (p1 - p0) & 0xffff
            c = struct.unpack(">I", up[0][0x10ce])[0]
            log(f"TIMEOUT: $100e at the setup end {p0}, at the time-up flag {p1}: {n} passes; clock then {c:#010x}; prediction {passes}; difference {n - passes:+d}")
            check(f"time-out after {passes} +-2 passes (measured {n})", abs(n - passes) <= 2)
        else:
            check("both breakpoints hit", False, f"setup {len(setup)} up {len(up)}")
        log("END " + raw())
    elif a.mode == "drive":
        # joystick up (debugger write of $6105) until the race is over: $1024 == $ff (BAR reached) or the time-up flag $1226 == 5 / the time-out counter $1027 grew (the clock ran out)
        r.poke(0x6105, 0x01)
        if not a.noff: r.ff(True)
        t0 = time.time(); state = None
        while time.time() - t0 < 600:
            time.sleep(0.3)
            if any(pc == 0x117be for pc, _ in ev()): state = "timed out"; break      # the game set the time-up flag
            if r.b(0x1024) == 0xff: state = "BAR reached"; break
        r.ff(False); time.sleep(0.5); r.poke(0x6105, 0x00)
        up = [d for pc, d in ev() if pc == 0x117be]
        log(f"DRIVE ended: {state}; " + raw()); r.shot("over")
        if up:
            d = up[0]; p1 = struct.unpack(">H", d[0x100e])[0]
            log(f"TIMEOUT: the time-up flag was set after {p1} passes with $5ff8={struct.unpack('>H', d[0x5ff8])[0]} of the BAR near {exp_len}; clock {struct.unpack('>I', d[0x10ce])[0]:#010x}")
        else:
            clk = r.l(0x10ce); log(f"FINISH {state}: clock {clk:#010x} = {clk / rate:.0f} of {0xff0000 / rate:.0f} passes used (rate {rate}); $5ff8={r.w(0x5ff8)} at the end; BAR near unit {exp_len}")
        check("the BAR ended the race before the time bar ran out", state == "BAR reached" and not up, f"state={state}")
    log(f"Bus/Address error lines: {r.errlines()}")
finally:
    log(f"== {tag} done: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}; bus/address error lines {r.errlines()}")
    r.close()
sys.exit(1 if FAILS else 0)
