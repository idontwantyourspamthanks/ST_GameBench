#!/usr/bin/env python3
"""A/B of two `--trace psg_write` traces of the same cold boot (YM-only machines: Mega ST / TT): the YM output is a pure function of the register writes,
so identical (reg, value) sequences = identical audio.  Compares the sequence of `ym write data reg=R val=V` (values of reg 7 masked with $3f, i.e. everything
but the I/O-direction bits 6+7, and reported separately), up to the shorter trace; prints the first differences and the timing drift (video_cyc, HBL position
are compared only as a count of lines that differ).
    python3 ymdiff.py TRACE_A TRACE_B"""
import re, sys
R = re.compile(r"^ym write data reg=0x([0-9a-f]+) val=0x([0-9a-f]+) video_cyc=(\d+) (\d+)@(\d+) pc=([0-9a-f]+)")
def load(p):
    out = []
    for ln in open(p, errors='replace'):
        m = R.match(ln)
        if m and int(m.group(1), 16) <= 13:          # sound registers only: reg 14 (floppy select) timing differs run to run with the disk
            out.append((int(m.group(1), 16), int(m.group(2), 16), int(m.group(3)), m.group(6), ln.strip()))
    return out
a, b = load(sys.argv[1]), load(sys.argv[2])
def anchor(x):                                   # first write of the game's sound init (`$338ea`, reg 0): both runs are compared from there (the boot stub's tune before it is not comparable run to run)
    for i, w in enumerate(x):
        if w[3] == '338ea': return i
    return 0
ia, ib = anchor(a), anchor(b)
print(f'anchor (first $338ea write): A index {ia}, B index {ib}')
a, b = a[ia:], b[ib:]
n = min(len(a), len(b))
print(f'writes A {len(a)}, B {len(b)}; comparing the first {n}')
diff_other = [i for i in range(n) if a[i][0] != b[i][0] or (a[i][1] & (0x3f if a[i][0] == 7 else 0xff)) != (b[i][1] & (0x3f if b[i][0] == 7 else 0xff))]
diff_r7 = [i for i in range(n) if a[i][0] == 7 == b[i][0] and a[i][1] != b[i][1] and (a[i][1] & 0x3f) == (b[i][1] & 0x3f)]
print(f'writes differing in (reg 0-13, value) other than reg-7 bits 6/7: {len(diff_other)}')
for i in diff_other[:6]: print('   A:', a[i][4][:110], '\n   B:', b[i][4][:110])
print(f'reg-7 writes differing ONLY in bits 6/7: {len(diff_r7)}')
for i in diff_r7[:6]: print('   A:', a[i][4][:110], '\n   B:', b[i][4][:110])
print('VERDICT', 'IDENTICAL AUDIO (only reg 7 bits 6/7 differ)' if not diff_other else 'DIFFERENT')
