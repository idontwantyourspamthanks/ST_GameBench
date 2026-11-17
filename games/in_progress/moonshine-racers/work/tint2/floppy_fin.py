"""Floppy cold boot + >= 2-minute steered drive of the integrated build.
python3 floppy_fin.py DISK_A DISK_B MACHINE MEM TOS NAME [native_secs=70] [fast_secs=60]
msrfloppy.gate (disk A alone, story screens, disk-2 swap, race) then a wall-clock steered drive (up / up+left / up / up+right, 4 s each, written to $6105)
at the native clock, then at 16 MHz; samples $1021 / $100e / extra-frame counters $b8f38 every 10 s."""
import sys, time, re
from argparse import Namespace
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers")
sys.path.insert(0, str(G / "tools"))
import msrfloppy as F
disk_a, disk_b, machine, mem, tos, name = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], sys.argv[6]
nat = int(sys.argv[7]) if len(sys.argv) > 7 else 70
fast = int(sys.argv[8]) if len(sys.argv) > 8 else 60
h = F.mk(disk_a, None, machine, mem, tos)
def mm(a, n): return h.debug(f"m ${a:x} {n}", 0.8).strip().splitlines()[-1]
def ctr():
    out = h.debug("m $b8f38 12", 0.8); g = {}
    for ln in out.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
    l = lambda o: int.from_bytes(bytes(g[0xb8f38 + o + i] for i in range(4)), "big")
    return l(0), l(4), l(8)
try:
    F.gate(h, Namespace(name=name, disk_b=disk_b, timeout=400, cpu=0))
    ZIG = [0x01, 0x05, 0x01, 0x09]
    for label, secs, mhz in (("native", nat, 0), ("16MHz", fast, 16)):
        if mhz: h.set_cpuclock(mhz)
        v0 = h.vbl(); c0 = ctr(); p0 = h.peekw(0x100e); t0 = time.time(); k = 0; last = 0
        while time.time() - t0 < secs:
            time.sleep(1.0); k += 1
            h.debug(f"w $6105 ${ZIG[(k // 4) % 4]:02x}", 0.1)
            if time.time() - last > 10:
                last = time.time()
                print(f"  [{label}] t={int(time.time() - t0)}s mode $1021={F.peekb(h, 0x1021)} $100e={h.peekw(0x100e)} extras={ctr()} vbl={h.vbl() - v0}", flush=True)
        c1 = ctr(); dv = h.vbl() - v0
        print(f"DRIVE {label}: {int(time.time() - t0)} s wall, {dv} VBL, $100e {p0} -> {h.peekw(0x100e)}, extra frames {c1[0] - c0[0]} (groups {c1[1] - c0[1]}), $1021={F.peekb(h, 0x1021)}", flush=True)
    log = h._logtext()
    print("END marker $b2700:", mm(0xb2700, 8), "| road magic", mm(0xc0000, 8), "| bus/address error lines", len(re.findall("Bus Error|Address Error", log)), "| alive", h.proc.poll() is None)
    print("shot", h.shot(str(G / "work/tint2/shots" / f"floppy_{name}_end.png")))
finally:
    h.close()
