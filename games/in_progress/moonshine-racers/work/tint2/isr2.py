"""Timer B ISR ($d616) entry latency over a steered drive: python3 isr2.py VARIANT SNAP NVBL OUT.json
VARIANT: A stock, X final default (blit on), NB final default without tb_blit* (same tick/extras).  Steering = zig as a pure function of $100e, 8 MHz.
Late = ((LineCycles - 480 + 256) mod 512) - 256 (nominal entry ~464 = end of the line, as work/tightB/isrlat.py)."""
import sys, json, re, time
sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2")
from mxlib_fin import *
SETS["NB"] = [n for n in SETS["X"] if not n.startswith("tb_blit")]
variant, snap, nvbl, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
KS = 140
h = Moonshine(snapshot=str(SNAPDIR / snap))
try:
    time.sleep(2)
    nm = None if variant == "A" else SETS[variant]
    if nm: apply_names(h, nm, variant)
    time.sleep(1); h.debug("b all", 0.3)
    for K in range(KS, KS + 1500):
        (h.R / f"z_{K}.txt").write_text(f"w $6105 ${[1, 5, 1, 9][((K - KS) // 15) % 4]:02x}\nb pc = $7a88 && ($100e).w = ${K + 1:x} :trace :once :file {h.R}/z_{K + 1}.txt\n")
    h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = ${KS:x} :trace :once :file {h.R}/z_{KS}.txt")
    (h.R / "l_tb.txt").write_text("e LineCycles\ne VBL\ne PC\n")
    n0 = len(h._logtext()); v0 = h.vbl()
    h.cmd(f"hatari-debug b pc = $d616 :trace :file {h.R}/l_tb.txt")
    t0 = time.time()
    while h.vbl() < v0 + nvbl and time.time() - t0 < 2400: time.sleep(2)
    h.debug("b all", 0.5); lg = h._logtext()[n0:]
    bst = h.debug("m $b5800 1", 0.6).strip().splitlines()[0][:24] if nm else "-"
finally:
    h.close()
lc = [int(x) for x in re.findall(r"^\s*LineCycles\s+#?(\d+)", lg, re.M)]
if not lc:
    lc = [int(x) for x in re.findall(r"#(\d+) \(dec\)", lg)]
late = sorted((((x - 480 + 256) % 512) - 256) for x in lc)
n = len(late)
hist = {}
for b in (-64, -32, 0, 32, 64, 100, 150, 200, 256):
    hist[b] = sum(1 for x in late if x <= b)
json.dump(dict(lc=lc, late=late, bst=bst), open(out, "w"))
print(f"{variant} {snap} VBL {nvbl} entries {n} late: mean {sum(late)/max(n,1):.1f} p50 {late[n//2] if n else 0} p90 {late[int(n*.9)] if n else 0} p99 {late[int(n*.99)] if n else 0} max {late[-1] if n else 0} | >50 {sum(1 for x in late if x>50)} >100 {sum(1 for x in late if x>100)} >150 {sum(1 for x in late if x>150)} | BST {bst}", flush=True)
