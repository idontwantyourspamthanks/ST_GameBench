import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
h = Hatari(snapshot='/home/ryan/Code/AtariST/midwinter2/work/snapshots/1mb_ingame_foot.sav', memsize_kb=1024)
D = [2000, 4000, 6000, 8000, 9000, 12000]
def w(a, v, n=4):
    h.debug(f"w ${a:x} " + ' '.join('$%02x' % ((v >> s) & 255) for s in range((n-1)*8, -1, -8)), 0.15)
try:
    px, py = 25600, 25600
    for i, d in enumerate(D):
        b = 0x3532 + i * 0x42
        w(b + 6, px - d); w(b + 0xa, py + 0 + i * 0)  # same y
        w(b + 0x2e, 1, 2); w(b + 0x3a, 0, 2)
    def rd():
        out = []
        for i, d in enumerate(D):
            b = 0x3532 + i * 0x42
            txt = h.debug(f"m ${b+6:x} 8", 0.4).strip().splitlines()[-1]
            hx = txt.split(':')[1].split()[:8]
            x = int(''.join(hx[:4]), 16); y = int(''.join(hx[4:8]), 16)
            out.append((d, x, y))
        return out
    a = rd(); time.sleep(4); b = rd(); time.sleep(4); c = rd()
    for i in range(len(D)):
        print('dist', D[i], 'start', a[i][1:], '+4s', b[i][1:], '+8s', c[i][1:], 'MOVED' if (b[i][1:] != a[i][1:] or c[i][1:] != b[i][1:]) else 'static')
finally:
    h.close()
