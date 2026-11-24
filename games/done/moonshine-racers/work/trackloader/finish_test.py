#!/usr/bin/env python3
"""Finish/win rule experiment in a restored race snapshot of the patched HD build (standing start, level 0).
   The next object of the stream ($133a: (type, lateral, gap) words) is overwritten with the level's finish type (sprite $21) so it spawns right away,
   the car is driven straight (joystick up, $6105=1) and the state variables are sampled until the race ends.
   finish_test.py --snap SNAP --machine ste --mem 4096 [--poke-102c 14] [--no-finish-obj] [--type 26] [--secs 150]
   Samples: $1024 (race end state), $5ff8 (world position), $130c (speed), $10ce.w (time bar), $102c, $1027, $1226, $11b1, $10ca, and the finish object's slot ($2d80.., 56 B each, sprite word +6 == $21; +$20 = distance ahead)."""
import argparse, re, struct, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
G = HERE.parents[1]
sys.path.insert(0, str(G / "tools")); sys.path.insert(0, str(G.parents[2] / "tools"))
from msr import Moonshine
from stharness import TOS
ap = argparse.ArgumentParser()
ap.add_argument("--snap", required=True); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=4096); ap.add_argument("--tos")
ap.add_argument("--game", default="/tmp/msrl_dist/MOONSHR"); ap.add_argument("--type", type=int, default=26, help="S4 type word of level 0's sprite-$21 type (finish_objs.py)")
ap.add_argument("--poke-102c", type=int); ap.add_argument("--no-finish-obj", action="store_true"); ap.add_argument("--secs", type=float, default=150)
ap.add_argument("--tag", default="fin"); ap.add_argument("--poke5ff8", type=int, help="write $5ff8 to this value at the start (does NOT move the object stream)")
ap.add_argument("--steer", action="store_true")
a = ap.parse_args()
kw = {"tos": TOS[a.tos]} if a.tos else {}
h = Moonshine(snapshot=a.snap, game_dir=a.game, machine=a.machine, memsize_kb=a.mem, **kw)
log = lambda *x: print(*x, flush=True)

def mem(addr, n):
    """m dump parsed to bytes; waits until the last line of the dump is in the log (the debugger answers asynchronously)."""
    n0 = len(h._logtext()); h.cmd(f"hatari-debug m ${addr:x} {n}")
    last = addr + ((n - 1) // 16) * 16
    t = time.time(); out = ""
    while time.time() - t < 8:
        time.sleep(0.15)
        out = h._logtext()[n0:]
        if re.search(rf"^{last:08x}:", out, re.I | re.M):
            time.sleep(0.1); out = h._logtext()[n0:]; break
    b = bytearray()
    for ln in out.splitlines():
        m = re.match(r"\s*([0-9a-fA-F]{8}):\s+((?:[0-9a-fA-F]{2} )*[0-9a-fA-F]{2})(?:  |$)", ln)
        if m and addr <= int(m.group(1), 16) < addr + n: b += bytes.fromhex(m.group(2).replace(" ", ""))
    return bytes(b[:n])
W = lambda b, o: struct.unpack(">H", b[o:o + 2])[0]
def sample(tag=""):
    b = mem(0x1000, 0x240)          # $1000-$123f: $1024 $1027 $102c $10ca $10ce $10d2 $10d8 $11b1 $1226 ...
    c = mem(0x5FF8, 2); d = mem(0x130C, 2)
    slots = mem(0x2D80, 56 * 32)
    fin = None
    for i in range(32):
        s = slots[i * 56:(i + 1) * 56]
        if len(s) == 56 and W(s, 6) == 0x21 and s[4] & 1: fin = (i, struct.unpack(">h", s[0x20:0x22])[0])
    st = dict(t1024=b[0x24], c1027=b[0x27], l102c=W(b, 0x2c), pos10ca=W(b, 0xca), bar10ce=W(b, 0xce), t1226=b[0x226], m11b1=b[0x1b1], m11ab=b[0xab],
              p5ff8=W(c, 0), s130c=W(d, 0), mode1021=b[0x21], fin_slot=fin)
    try: v = h.vbl()
    except Exception: v = -1
    log(f"[{time.time() - T0:5.1f}s vbl {v}] {tag}", st)
    return st
try:
    time.sleep(3)
    T0 = time.time()
    st = sample("start")
    p133a = struct.unpack(">I", mem(0x133A, 4))[0]; p1346 = W(mem(0x1346, 2), 0)
    log(f"object stream pointer $133a={p133a:#x} spawn counter $1346={p1346}; next entry words:", [hex(W(mem(p133a, 6), o)) for o in (0, 2, 4)])
    if not a.no_finish_obj:
        h.debug(f"w ${p133a:x} ${a.type >> 8:02x} ${a.type & 255:02x} $00 $00", 0.8)
        log("overwrote the next object with type", a.type, "lateral 0:", [hex(W(mem(p133a, 6), o)) for o in (0, 2, 4)])
    if a.poke_102c is not None:
        h.debug(f"w $102c ${a.poke_102c >> 8:02x} ${a.poke_102c & 255:02x}", 0.8); log("poked $102c =", a.poke_102c)
    if a.poke5ff8 is not None:
        h.debug(f"w $5ff8 ${a.poke5ff8 >> 8:02x} ${a.poke5ff8 & 255:02x}", 0.8); log("poked $5ff8 =", a.poke5ff8)
    h.drive(True)
    last = None; n = 0
    while time.time() - T0 < a.secs:
        st = sample()
        key = (st["t1024"], st["l102c"], st["t1226"], st["mode1021"])
        if key != last:
            h.shot(str(HERE / "snap" / f"{a.tag}_{n:02d}_t1024_{st['t1024']:02x}_l{st['l102c']:04x}.png")); n += 1; last = key
        if a.steer: pass
        time.sleep(1.0)
    h.drive(False)
finally:
    h.close()
