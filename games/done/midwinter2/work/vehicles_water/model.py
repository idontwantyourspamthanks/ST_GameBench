"""Offline model of the 5-sub-step split vs the original single step, checked on the control (unpatched) rows of a run.
For every consecutive tick pair (k -> k+1) of the logged unpatched game:
  ORIG : the game's own formulas (disassembly: $345c4 heading, $344ac/$344f8 position, $3461a bank, $34586 depth) reproduce row k+1 from row k;
  SPLIT: five sub-steps with the exact integer arithmetic of the p3b blobs (bres/fdiv5 Bresenham, Q16 position accumulators with the
         group-end heading HF, Bresenham depth) land on the same row k+1.
usage: model.py <pickle tag> ...    (logs/<tag>.pkl from cmp.py)"""
import pickle, sys
from vw import *
RAM = open(ROOT / 'work/dumps/ram_ingame_lobos.bin', 'rb').read()
def sin_tab(h):  # word at $44a4 + (h & $3fe)
    return int.from_bytes(RAM[0x44a4 + (h & 0x3fe):0x44a4 + (h & 0x3fe) + 2], 'big', signed=True)
def cos_tab(h):
    return sin_tab((h & 0x3fe) + 0x100)
def fdiv5(d):                       # p3b_head fdiv5: ((d+3000)*52429 >> 18) - 600, word domain -3000..62000
    assert -3000 <= d <= 62000, d
    return (((d + 3000) & 0xffff) * 52429 >> 18) - 600
def bres(e2, rem):                  # p3b_head bres: returns (2q, rem')
    d1 = rem + e2; q = fdiv5(d1); return 2 * q, d1 - 5 * q
def s16(x): x &= 0xffff; return x - 0x10000 if x & 0x8000 else x
def sext10(x): x &= 0x3fe; return x - 0x400 if x & 0x200 else x
def orig_tick(a, b):
    """ORIG formulas: returns predicted (H, X, Y, lean) from row a and the control inputs sampled in row b."""
    f984 = b.sw(0xf984); dh = b.sw(0x6752) >> 4; x = s16(f984 + dh)
    H = (a.w(0x6742) + x) & 0x3fe
    v = b.sw(0x6772)
    X = a.l(0x66e6) + ((sin_tab(H) * v) >> 16)
    Y = a.l(0x66ea) + ((cos_tab(H) * v) >> 16)
    lean = sext10(x)               # $674e is cleared each pass then += x
    return H, X, Y, lean, x
def split_tick(a, b):
    f984 = b.sw(0xf984); dh = b.sw(0x6752) >> 4; x = s16(f984 + dh)
    e = x & ~1; e2 = e >> 1
    H0 = a.w(0x6742); HF = (H0 + e) & 0x3fe
    v = b.sw(0x6772)
    sacc = 0; H = H0; accx = 0; accy = 0; X = a.l(0x66e6); Y = a.l(0x66ea)
    PX = sin_tab(HF) * v; PY = cos_tab(HF) * v
    for j in range(5):
        d, sacc = bres(e2, sacc); H = (H + d) & 0x3fe
        for P, which in ((PX, 'x'), (PY, 'y')):
            S = (accx if which == 'x' else accy) + P
            q = fdiv5(S >> 16) if False else fdiv5(S >> 16)        # floor(ACC/65536) then /5 (p3b_pos .axis)
            q = fdiv5((S >> 16))
            S -= q * 5 * 65536
            if which == 'x': accx = S; X += q
            else: accy = S; Y += q
    return H, X, Y
def depth_orig(a, b, lo=-0x1f40, hi=0x2ee0):
    return max(lo, min(hi, a.sw(0x764c) + (b.sw(0x675a) >> 4)))
def depth_split(a, b, lo=-0x1f40, hi=0x2ee0):
    e = b.sw(0x675a) >> 4; acc = 0; z = a.sw(0x764c)
    for j in range(5):
        S = acc + e; q = fdiv5(S); acc = S - 5 * q; z = max(lo, min(hi, z + q))
    return z
def bank_orig(a, b, clamp):
    e = b.sw(0x675a) >> 4; v = sext10(a.sw(0x6746) + e)
    return max(-192, min(192, v)) if clamp else v
def bank_split(a, b, clamp):
    e = (b.sw(0x675a) >> 4) & ~1; e2 = e >> 1; rem = 0; z = a.sw(0x6746)
    for j in range(5):
        d, rem = bres(e2, rem); z = sext10(z + d)
        if clamp: z = max(-192, min(192, z))
    return z
def air_orig(a, b):
    thr = b.sw(0x6750); P0 = thr * a.sw(0x7652); sp = ((thr * a.sw(0x7654)) << 2) >> 16
    z = max(-0x1f40, min(0x2ee0, a.sw(0x764c) + (P0 >> 17)))
    return z, sp
def air_split(a, b):                  # sw_alt: P0 and speed frozen at the group start (a.$7652/$7654), Q16/5 accumulator
    thr = b.sw(0x6750); P0 = thr * a.sw(0x7652); sp = ((thr * a.sw(0x7654)) << 2) >> 16
    acc = 0; z = a.sw(0x764c)
    for j in range(5):
        S = acc + P0; q = fdiv5(S >> 16) >> 1 if False else (fdiv5(S >> 16) >> 1)
        acc = S - q * 655360; z = max(-0x1f40, min(0x2ee0, z + q))
    return z, sp
def air_split_unfrozen(a, b):         # p3b_alt as shipped: every sub-pass reads the $7652 written by the previous sub-pass ($3467c)
    thr = b.sw(0x6750); e = (b.sw(0x675a) >> 4) & ~1; e2 = e >> 1; rem = 0; bank = a.sw(0x6746)
    s52 = a.sw(0x7652); acc = 0; z = a.sw(0x764c)
    for j in range(5):
        P0 = thr * s52; S = acc + P0; q = fdiv5(S >> 16) >> 1; acc = S - q * 655360; z = max(-0x1f40, min(0x2ee0, z + q))
        d, rem = bres(e2, rem); bank = sext10(bank + d); s52 = sin_tab(bank)     # $3467c at the end of the pass
    return z
def main(tags):
    for tag in tags:
        ctl, pat = pickle.load(open(OUT / 'logs' / (tag + '.pkl'), 'rb'))
        n = ok_o = ok_s = tot = 0; bad = []
        for k in range(1, len(ctl) - 1):
            a, b = ctl[k], ctl[k + 1]
            if a.w(0x6220) != b.w(0x6220) or b.w(0x676e): continue          # type change / probe event: not an integrator step
            H, X, Y, lean, x = orig_tick(a, b)
            Hs, Xs, Ys = split_tick(a, b)
            tot += 1
            o = (H, X, Y) == (b.w(0x6742), b.l(0x66e6), b.l(0x66ea))
            s = (Hs, Xs, Ys) == (b.w(0x6742), b.l(0x66e6), b.l(0x66ea))
            ok_o += o; ok_s += s
            if not (o and s): bad.append((k, (H, X, Y), (Hs, Xs, Ys), (b.w(0x6742), b.l(0x66e6), b.l(0x66ea))))
        if ctl[1].w(0x6220) == 9:
            dk = [(depth_orig(ctl[k], ctl[k + 1]) == ctl[k + 1].sw(0x764c), depth_split(ctl[k], ctl[k + 1]) == ctl[k + 1].sw(0x764c)) for k in range(1, len(ctl) - 1)]
            print(f'   depth ($34586 $764c += $6740>>... clamp): ORIG {sum(o for o, s in dk)}/{len(dk)} SPLIT {sum(s for o, s in dk)}/{len(dk)}')
        T = ctl[1].w(0x6220)
        if T in (8, 11, 21):
            cl = T == 21
            bk = [(bank_orig(ctl[k], ctl[k + 1], cl) == ctl[k + 1].sw(0x6746), bank_split(ctl[k], ctl[k + 1], cl) == ctl[k + 1].sw(0x6746)) for k in range(1, len(ctl) - 1) if ctl[k].w(0x6220) == ctl[k + 1].w(0x6220) == T]
            print(f'   bank ($3461a, clamp {cl}): ORIG {sum(o for o, s in bk)}/{len(bk)} SPLIT {sum(s for o, s in bk)}/{len(bk)}')
        if T in (8, 11):
            ak = [(air_orig(ctl[k], ctl[k + 1]) == (ctl[k + 1].sw(0x764c), ctl[k + 1].sw(0x6772)), air_split(ctl[k], ctl[k + 1]) == (ctl[k + 1].sw(0x764c), ctl[k + 1].sw(0x6772))) for k in range(1, len(ctl) - 1)]
            uk = [air_split_unfrozen(ctl[k], ctl[k + 1]) == ctl[k + 1].sw(0x764c) for k in range(1, len(ctl) - 1)]
            print(f'   alt with the shipped p3b_alt (unfrozen $7652): {sum(uk)}/{len(uk)} ticks equal')
            print(f'   alt/speed ($33f40 bit6): ORIG {sum(o for o, s in ak)}/{len(ak)} SPLIT {sum(s for o, s in ak)}/{len(ak)}')
        print(f'{tag}: type {ctl[1].w(0x6220)}  ticks {tot}  ORIG-formula==game {ok_o}/{tot}  SPLIT==game {ok_s}/{tot}', bad[:2])
main(sys.argv[1:])
