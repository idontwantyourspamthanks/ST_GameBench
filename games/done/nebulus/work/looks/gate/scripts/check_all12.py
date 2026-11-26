"""12-level all-nibble file (mk_looks2.py all12.ovl, played from the campaign list by run_look.py camp): palette/raster/skyline == stock tower c', eye frames == stock design e',
rsCol/rsEye caches, tower word = base.  usage: check_all12.py REFDIR(base8 dump of the same machine) DIR"""
import sys, struct, hashlib
REF, DIR = sys.argv[1], sys.argv[2]
c12 = [((i * 3) % 8, (0, 8, 1, 7, 4, 2, 8, 0, 5, 3, 6, 8)[i], (0, 4, 4, 0, 1, 2, 3, 4, 2, 1, 3, 0)[i]) for i in range(12)]
rd = lambda d, i: open(f'{d}/lvl{i}.bin', 'rb').read()
ref = [rd(REF, t) for t in range(8)]
def reg(x, a, n): return x[a:a + n]
def sig(x): return (reg(x, 0x351ac, 0x20), reg(x, 0x40398, 8), hashlib.md5(reg(x, 0x100e0, 0x1000)).digest(), hashlib.md5(reg(x, 0x24be0, 0xaf00)).digest())
S = [sig(x) for x in ref]; fails = 0
for i, (b, c, e) in enumerate(c12):
    x = rd(DIR, i); s = sig(x); ct = c - 1 if c else b; et = e - 1 if e else b
    ok_c = s[:3] == S[ct][:3]; ok_e = s[3] == S[et][3]
    rc = struct.unpack('>H', reg(x, 0x77c80 + 62, 2))[0]; re_ = struct.unpack('>H', reg(x, 0x77c80 + 50, 2))[0] & 3; tw = struct.unpack('>H', reg(x, 0x3390c, 2))[0]
    ok_r = rc == ct and re_ == et & 3 and tw == b
    good = ok_c and ok_e and ok_r; fails += not good
    print(f'level {i:2d} base T{b+1} colours {c} enemies {e} | pal/raster/sky == stock T{ct+1}: {ok_c} | eyes == stock design T{et+1}: {ok_e} | rsCol {rc} rsEye {re_} tower {tw}: {ok_r}  {"PASS" if good else "FAIL"}')
print('FAILS', fails)
