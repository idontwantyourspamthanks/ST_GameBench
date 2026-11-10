#!/usr/bin/env python3
"""skipgo.py TYPE [MHZ=16] [--ticks N]: stop-and-go pixel gate of p7_skip_render_t for one vehicle type.
Two frame-locked runs (tick_vbl tick_head tick_render + the shipped display patches) from the type's Raids snapshot, one without the p7_skip set, one with it.
Input timeline (VBL after the apply flip): stand, forward ($6fba) at 30, stop at 130, forward again at 230, stop at 330.  At EVERY flip (pc=$26e98) both visible
screen buffers (2 x 32000 B) are dumped; the gate is that the per-flip pair of buffers is identical in both runs for all flips.  Skips fired = NSKIP counter delta."""
import sys, re, hashlib, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b')
from vt import *
import runtype
from concurrent.futures import ThreadPoolExecutor
DISP = open('/tmp/disp_set.txt').read().split(',') if False else None
BASE = 'p4_grid,p4_hud_pfx_fill,p4_hud_pfx_replay,p4_hud_pfx_ymin,p4_hud_reset,p4_proj_axis,p4_proj_cols,p4_proj_div,p4_walk,p4_walk_c4,p4_walk_ret,p4_walk_tab,p7_cell_cull,p7_cell_pre,p7_ck_enter,p7_ck_exit,p7_ck_obj,p7_ck_poly,p7_ck_tab,mw2_credit,tick_vbl,tick_head,tick_render'.split(',')
SK = 'p7_skip_render,p7_skip_enter,p7_skip_gate,p7_skip_scn,p7_skip_wv1,p7_skip_wv2,p7_skip_wv3'.split(',')
t = int(sys.argv[1]); mhz = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 16
ticks = int(sys.argv[sys.argv.index('--ticks') + 1]) if '--ticks' in sys.argv else 40
st = runtype.FORCE.get(t, t); snap = runtype.SNAPS[st]
fwd = [p for p in runtype.pokes(t, 'move') if p.startswith('6fba')][0]
def pk(s):
    a, v = s.split('='); return f"w ${int(a,16):x} " + ' '.join(f'${x:02x}' for x in bytes.fromhex(v))
def run(names, tag):
    live = build_live(names, 'sg_' + tag)
    h = Hatari(snapshot=str(SNAP / snap), memsize_kb=2048)
    try:
        if mhz != 8: h.set_cpuclock(mhz)
        v = h.vbl()
        cmds = apply_cmds(live) + ([pk('6220=%04x' % t)] if t in runtype.FORCE else [])
        hit = h.R / 'fl.txt'; hit.write_text('m $60000 32000\nm $70000 32000\n')
        start = len(h._logtext())
        at_flip(h, cmds, v + 100)
        tl = [(30, fwd), (130, '6fba=00000000'), (230, fwd), (330, '6fba=00000000')]
        for i, (dv, p) in enumerate(tl):
            lf = h.R / f'tl{i}.txt'; lf.write_text(pk(p) + '\n')
            h.cmd(f"hatari-debug b VBL > {v + 100 + dv} :trace :once :file {lf}"); time.sleep(0.15)
        h.cmd(f'hatari-debug b pc = ${h.FLIP:x} :trace :file {hit}')
        tt = time.time()
        while True:
            txt = h._logtext()[start:]
            n = len(re.findall(r'^00060000:', txt, re.M | re.I))
            if n >= ticks: break
            if time.time() - tt > 900: raise TimeoutError(txt[-500:])
            time.sleep(0.5)
        h.debug('b all', 0.5)
        txt = h._logtext()[start:]
        skips = None
        if 'p7_skip_render' in names:
            skips = memb(h, 0xb6014, 4)
        # split per flip: each flip = 0x60000 block then 0x70000 block
        hashes = []; cur = {}
        for m in re.finditer(r'^([0-9A-F]{8}):((?: [0-9a-f]{2})+)', txt, re.M | re.I):
            a = int(m.group(1), 16); b = bytes.fromhex(m.group(2).replace(' ', ''))
            if a == 0x60000 and cur: hashes.append({k: hashlib.md5(bytes(x)).hexdigest() for k, x in cur.items()}); cur = {}
            key = 0x60000 if a < 0x70000 else 0x70000
            cur.setdefault(key, bytearray()).extend(b)
        if cur: hashes.append({k: hashlib.md5(bytes(x)).hexdigest() for k, x in cur.items()})
        return hashes, skips
    finally:
        h.close()
with ThreadPoolExecutor(2) as ex:
    fa = ex.submit(run, BASE, f'a{t}'); fb = ex.submit(run, BASE + SK, f'b{t}')
    (ha, _), (hb, sk) = fa.result(), fb.result()
n = min(len(ha), len(hb))
bad = [i + 1 for i in range(n) if ha[i] != hb[i]]
print(f'SKIPGO type {t} {runtype.NAMES[t]} {mhz}MHz: flips compared {n}, differing flips {len(bad)} {bad[:10]}; skips fired (NSKIP at the end) {int.from_bytes(sk,"big") if sk else None}')
