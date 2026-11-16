#!/usr/bin/env python3
"""shots.py (CrawlerApply): TT Crawler downhill; at 14 consecutive flips (a chain of :once breakpoints, each file saves both screen buffers + the
pose/phase words and arms the next) from the snapshot snap/ttp_crawler.sav (v1.4 code from a cold boot = the shipped-before p3cp_head).
  shots.py TAG [--after]: --after first overwrites the p3cp_head code ($b8000-$b86ff) with the new build's bytes (build/dh_new.img).
Output: ab/raw_TAG/ (bins + log), logs/shots_TAG.txt; PNG rendering: shots_png.py."""
import sys, os, re, time, argparse, json, shutil
os.environ['HATARI'] = '/home/ryan/Code/AtariST/hattari/build/src/hatari'
from cs import *
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from stharness import MACHINE_TOS
ap = argparse.ArgumentParser(); ap.add_argument('tag'); ap.add_argument('--after', action='store_true'); ap.add_argument('--n', type=int, default=14)
ap.add_argument('--poke', nargs='*', default=['6fba=01d20000', '66e6=00001c00', '6742=0100', '6294=0100', '764a=0100'])
a = ap.parse_args()
def pk(e):
    ad, val = e.split('='); return f"w ${int(ad,16):x} " + ' '.join(f'${b:02x}' for b in bytes.fromhex(val))
raw = HERE / 'ab' / f'raw_{a.tag}'; shutil.rmtree(raw, ignore_errors=True); raw.mkdir(parents=True)
kw = dict(machine='tt', tos=MACHINE_TOS['tt'], memsize_kb=4096, game_dir=GAME / 'build/game', extra=['--mmu', 'true', '--joy1', 'none'])
h = Hatari(snapshot=str(HERE / 'snap/ttp_crawler.sav'), **kw)
try:
    time.sleep(2)
    cmds = []
    if a.after:
        spec = json.loads((HERE / 'build/dh_new.json').read_text()); img = (HERE / 'build/dh_new.img').read_bytes()
        base = spec['img_base']
        for o in range(0xb8000 - base, 0xb8700 - base, 16):
            cmds.append(f"w ${base + o:x} " + ' '.join(f'${b:02x}' for b in img[o:o + 16]))
    cmds += [pk(e) for e in a.poke]
    N = a.n; files = []
    for k in range(N):
        f = h.R / f'chain{k}.txt'
        body = ['e VBL', 'm $66e6 8', 'm $764c 2', 'm $b42e6 2', 'm $67a6 8', 'm $ff8240 32', 'm $ff8400 32',
                f'savebin {raw}/b60000_{k:02d}.bin $60000 $8000', f'savebin {raw}/b70000_{k:02d}.bin $70000 $8000']
        if k + 1 < N: body.append(f'b pc = ${h.FLIP:x} :2 :trace :once :file {h.R / f"chain{k+1}.txt"}')
        f.write_text('\n'.join(body) + '\n')
    # apply: pokes, then arm the chain at the next flip (the apply breakpoint sits AT a flip; its own hit is the poke batch)
    cmds.append(f'b pc = ${h.FLIP:x} :2 :trace :once :file {h.R / "chain0.txt"}')
    v = h.vbl()
    at_flip(h, cmds, v + 60)
    t0 = time.time()
    while not (raw / f'b70000_{N-1:02d}.bin').exists():
        if time.time() - t0 > 300: raise TimeoutError(h._logtext()[-1500:])
        time.sleep(0.5)
    time.sleep(1)
    txt = h._logtext(); h.debug('b all', 0.3)
    (raw / 'log.txt').write_text(txt)
    rows = parse_hits(txt, 0x66e6)
    out = [f"flip {i:02d} vbl {r['vbl']} PH {rd(r, 0xb42e6)} X {rd(r, 0x66e6, 4)} alt {rd(r, 0x764c, 2, True)} drawn {rd(r, 0x67a6, 4):x}" for i, r in enumerate(rows)]
    (HERE / 'logs' / f'shots_{a.tag}.txt').write_text('\n'.join(out) + '\n'); print('\n'.join(out))
finally:
    h.close()
