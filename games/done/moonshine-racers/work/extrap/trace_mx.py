"""sample the blob state every STEP VBLs: python3 trace_mx.py SNAP MHZ N STEP [poke addr=hex]"""
import sys, re; sys.path.insert(0, '../timing'); sys.path.insert(0, '../tick'); sys.path.insert(0, '.')
from tlib import *
from live import *
from mxlive import apply_mx
snap, mhz, N, STEP = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
pokes = [(int(x.split('=')[0], 16), bytes.fromhex(x.split('=')[1])) for x in sys.argv[5:] if '=' in x]
CAP = ["e VBL", "m $1020 8", "m $11b0 4", "m $1226 2", "m $b8f00 12", "m $b8f24 16", "m $b8f38 12", "m $100e 2", "m $130c 2", "m $b8f20 2"]
h = open_snap(snap, mhz)
try:
    apply_mx(h, pokes=pokes)
    time.sleep(1)
    v = h.vbl()
    caps = []
    for i in range(N):
        f = h.R / f"cap{i}.txt"; f.write_text("\n".join(CAP) + "\n")
        h.cmd(f"hatari-debug b VBL > {v + 20 + i * STEP} :trace :once :file {f}")
    n0 = len(h._logtext())
    t0 = time.time()
    while h._logtext()[n0:].count("Removed CPU breakpoint") < N:
        if time.time() - t0 > 900: raise TimeoutError
        time.sleep(0.5)
    time.sleep(0.5)
    log = h._logtext()[n0:]
    for part in log.split("Reading debugger commands")[1:]:
        g = {}
        for ln in part.splitlines():
            m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
            if m:
                a = int(m.group(1), 16)
                for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + i] = x
        mv = re.search(r"#(\d+) \(dec\)", part)
        w = lambda a: (g[a] << 8) | g[a + 1]; l = lambda a: (w(a) << 16) | w(a + 2)
        print(f"vbl {mv.group(1)} clk {l(0xb8f00)} next {l(0xb8f04)} DEXT {w(0xb8f24)} DPREV {w(0xb8f26)} KCUM {w(0xb8f28)} V {w(0xb8f2c)} frames {l(0xb8f38)} groups {l(0xb8f3c)} ticks {l(0xb8f40)} pass {w(0x100e)} spd {w(0x130c)} off {g[0xb8f20]} 1021={g[0x1021]:02x} 1024={g[0x1024]:02x} 11b0-3={g[0x11b0]:02x}{g[0x11b1]:02x}{g[0x11b2]:02x}{g[0x11b3]:02x} 1226={g[0x1226]:02x}")
finally:
    h.close()
