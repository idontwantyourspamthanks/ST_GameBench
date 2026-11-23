import sys; sys.path.insert(0,'.')
from analyze import *
COPY = {"pm": 0x12ce0, "ww1": 0x13a94}
# named routine ranges: (name, pm lo, pm hi, ww1 lo, ww1 hi) from the address map / blocks
R = [("terrain span fill (head+loop)", 0xe3e6,0xe4da, 0xe7c6,0xe8be),
     ("terrain span fill tail", 0xe52a,0xe5aa, 0xe90a,0xe98a),
     ("triangle setup", 0xef62,0xf240, 0xf342,0xf5c2),
     ("terrain cell loop", 0xf898,0xfe00, 0xfc78,0x10200),
     ("sprite blit 32px", 0x12326,0x126d6, 0x130ff-0xd9+0x0,0x13560),   # refined below
     ("object project/small sprites", 0x11500,0x12326, 0x12290,0x130ff),
     ("window copy", 0x12ce0,0x12d06, 0x13a94,0x13abc),
     ("pointer (VBL)", 0x1378,0x14e4, 0x866,0x9da),
     ("sample IRQ", 0x1af32,0x1af84, 0x1bc92,0x1bce6),
     ("VBL wait", 0x1858,0x1960, 0xe04,0xef6)]
def run(g, s, mhz):
    d, rows = load(g, s, mhz)
    tot = sum(v[2] for v in rows.values()); npass = rows[COPY[g]][1]
    print(f"== {g} {s} {mhz}MHz  profiled {tot} cycles, {npass} rendered passes (window copy entries), {tot/npass:.0f} cycles/pass")
    return d, rows, tot, npass
if __name__ == "__main__":
    for mhz in (8,16):
      for g, snaps in (("ww1", ["map_idle","get_men"]), ("pm", ["map_idle","get_men","battle_320"])):
        for s in snaps:
            d, rows, tot, npass = run(g, s, mhz)
            bl = blocks(rows); agg=[]
            for b in bl:
                c = sum(rows[a][2] for a in b); agg.append((c, b[0], b[-1]+4, rows[b[0]][1]))
            agg.sort(reverse=True)
            for c, lo, hi, n in agg[:10]:
                print(f"  ${lo:06x}-${hi:06x} {100*c/tot:5.1f}% {c/npass:9.0f} cyc/pass {n/npass:7.1f} entries/pass")
