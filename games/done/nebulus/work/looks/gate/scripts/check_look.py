"""Look gate: compare level-start dumps of a looks campaign with the per-tower reference (a flags-0 base8 run on the same build).
usage: check_look.py REFDIR LOOKDIR [cells=looks15|st6]   (REFDIR = run_look.py of base8, 8 levels = towers T1..T8, flags 0; LOOKDIR = the cells)
For every cell (b,c,e): palette $351ac, raster $40398, skyline buffer $100e0 == ref[c'] ; eye frames $24be0 == ref[e'] (e' & 3 only matters) ; rsCol = c' ; rsEye&3 = e'&3 ;
tower word $3390c = b ; rows/grid/timer/title follow the record (grid md5 equal to the reference grid)."""
import sys, struct, hashlib
sys.path.insert(0, 'work/looks')
REF, DIR = sys.argv[1], sys.argv[2]
CELLS = sys.argv[3] if len(sys.argv) > 3 else 'looks15'
sys.path.insert(0, 'work/editor')
import importlib.util
ns = {}; exec(compile(open('work/looks/mk_looks2.py').read().split("d = sys.argv[1]")[0], 'mk', 'exec'), ns)
CELL = ns['CELLS'] if CELLS == 'looks15' else ns['ST6'] if CELLS == 'st6' else None
def rd(d, i): return open(f'{d}/lvl{i}.bin', 'rb').read()
ref = [rd(REF, t) for t in range(8)]
def reg(x, a, n): return x[a:a + n]
def sig(x):
    return dict(pal=reg(x, 0x351ac, 0x20), ras=reg(x, 0x40398, 8), sky=hashlib.md5(reg(x, 0x100e0, 0x1000)).hexdigest()[:8],
                eye=hashlib.md5(reg(x, 0x24be0, 0xaf00)).hexdigest()[:8], balls=hashlib.md5(reg(x, 0x14560, 0x400)).hexdigest()[:8],
                grid=hashlib.md5(reg(x, 0x327f0, 0x1000)).hexdigest()[:8])
S = [sig(x) for x in ref]
fails = 0
print(f"{'lvl':>3} {'b':>2} {'c':>2} {'e':>2} | pal ras sky | eye | grid | rsCol rsEye tower | expected colour tower / eye tower")
for i, (b, c, e) in enumerate(CELL):
    x = rd(DIR, i); s = sig(x)
    ct = c - 1 if c else b; et = e - 1 if e else b
    ok_c = s['pal'] == S[ct]['pal'] and s['ras'] == S[ct]['ras'] and s['sky'] == S[ct]['sky']
    ok_e = s['eye'] == S[et]['eye']
    ok_g = s['grid'] == S[0]['grid'] and s['balls'] == S[0]['balls']
    rc = struct.unpack('>H', reg(x, 0x77c80 + 62, 2))[0]; re_ = struct.unpack('>H', reg(x, 0x77c80 + 50, 2))[0] & 3
    tw = struct.unpack('>H', reg(x, 0x3390c, 2))[0]
    ok_r = rc == ct and re_ == et & 3 and tw == b
    # also: the eye buffer must NOT equal another tower's eye design unless the designs coincide (t&3)
    others = [t for t in range(8) if S[t]['eye'] == s['eye']]
    good = ok_c and ok_e and ok_g and ok_r
    fails += not good
    print(f"{i:3d} T{b+1} {c:2d} {e:2d} | {ok_c!s:5} | {ok_e!s:5} {others} | {ok_g!s:5} | rsCol {rc} rsEye {re_} tower {tw} {ok_r!s:5} | colour {ct+1} eye {et+1}  {'PASS' if good else 'FAIL'}")
# screenshot cross-check (palette + raster + skyline + tower TEXTURE together): the tower body / sky / skyline of a level with colours c must look exactly like the stock tower c
# (same grid, same position); compared on a crop that excludes the HUD, the frog and the enemies
from PIL import Image, ImageChops
def crop(p, box): return Image.open(p).convert('RGB').crop(box)
BOX = (96, 110, 736, 290)          # y 110..290 of the 832x588 screenshot: sky, skyline, tower body above the frog row; no HUD
print('screenshot crop equality (colours c of the cell == stock tower c, flags 0):')
for i, (b, c, e) in enumerate(CELL):
    ct = c - 1 if c else b
    d = ImageChops.difference(crop(f'{DIR}/lvl{i}.png', BOX), crop(f'{REF}/lvl{ct}.png', BOX)).getbbox()
    mark = 'equal' if d is None else f'DIFF bbox {d}'
    fails += d is not None
    print(f'  cell {i} (b=T{b+1} c={c} e={e}) vs stock T{ct+1}: {mark}')
print('FAILS', fails)
