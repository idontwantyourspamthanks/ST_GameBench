import sys, re; sys.path.insert(0,'.')
from tlib import *
from live import *
from tickpatch import sync_only
blobs, sites, sy = sync_only("sync2.s")
print({k:hex(v) for k,v in sy.items()})
h = open_snap("ste1m_race_start.sav", 8)
try:
    apply_live(h, blobs, sites)
    time.sleep(1)
    pcs=[0x7a88, sy["wait"], 0x17c42, 0x7b74, 0x7b86]
    log = chain(h, pcs, ["e VBL","e FrameCycles","m $b8f08 1","m $611b 1"], 8, tag="e")
finally:
    h.close()
open("dbg_e.raw","w").write(log)
rows=[]
cur=None
for ln in log.splitlines():
    m=re.match(r"\tpc = \$([0-9a-f]+) :once :trace", ln)
    if m: cur=int(m.group(1),16); vals=[]; continue
    m=re.search(r"#(\d+) \(dec\)", ln)
    if m and cur is not None: vals.append(int(m.group(1))); continue
    m=re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)", ln, re.I)
    if m and cur is not None:
        b=bytes.fromhex(m.group(2).replace(" ",""))
        rows.append((cur, vals[0], vals[1], b[0], 0))
        cur=None
best=None
for c0 in sorted({r[2] for r in rows})+[CYC]:
    t=[(r[1]+(1 if r[2]<c0 else 0))*CYC+r[2] for r in rows]
    bad=sum(1 for i in range(1,len(t)) if t[i]<t[i-1])
    if best is None or bad<best[0]: best=(bad,c0)
bad,c0=best
t0=None
print("viol",bad,"c0",c0)
for r in rows:
    t=(r[1]+(1 if r[2]<c0 else 0))*CYC+r[2]
    if t0 is None: t0=t
    print(f"{r[0]:05x} t={(t-t0)/CYC:7.3f} pend={r[3]} 611b={r[4]}")
