"""Enumerate every cloud-edge residue pixel (exact): python3 residue.py LEVEL... [--inputs up zig] [--passes 120]
Emulator (Unicorn, exact 68000) on a race-loop dump of one level: stock vs mx (X_TEST=3 extras, the real extras code, no timing).
For every flip (main frame and every extra frame) the DRAWN buffer is read at $d1ca; a main frame is compared with the stock main
frame of the same pass, an extra frame with the stock image of that same buffer as of the last stock main frame that wrote it.
Differences are written to work/extrap/residue/residue.tsv (level, input, flip index, kind, pass, buffer, row, x, stock colour, mx colour)."""
import sys, os, json
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap')
os.chdir('/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap')
from gate3 import *
from unicorn import *
from unicorn.m68k_const import *
import struct
DUMP = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/int/mx/dumps/L{}.bin'
OUT = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap/residue/residue.tsv'
def idx(buf, row, x):
    o = row * 160 + (x // 16) * 8; w = [struct.unpack('>H', buf[o + 2 * p:o + 2 * p + 2])[0] for p in range(4)]
    b = x % 16
    return sum(((w[p] >> (15 - b)) & 1) << p for p in range(4))
def pixdiff(a, b):
    out = []
    for i in range(0x7d00):
        if a[i] != b[i]:
            row, x = i // 160, (i % 160) // 8 * 8 // 8 * 0 + ((i % 160) // 8) * 8   # byte -> first x of the 8-px group
            out.append((row, x, idx(a, row, x), idx(b, row, x)))
    return out
def run(dump, npass, kind, patched):
    e = Emu(dump); flips = []
    st = {"pass": None, "n": 0}
    if patched:
        apply_live(e); e.setb(0xB8F21, 3)
    def at_newsync(uc, addr, size, ud): st["pass"] = e.w(0x100e); st["n"] = 0
    def at_flip(uc, addr, size, ud):
        b = struct.unpack('>I', bytes(uc.mem_read(0x1008, 4)))[0]
        flips.append(dict(pass_=e.w(0x100e), kind=("main" if not patched or st["n"] == 0 else "extra"), buf=b,
                          img=bytes(uc.mem_read(b, 0x7d00)), sub=st["n"]))
        st["n"] += 1
    e.uc.hook_add(UC_HOOK_CODE, at_flip, begin=0xd1ca, end=0xd1ca)
    if patched: e.uc.hook_add(UC_HOOK_CODE, at_newsync, begin=0xb8100, end=0xb8100)
    for p in range(npass):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        if patched:
            e.setb(0xB8F08, 0); e.setl(0xB8F00, 36 * (p + 1)); e.run(0x7a88, 0xb8100); e.run(0xb8100, 0x7b7a)
        else:
            e.run(0x7a88, 0x7b74); flip(e)
        e.run(0x7b7a, 0x7a88)
    return flips
rows = []
argv = sys.argv[1:]
levels = [int(a) for a in (argv[:argv.index("--passes")] if "--passes" in argv else argv) if a.isdigit()]
inputs = [a for a in sys.argv[1:] if a in ("up", "zig")] or ["up", "zig"]
np_ = int(sys.argv[sys.argv.index("--passes") + 1]) if "--passes" in sys.argv else 120
for L in levels:
    for kind in inputs:
        A = run(DUMP.format(L), np_, kind, False); X = run(DUMP.format(L), np_, kind, True)
        stock_main = {f["pass_"]: f for f in A}
        last_stock = {}
        for f in A: last_stock[f["buf"]] = f["img"]
        # stock per-buffer image as of the *end* of each pass (needed to compare extras in order): rebuild from A sequence
        seq = []
        for f in A: seq.append(f)
        # walk stock order, tracking the image each buffer had after its last main frame
        st_last = {}
        stock_state_after_pass = {}
        for f in A: st_last[f["buf"]] = f["img"]
        # for extras: reference = stock buffer image after the last stock main frame *before or at* the same buffer's turn
        # (the extras draw into the buffer the main frame will not draw next; stock's last writer of that buffer is the previous main frame)
        nmain = ne = 0; cases = {}
        for f in X:
            key = (L, kind, f["kind"])
            if f["kind"] == "main":
                r = stock_main.get(f["pass_"])
                if r is None: continue
                d = pixdiff(f["img"], r["img"])
                nmain += 1
            else:
                # stock image of this buffer = the stock main frame that wrote that buffer most recently before this pass
                cand = [g for g in A if g["buf"] == f["buf"] and g["pass_"] <= f["pass_"]]
                if not cand: continue
                r = cand[-1]; d = pixdiff(f["img"], r["img"]); ne += 1
            for row, x, sa, sb in d:
                rows.append((L, kind, f["pass_"], f["kind"], f["sub"], hex(f["buf"]), row, x, sa, sb))
                cases[key] = cases.get(key, 0) + 1
        print(L, kind, "main flips", nmain, "extra flips", ne, "diff bytes by kind", cases, flush=True)
with open(OUT, "w") as fh:
    fh.write("level\tinput\tpass\tkind\tsub\tbuffer\trow\tx\tstock_colour\tmx_colour\n")
    for r in rows: fh.write("\t".join(map(str, r)) + "\n")
print("wrote", OUT, len(rows), "rows")
