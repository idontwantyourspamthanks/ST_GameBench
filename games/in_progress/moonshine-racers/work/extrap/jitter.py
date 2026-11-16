"""main-frame flip intervals and extra-frame spacing from the blob's flip log, sampled repeatedly: python3 jitter.py SNAP MHZ NSAMPLES STEPVBL"""
import sys, re; sys.path.insert(0, '../timing'); sys.path.insert(0, '../tick'); sys.path.insert(0, '.')
from tlib import *
from live import *
from mxlive import apply_mx
snap, mhz, N, STEP = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
CAP = ["e VBL", "m $b8f44 2", "m $b8f80 64", "m $b8fc0 64"]
h = open_snap(snap, mhz)
try:
    apply_mx(h); time.sleep(1)
    v = h.vbl()
    for i in range(N):
        f = h.R / f"cap{i}.txt"; f.write_text("\n".join(CAP) + "\n")
        h.cmd(f"hatari-debug b VBL > {v + 30 + i * STEP} :trace :once :file {f}")
    n0 = len(h._logtext()); t0 = time.time()
    while h._logtext()[n0:].count("Removed CPU breakpoint") < N:
        if time.time() - t0 > 900: raise TimeoutError
        time.sleep(0.5)
    time.sleep(0.5)
    log = h._logtext()[n0:]
    mains = []; allint = []; ks = {}
    for part in log.split("Reading debugger commands")[1:]:
        g = {}
        for ln in part.splitlines():
            m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
            if m:
                a = int(m.group(1), 16)
                for k, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): g[a + k] = x
        w = lambda a: (g[a] << 8) | g[a + 1]
        i = w(0xb8f44)
        fl = [w(0xb8f80 + 2 * ((i + k) % 32)) for k in range(32)]; kl = [w(0xb8fc0 + 2 * ((i + k) % 32)) for k in range(32)]
        for k in range(1, 32):
            d = (fl[k] - fl[k - 1]) & 0xffff
            allint.append((kl[k], d))
        mt = [fl[k] for k in range(32) if kl[k] == 0]
        for a, b in zip(mt, mt[1:]): mains.append((b - a) & 0xffff)
    from collections import Counter
    print(f"{mhz} MHz: main-flip intervals (clock units, 36 = on grid):", sorted(Counter(mains).items()))
    first = Counter(d for k, d in allint if k == 0)
    print("   interval from any frame to the next MAIN frame:", sorted(first.items()))
    print("   intervals between flips (all):", sorted(Counter(d for k, d in allint).items()))
finally:
    h.close()
