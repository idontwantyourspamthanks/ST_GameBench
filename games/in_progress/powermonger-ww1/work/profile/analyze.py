import sys, re, json, struct
from pathlib import Path
from collections import defaultdict
sys.dont_write_bytecode = True
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger-ww1")
sys.path.insert(0, str(G/"tools"))
import addrmap
from capstone import *
RES = Path("/tmp/pmww1prof/res")
md = Cs(CS_ARCH_M68K, CS_MODE_M68K_000)
IM = addrmap.Images()

def load(game, snap, mhz):
    b = RES/f"{game}_{snap}_{mhz}"
    d = json.load(open(f"{b}.json")); rows = {}
    for l in open(f"{b}.txt"):
        x = re.match(r"^\$?([0-9a-fA-F]{8})\s+(.*?)\s+[\d.]+% \((\d+), (\d+),", l)
        if x: rows[int(x.group(1),16)] = (x.group(2).strip(), int(x.group(3)), int(x.group(4)), 0)
    return d, rows

def passes(d, copy_pc):
    recs = d["recs"]; r = [x for x in recs if x[0] == copy_pc]
    deltas = [(b[1]-a[1]) & 0xFFFFFFFF for a, b in zip(r, r[1:])]
    return r, deltas

def blocks(rows, gap=64):
    ad = sorted(rows); out = []; cur = [ad[0]]
    for a in ad[1:]:
        if a - cur[-1] <= gap: cur.append(a)
        else: out.append(cur); cur = [a]
    out.append(cur); return out

def rev(y, half=32):
    """WW1 address y -> (master address, score) via the best diagonal."""
    best = (None, -1)
    ref = IM.wb(y - half, 2*half)
    for s in IM.shifts:
        w = IM.mb(y - half - s, 2*half)
        if len(w) != len(ref): continue
        sc = sum(1 for a, b in zip(ref, w) if a == b)
        if sc > best[1]: best = (y - s, sc)
    return best

def mn(img, lo, hi, w):
    b = IM.wb(lo, hi-lo) if w else IM.mb(lo, hi-lo)
    return [i.mnemonic for i in md.disasm(b, lo)]

def cmp_block(lo, hi):
    """compare WW1 [lo,hi) with master at the mapped address: mnemonic-sequence equality."""
    m0, sc = rev(lo + 16)
    if m0 is None: return None
    ml = m0 - 16
    a = mn(IM, lo, hi, True); b = mn(IM, ml, ml + (hi - lo), False)
    n = min(len(a), len(b)); eq = sum(1 for i in range(n) if a[i] == b[i])
    return ml, sc, eq, len(a)

def table(game, snap, mhz, top=14, copy_pc=None):
    d, rows = load(game, snap, mhz)
    tot = sum(v[2] for v in rows.values())
    bl = blocks(rows)
    agg = []
    for b in bl:
        c = sum(rows[a][2] for a in b); n = rows[b[0]][1]
        agg.append((c, b[0], b[-1] + rows[b[-1]][3], n))
    agg.sort(reverse=True)
    return d, rows, tot, agg[:top]
if __name__ == "__main__":
    game, snap, mhz = sys.argv[1], sys.argv[2], int(sys.argv[3])
    d, rows, tot, agg = table(game, snap, mhz)
    print(game, snap, mhz, "profiled cycles", tot, "= %.1f VBL" % (tot/ (160256 * (mhz/8))))
    for c, lo, hi, n in agg:
        extra = ""
        if game == "ww1":
            r = cmp_block(lo, hi)
            if r: extra = f"master ${r[0]:x} windowscore {r[1]}/64 mnemonics-equal {r[2]}/{r[3]}"
        print(f"${lo:06x}-${hi:06x} {c:10d} {100*c/tot:5.1f}%  entry-count {n:6d}  {extra}")
