"""Exact residue enumeration (v2): python3 residue2.py LEVEL... --passes N
Phase 1 (main frames): every differing pixel between a main frame and the stock frame of the same pass -> the residue set.
Phase 2 (extra frames): at those coordinates, is the pixel *also* wrong in the extra frames (i.e. can extras show the residue)?
Outputs work/extrap/residue/{residue.tsv, extras.tsv, summary.txt}."""
import sys, os, json, struct
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap')
os.chdir('/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap')
from gate3 import *
from unicorn import *
from unicorn.m68k_const import *
D = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/int/mx/dumps/L{}.bin'
R = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap/residue/'
def idx(buf, row, x):
    o = row * 160 + (x // 16) * 8; w = [struct.unpack('>H', buf[o + 2 * p:o + 2 * p + 2])[0] for p in range(4)]
    return sum(((w[p] >> (15 - x % 16)) & 1) << p for p in range(4))
def run(dump, npass, kind, patched):
    e = Emu(dump); fl = []; st = {"n": 0}
    if patched: apply_live(e); e.setb(0xB8F21, 3)
    e.uc.hook_add(UC_HOOK_CODE, lambda uc, a, s, u: st.__setitem__("n", 0), begin=0xb8100, end=0xb8100) if patched else None
    def at_flip(uc, a, s, u):
        b = struct.unpack('>I', bytes(uc.mem_read(0x1008, 4)))[0]
        fl.append(dict(pass_=e.w(0x100e), kind=("main" if (not patched or st["n"] == 0) else "extra"), buf=b,
                       img=bytes(uc.mem_read(b, 0x7d00)), sub=st["n"]))
        st["n"] += 1
    e.uc.hook_add(UC_HOOK_CODE, at_flip, begin=0xd1ca, end=0xd1ca)
    for p in range(npass):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        if patched:
            e.setb(0xB8F08, 0); e.setl(0xB8F00, 36 * (p + 1)); e.run(0x7a88, 0xb8100); e.run(0xb8100, 0x7b7a)
        else:
            e.run(0x7a88, 0x7b74); flip(e)
        e.run(0x7b7a, 0x7a88)
    return fl
argv = sys.argv[1:]
levels = [int(a) for a in (argv[:argv.index("--passes")] if "--passes" in argv else argv) if a.isdigit()]
np_ = int(argv[argv.index("--passes") + 1]) if "--passes" in argv else 120
inputs = [a for a in argv if a in ("up", "zig")] or ["up", "zig"]
t1 = open(R + "residue.tsv", "w"); t1.write("level\tinput\tpass\tkind\tsub\tbuffer\trow\tx\tstock_colour\tmx_colour\tbytes_in_group\n")
t2 = open(R + "extras.tsv", "w"); t2.write("level\tinput\tpass\tsub\tbuffer\trow\tx\tstock_ref_colour\textra_colour\n")
summ = []
for L in levels:
    for kind in inputs:
        A = run(D.format(L), np_, kind, False); X = run(D.format(L), np_, kind, True)
        sm = {f["pass_"]: f for f in A}
        res = {}     # (row,x) -> (stock, mx) from main frames
        nres = 0
        for f in X:
            if f["kind"] != "main": continue
            r = sm.get(f["pass_"])
            if not r: continue
            for i in range(0x7d00):
                if f["img"][i] != r["img"][i]:
                    pass
            for row in range(200):
                base = row * 160
                if f["img"][base:base + 160] == r["img"][base:base + 160]: continue
                for x in range(320):
                    sa, sb = idx(f["img"], row, x), idx(r["img"], row, x)
                    if sa == sb: continue
                    res[(row, x)] = (sa, sb); nres += 1
                    t1.write(f"{L}\t{kind}\t{f['pass_']}\tmain\t{f['sub']}\t{hex(f['buf'])}\t{row}\t{x}\t{sb}\t{sa}\t1\n")
        seen_extra = 0; frames_extra = 0
        for f in X:
            if f["kind"] != "extra": continue
            cand = [g for g in A if g["buf"] == f["buf"] and g["pass_"] <= f["pass_"]]
            if not cand: continue
            ref = cand[-1]; frames_extra += 1; hit = False
            for (row, x), (smx, sstock) in res.items():
                v = idx(f["img"], row, x)
                if v != sstock:
                    t2.write(f"{L}\t{kind}\t{f['pass_']}\t{f['sub']}\t{hex(f['buf'])}\t{row}\t{x}\t{sstock}\t{v}\n"); hit = True
            seen_extra += hit
        summ.append((L, kind, nres, frames_extra, seen_extra))
        print(L, kind, "residue pixels", nres, "extra frames", frames_extra, "extra frames showing a residue pixel", seen_extra, flush=True)
t1.close(); t2.close()
with open(R + "summary.txt", "w") as fh:
    fh.write("level input residue_pixels(all main frames) extra_frames extra_frames_showing_a_residue_pixel\n")
    for s in summ: fh.write("%s %s %d %d %d\n" % s)
