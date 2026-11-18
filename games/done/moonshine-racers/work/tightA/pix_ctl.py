"""Hatari A/B with sensitive controls on the SAME capture: python3 pix_ctl.py SNAP:FLIP,SNAP:FLIP ... 
For each (snap, flip): R = default set, C = R with all ta_* (incl. rb0, nomouse), controls = C + ONE poke:
  face_same (ta_face always 'same'), face_wrong (ta_face draws sprite+1), erase_short (box restore writes the wrong 48 bytes), glyph_bad (MOVEP write displaced by 2).
Prints per capture: $100e/$11ab/$10f8/$11b0 (what the game was doing), differing bytes in the face box (272-303 x 17-64), message box (112-271), and in total."""
import sys, os, json, re, time
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/tools')
os.environ.setdefault('MSRPATCH_TOOL', GAME + '/work/tightA/msrpatch_priv.py'); os.environ.setdefault('MSR_LIVETAG', '_tA')
import msrabtest as ab
import numpy as np
from msr import Moonshine
from pathlib import Path
sys.path.insert(0, GAME + '/tools'); import msrmask
BASE = ['hd_clouds', 'hd_nomap', 'hd_nomap2', 'hd_stage', 'mr_edge', 'rd_draw', 'rd_geom', 'rd_init']
R = ab.live_build(BASE + ['hd_init'])
C = ab.live_build(BASE + ['ta_init', 'ta_erase', 'ta_face', 'ta_glyph', 'ta_ymw', 'ta_rb', 'ta_rb0', 'ta_nomouse'])
F = ab.live_build(BASE + ['ta_init', 'ta_erase', 'ta_facestat', 'ta_glyph', 'ta_ymw', 'ta_rb', 'ta_rb0', 'ta_nomouse'])   # the VISIBLE variant: must differ in the face box while a message is typed
CTL = {'face_same': 'be112=600e', 'face_wrong': 'be11a=b0e4', 'erase_short': 'be042=0040', 'glyph_bad': 'be660=0002'}
LIVES = {'R': R, 'C': C, 'facestat': F}
for k, v in CTL.items(): LIVES[k] = ab.with_pokes(C, [v], 'tA_ctl_' + k)
out = ab.AB / 'tA' / 'ctl'; out.mkdir(parents=True, exist_ok=True)
BUF = {'b70000': (0x70000, 0x7d00), 'b78000': (0x78000, 0x7d00), 'ram': (0x1000, 0x200)}
def cap(sp, at, live, flip, name):
    h = Moonshine(snapshot=sp)
    try:
        h.capture_frames(str(out / name), flip_addr=0xD1CA, at_vbl=at, nth_flip=flip, live=str(live), buffers=BUF)
    finally:
        h.close()
    d = out / name
    ram = (d / 'ram.bin').read_bytes()
    return [msrmask.planar_to_idx((d / f'{b}.bin').read_bytes()) for b in ('b70000', 'b78000')], ram
def box(a, b, x0, y0, x1, y1): return int((a[y0:y1 + 1, x0:x1 + 1] != b[y0:y1 + 1, x0:x1 + 1]).sum())
for spec in sys.argv[1:]:
    snap, flip = spec.split(':'); flip = int(flip)
    sp = ab.snap_path(snap); at = ab.at_vbl_for(sp)
    res = {}
    for nm, lv in LIVES.items():
        res[nm] = cap(sp, at, lv, flip, f'{snap}_{flip}_{nm}')
    ram = res['R'][1]
    p100e = int.from_bytes(ram[0xe:0x10], 'big'); st = lambda a: ram[a - 0x1000]
    print(f'== {snap} flip {flip}: $100e={p100e} $11ab={st(0x11ab)} (ticker state: 0 none, 1 typing, >=2 held) $11b0={st(0x11b0)} (erase pending) $10f8={st(0x10f8)}')
    for nm in ('C', 'facestat', 'face_same', 'face_wrong', 'erase_short', 'glyph_bad'):
        tot = face = msg = 0
        for k in (0, 1):
            a, b = res['R'][0][k], res[nm][0][k]
            tot += int((a != b).sum()); face += box(a, b, 272, 17, 303, 64); msg += box(a, b, 112, 16, 271, 64)
        print(f'   {nm:12s} vs R: differing pixels total {tot:6d}  (face box {face:5d}, text box {msg:5d})  -> {"DIFFER" if tot else "IDENTICAL"}', flush=True)
