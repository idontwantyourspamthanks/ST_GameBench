"""Emulator gate: reference build (X = mx_sync) vs candidate build (M = mf_sync) in lockstep.
 per pass: every flip's finished buffer (main + extras, 32000 B) must be equal, and the whole RAM outside the payload area $B2700-$BFFFF after the group (at $7b7a) must be equal.
 python3 cmpmx.py DUMP KIND NPASS NTEST [REF CAND] [neg=...]"""
import sys, collections
from unicorn import UC_HOOK_CODE
from mflib import *
dump, kind, npass, ntest = DUMPS.get(sys.argv[1], sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
ref = sys.argv[5] if len(sys.argv) > 5 and '=' not in sys.argv[5] else 'X'; cand = sys.argv[6] if len(sys.argv) > 6 and '=' not in sys.argv[6] else 'M'
pokes = [a for a in sys.argv[5:] if '=' in a and not a.startswith('neg=')]
negs = [a[4:] for a in sys.argv[5:] if a.startswith('neg=')]
def mk(v, tag):
    pre = live_build(v, tag)
    e = Emu(dump); apply_live(e, pre); e.setb(0xB8F21, ntest)
    e.flips = []
    def hk(uc, addr, size, ud): e.flips.append(bytes(uc.mem_read(e.l(0x1008), 0x7d00)))
    e.uc.hook_add(UC_HOOK_CODE, hk, begin=0xd1ca, end=0xd1ca)
    return e
A = mk(ref, 'cmp_ref'); B = mk(cand, 'cmp_cand')
for p in pokes:
    a, v = p.split('=')
    if a.startswith('b'): A.write(int(a[1:], 16), bytes.fromhex(v))   # bADDR=HEX: both builds
    B.write(int(a[1:] if a.startswith('b') else a, 16), bytes.fromhex(v))
LM = dict((l, a) for a, l in labelmap(GAME + ('/patches/mg_sync.s' if cand == 'G' else '/patches/mf_sync.s')))
def find(lab, pat, nth=0, span=0x800, back=0):
    base = LM[lab] - back; m = B.read(base, span); i = -1
    for _ in range(nth + 1): i = m.index(bytes.fromhex(pat), i + 1)
    return base + i
for n in negs:
    if n == 'restore_slots': a = find('restoreundo.sl', '7e0d', back=4); B.write(a, bytes.fromhex('7e0c'))
    elif n == 'prerestore_short': a = find('prerestore', '7e0d'); B.write(a, bytes.fromhex('7e0c'))
    elif n == 'ring_window': a = find('restoreundo.rs', 'e449'); B.write(a, bytes.fromhex('e649'))
    elif n == 'kernel_one': a = find('restoreundo', '23c1' if False else '2298' if False else '2358', 0, 0x600) if False else None
    elif n == 'static_1308': a = find('restoreundo', '21c21308'); B.write(a, bytes.fromhex('4e714e71'))
    elif n == 'kernel_long':
        a = find('restoreundo', '23d80000dafe', 0, 0x800)   # move.l (a0)+,$dafe.l : the HUD face generator immediate
        B.write(a, bytes.fromhex('58884e714e71'))
    elif n == 'kernel_12b6a':
        a = find('restoreundo', '23580a66' if False else '2358', 3, 0x800)
        B.write(a, bytes.fromhex('58884e71'))
    elif n == 'save_slots_short': a = find('saveundo.sl', '7e0d', back=4); B.write(a, bytes.fromhex('7e0c'))
    elif n == 'g_restore_fields': a = find('restoreundo.sl', '48d1001f'); B.write(a, bytes.fromhex('4e714e71'))
    elif n == 'g_reset_fields': a = find('slotreset', '48d1001f'); B.write(a, bytes.fromhex('4e714e71'))
    elif n == 'g_scan_short': a = find('saveundo', '7a2f' if False else '7e2f', 0, 0x400); B.write(a, bytes.fromhex('7e14'))
    elif n == 'g_no_reset': a = find('slotreset', '4a79'); B.write(a, bytes.fromhex('4e754e71' if False else '4e75'))
    else: raise SystemExit('unknown neg ' + n)
    print('neg', n, 'applied at', hex(a))
nmain = 0; post_rel = []; entry_diff = []; nfl = 0; nbad = 0; nout = 0; nout_rel = 0; nrel = 0; sbad = collections.Counter(); worst = 0; nstate = 0; badp = []
for p in range(npass):
    v = schedule(p, kind)
    for e in (A, B):
        if v is not None: e.setb(0x6105, v)
        e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1))
        e.flips = []
    if cand == 'G':   # the post stages run after the extras in G and before them in X: record what they changed that the extras can see
        for e in (A, B): e.run(0x7a88, 0xb8400)
        xa, xb = A.read(0x1000, 0xb1700), B.read(0x1000, 0xb1700)
        dd = [0x1000 + i for i in range(len(xa)) if xa[i] != xb[i] and not (0x70000 <= 0x1000 + i < 0x80000) and not (0x7b00 <= 0x1000 + i < 0x7c00)]
        gl = [a for a in dd if (0x1300 <= a < 0x1340) or (0x130c <= a < 0x130e) or (0x2ca0 <= a < 0x2d80 and (a - 0x2c68) % 56 in (0, 1, 2, 3, 0x20, 0x21))]
        post_rel.append(bool(gl)); entry_diff.append(len(dd))
    for e in (A, B):
        e.run(0x7a88 if cand != 'G' else 0xb8400, 0x7b7a)
    if len(A.flips) != len(B.flips): print('pass', p, 'flip count', len(A.flips), len(B.flips)); nbad += 1
    for i, (x, y) in enumerate(zip(A.flips, B.flips)):
        nfl += 1
        if x != y:
            if i == 0: nmain += 1
            d = sum(1 for k in range(0x7d00) if x[k] != y[k]); nbad += 1; worst = max(worst, d)
            rows = sorted(set(k // 160 for k in range(0x7d00) if x[k] != y[k]))
            if rows[-1] >= 16:
                nout += 1
                if cand == 'G' and not post_rel[p] and not (p > 0 and post_rel[p - 1]): nout_rel += 1
            if len(badp) < 8: badp.append((p, i, d, f'rows {rows[0]}-{rows[-1]}'))
    ra, rb = bytearray(A.read(0, 0xb2700)), bytearray(B.read(0, 0xb2700))
    ra[0x77d00:0x78000] = bytes(0x300); rb[0x77d00:0x78000] = bytes(0x300)   # dead stack residue below the stack top
    ra2, rb2 = A.read(0xc0000, 0x40000), B.read(0xc0000, 0x40000)
    if ra != rb or ra2 != rb2:
        nstate += 1
        for a in range(0xb2700):
            if ra[a] != rb[a]: sbad[a] += 1
        for a in range(0x40000):
            if ra2[a] != rb2[a]: sbad[0xc0000 + a] += 1
    A.run(0x7b7a, 0x7a88); B.run(0x7b7a, 0x7a88)
if cand == 'G': print(f'  G only: passes where the post stages changed pose-relevant globals ($1300-$133f, $130c, car/player x,y,distance): {sum(post_rel)} of {npass}; differing frames BELOW the HUD strip in passes where they did not (and not the pass after one that did, which inherits the lateral history): {nout_rel}')
print(f'{ref} vs {cand}  {sys.argv[1]} {kind} passes {npass} ntest {ntest}: flips compared {nfl}, differing frames {nbad} (worst {worst} B; of which with differences below the HUD strip, rows >= 16: {nout}) {badp}; passes with state diff {nstate}, differing addresses {len(sbad)}')
if sbad:
    ad = sorted(sbad); runs = []
    for a in ad:
        if runs and a - runs[-1][1] <= 1: runs[-1][1] = a
        else: runs.append([a, a])
    print('  runs:', ' '.join(f'{s:x}-{t:x}' for s, t in runs[:20]))
nonscr = [a for a in sbad if not (0x70000 <= a < 0x80000) and not (0x7b49 <= a < 0x7b4c or 0x7b52 <= a < 0x7b58 or a == 0x7b79)]
if nonscr:
    r_ = []
    for a in sorted(nonscr):
        if r_ and a - r_[-1][1] <= 1: r_[-1][1] = a
        else: r_.append([a, a])
    print('  non-screen differing runs:', ' '.join(f'{x:x}-{y:x}' for x, y in r_[:30]))
print(f'  main frames (flip 0 of each pass) differing: {nmain}; state addresses differing outside the screen buffers and the patch sites: {len(nonscr)}')
print(f'  extras: ref frames {A.l(0xB8F38)} groups {A.l(0xB8F3C)} ; cand frames {B.l(0xB8F38)} groups {B.l(0xB8F3C)}')
