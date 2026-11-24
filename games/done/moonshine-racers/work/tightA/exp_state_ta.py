"""Per-pass state at $7b86 keyed by $100e (Hatari). python3 exp_state_ta.py SNAP PATCHLIST|stock NPASS OUT.json [hold]"""
import sys, json, re, time, os
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/tools')
os.environ.setdefault('MSRPATCH_TOOL', GAME + '/work/tightA/msrpatch_priv.py'); os.environ.setdefault('MSR_LIVETAG', '_tA')
import msrabtest as ab
from msr import Moonshine
snap, plist, npass, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
RANGES = [(0x1000, 1024), (0x29c8, 2872), (0x4500, 2816), (0xdae6, 4), (0x1bb0, 12), (0x23bc, 16), (0x27c8, 38), (0x3500, 512), (0xdafe, 4), (0x6100, 24)]
names = None if plist == 'stock' else plist.split(',')
live = ab.live_build(names) if names else None
mhz = next((int(a[4:]) for a in sys.argv[5:] if a.startswith('mhz=')), 0)
h = Moonshine(snapshot=ab.snap_path(snap))
try:
    time.sleep(3 if mhz else 1.5)
    if mhz: h.set_cpuclock(mhz); time.sleep(1)
    if live: ab.apply_live(h, live, 0x7A88)
    time.sleep(0.4)
    f = h.R / "state.txt"
    f.write_text("e VBL\n" + "".join(f"m ${a:x} {n}\n" for a, n in RANGES))
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    if "hold" in sys.argv[5:]:
        (h.R / "hold.txt").write_text("w $6105 $01\n"); h.cmd(f"hatari-debug b pc = $7a88 :trace :file {h.R}/hold.txt")
    h.cmd(f"hatari-debug b pc = $7b86 :trace :file {f}")
    t0 = time.time()
    while h._logtext()[n0:].count("> e VBL") < npass:
        if time.time() - t0 > 1500: break
        if 'Address Error' in h._logtext()[n0:] or 'Bus Error' in h._logtext()[n0:]: print('CRASH detected'); break
        time.sleep(1)
    h.debug("b all", 0.5)
    log = h._logtext()[n0:]
finally:
    h.close()
res = []
for ht in log.split("> e VBL")[1:]:
    mem = {}
    m = re.search(r"#(\d+) \(dec\)", ht); vbl = int(m.group(1)) if m else None
    for ln in ht.splitlines():
        m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
        if m:
            a = int(m.group(1), 16)
            for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): mem[a + i] = x
    res.append((vbl, mem))
json.dump([{"vbl": v, "mem": {hex(k): x for k, x in mm.items()}} for v, mm in res], open(out, "w"))
print(plist[:60], snap, "hits", len(res), "bytes/hit", len(res[0][1]) if res else 0)
