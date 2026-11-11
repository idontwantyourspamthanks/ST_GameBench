"""tickreal.py SNAP MHZ: are the 1-VBL-gap hits of $31586 real ticks? Per hit: VBL, tick_vbl clock, X/Y ($66e6/$66ea), $6742 heading; counts hits whose pose did not change."""
import sys, re, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b')
from vt import *
import runtype
snap, mhz = sys.argv[1], int(sys.argv[2])
live = build_live(cand_names(), 'tickreal')
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=2048)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    v = h.vbl(); ty = h.peekw(0x6220)
    pk = ['w $%x ' % int(p.split('=')[0], 16) + ' '.join('$%02x' % b for b in bytes.fromhex(p.split('=')[1])) for p in runtype.pokes(ty, 'movturn')]
    at_flip(h, apply_cmds(live) + pk, v + 100)
    time.sleep(3)
    f = h.R / 'g.txt'; f.write_text('e VBL\nm $b3400 4\nm $66e6 8\nm $6742 2\n')
    h.debug('b all', 0.3); s = len(h._logtext()); v0 = h.vbl()
    h.cmd(f'hatari-debug b pc = $31586 :trace :file {f}'); time.sleep(0.2)
    h.cmd(f'hatari-debug b VBL > {v0 + 800} :trace :once'); time.sleep(0.2)
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[s:] and time.time() - t < 300: time.sleep(0.5)
    out = h._logtext()[s:]; h.debug('b all', 0.3)
    rows = re.findall(r'#(\d+) \(dec\)[^\n]*\n> m \$b3400 4\n0*b3400:\s+((?:[0-9a-f]{2} ){4})[^\n]*\n> m \$66e6 8\n0*66e6:\s+((?:[0-9a-f]{2} ){8})[^\n]*\n> m \$6742 2\n0*6742:\s+(\w\w) (\w\w)', out, re.I)
    R = [(int(a), int(b.replace(' ', ''), 16), c.replace(' ', ''), d + e) for a, b, c, d, e in rows]
    n = len(R); same = [i for i in range(1, n) if R[i][2:] == R[i - 1][2:]]
    iv = [R[i][0] - R[i - 1][0] for i in range(1, n)]
    short = [i for i in range(1, n) if iv[i - 1] <= 1]
    print(snap, mhz, 'type', ty, 'hits', n, 'span_s', round((R[-1][1] - R[0][1]) / 300, 2), 'ticks/s clock', round((n - 1) * 300 / (R[-1][1] - R[0][1]), 3),
          '| hits <=1 VBL after the previous:', len(short), '| of all hits, pose (X,Y,heading) unchanged vs previous hit:', len(same), '| short hits with unchanged pose:', len(set(short) & set(same)))
    print('gaps hist', {g: iv.count(g) for g in sorted(set(iv))})
finally:
    h.close()
