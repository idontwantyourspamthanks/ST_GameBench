"""Python model of the air-vehicle player step (flags bit0 path) and of the p3b 1/5 split, checked against the logged
original game (out/heliB.pkl = unpatched control + shipped p3b, out/heliB2.pkl = frozen-coefficient fix).
Original tick k (types 12,13,14,18,20; $33bde order): thr level; $344ac/$33f40 uses the coefficients left by tick k-1:
    alt += floor(thr*sinq/131072)  (clamp)      spd = (thr*cosq*4)>>16
    bank_k = sext10(bank_{k-1} + b)             sinq,cosq = table[bank_k]   (for tick k+1)
"""
import pickle, struct, sys
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehair')
import cmp
ram = open('/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/dumps/ram_ingame_lobos.bin', 'rb').read()
def sw(a): return struct.unpack('>h', ram[a:a+2])[0]
def sin_(b): return sw(0x44a4 + (b & 0x3fe))
def cos_(b): return sw(0x45a4 + (b & 0x3fe))
def sext10(v): v &= 0x3fe; return v - 1024 if v & 0x200 else v   # lsl.w #6 ; asr.w #6 on the 10-bit field
def f5(x): return x // 5
def orig_step(alt, bank, thr, b, sinq, cosq):
    alt2 = alt + ((thr * sinq) >> 17)                      # swap + asr.w #1 : floor(P/131072)
    spd = ((thr * cosq * 4) >> 16)
    bank2 = sext10(bank + b)
    return alt2, spd, bank2, sin_(bank2), cos_(bank2)
def split_step(alt, bank, thr, b, sinq, cosq, frozen=True):
    """5 passes; Bresenham on bank in units of 2 (as p3b_bank), alt via Q16 accumulator on P0 (as p3b_alt)."""
    acc = 0; rem = 0; e2 = (b & ~1) // 2
    sq, cq = sinq, cosq
    spds = []
    for j in range(5):
        s, c = (sinq, cosq) if frozen else (sq, cq)         # frozen: group-start coefficients
        acc += thr * s
        q = acc // 655360; acc -= q * 655360; alt += q
        spds.append((thr * c * 4) >> 16)
        S = rem + e2; qq = S // 5; rem = S - 5 * qq; bank = sext10(bank + 2 * qq)
        sq, cq = sin_(bank), cos_(bank)                       # $3467c every pass
    return alt, spds[-1], bank, sq, cq
if __name__ == '__main__':
    tag = sys.argv[1] if len(sys.argv) > 1 else 'heliB'
    A, B = pickle.load(open(cmp.vh.OUT / f'{tag}.pkl', 'rb'))
    Ar = [cmp.row(m) for m in A]
    # model start = control row 0; b = button step 16 (left button: $10*$10>>4)
    thr = Ar[1]['thr']; b = 16
    alt, bank = Ar[0]['alt'], Ar[0]['bank']; sinq, cosq = Ar[0]['c52'], Ar[0]['c54']
    print('k  observed(alt,spd,bank)  model-orig  | model split frozen | model split LIVE coefficients (shipped p3b)')
    a1 = (alt, bank, sinq, cosq); a2 = (alt, bank, sinq, cosq); a3 = (alt, bank, sinq, cosq)
    bad = [0, 0, 0]
    for k in range(1, 23):
        o = orig_step(a1[0], a1[1], thr, b, a1[2], a1[3]); a1 = (o[0], o[2], o[3], o[4])
        f = split_step(*a2[:2], thr, b, a2[2], a2[3], True); a2 = (f[0], f[2], f[3], f[4])
        l = split_step(*a3[:2], thr, b, a3[2], a3[3], False); a3 = (l[0], l[2], l[3], l[4])
        obs = (Ar[k]['alt'], Ar[k]['spd'], Ar[k]['bank'])
        mo = (o[0], o[1], o[2]); mf = (f[0], f[1], f[2]); ml = (l[0], l[1], l[2])
        bad[0] += mo != obs; bad[1] += mf != obs; bad[2] += mf != mo
        if k <= 8 or k % 7 == 0: print(k, obs, mo, '|', mf, '|', ml)
    print('mismatches: model-orig vs observed control', bad[0], '; split-frozen vs observed', bad[1], '; split-frozen vs model-orig', bad[2])
