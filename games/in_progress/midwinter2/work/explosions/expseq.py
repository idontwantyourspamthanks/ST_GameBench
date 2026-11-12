"""Deterministic explosion sequence capture (STE snapshot, per-frame simulation).
usage: expseq.py SNAP SETNAME OUTDIR [--dist D] [--n N] [--turn-at K] [--turn V] [--life-at K]
SETNAME: stock | display | default | comma list of patch names
Per flip k=0..N: both screen buffers (visible 32000 B), $67a6 ptrs, KB block $b4680 (20 B), $6220, NPC slot 3."""
import sys, time, argparse, subprocess
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
ap = argparse.ArgumentParser()
ap.add_argument('snap'); ap.add_argument('setname'); ap.add_argument('out')
ap.add_argument('--dist', type=int, default=700); ap.add_argument('--n', type=int, default=40)
ap.add_argument('--turn-at', type=int, default=10); ap.add_argument('--turn', type=int, default=0)
ap.add_argument('--pitch', type=int, default=0)
ap.add_argument('--at-vbl', type=int, default=0)
ap.add_argument('--alt', type=int, default=0)
ap.add_argument('--machine', default='ste'); ap.add_argument('--mem', type=int, default=2048)
a = ap.parse_args()
B = 12
DISPLAY = ['p4_grid','p4_hud_pfx_fill','p4_hud_pfx_replay','p4_hud_pfx_ymin','p4_hud_pfx_circle','p4_hud_reset','p4_proj_axis','p4_proj_cols','p4_proj_div',
           'p4_walk','p4_walk_c4','p4_walk_ret','p4_walk_tab','p7_cell_cull','p7_cell_pre','p7_ck_enter','p7_ck_exit','p7_ck_obj','p7_ck_poly',
           'p7_ck_tab','p7_skip_enter','p7_skip_gate','p7_skip_render','p7_skip_scn','p7_skip_wv1','p7_skip_wv2','p7_skip_wv3']
if a.setname == 'stock': names = None
elif a.setname == 'display': names = DISPLAY
elif a.setname == 'nofix': names = [n for n in DISPLAY if n != 'p4_hud_pfx_circle']
elif a.setname == 'default': names = default_names()
else: names = a.setname.split(',')
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
live = None
if names is not None:
    import hashlib
    live = build_live(names, 'expseq_' + hashlib.md5(','.join(names).encode()).hexdigest()[:10])
h = Hatari(snapshot=a.snap, machine=a.machine, memsize_kb=a.mem)
try:
    v0 = h.vbl()
    at = a.at_vbl or ((v0 // 100) + 3) * 100
    base = 0x3532 + 3 * 0x42
    nearx = 25856 + int(a.dist * 0.7071); neary = 25600 - int(a.dist * 0.7071)
    for k in range(1, a.n + 1):
        cm = [f"savebin {out}/f{k:02d}_60000.bin $60000 $7d00", f"savebin {out}/f{k:02d}_70000.bin $70000 $7d00",
              f"savebin {out}/f{k:02d}_ptr.bin $67a6 8", f"savebin {out}/f{k:02d}_kb.bin $b4680 20",
              f"savebin {out}/f{k:02d}_npc.bin ${base:x} $42", f"savebin {out}/f{k:02d}_ty.bin $6220 2",
              f"savebin {out}/f{k:02d}_yaw.bin $6742 2", f"savebin {out}/f{k:02d}_pal.bin $ff8240 $20"]
        if k == a.turn_at and a.turn:
            cm.append(pokel(0x6fb6, a.turn & 0xffffffff))
        if k % B == 0 and k < a.n:      # Hatari holds at most 16 breakpoints: re-arm the next batch from this flip's file
            for j in range(k + 1, min(k + B, a.n) + 1):
                cm.append(f"b pc = ${h.FLIP:x} :{j-k+1} :trace :once :file {h.R}/f{j}.txt")
        (h.R / f'f{k}.txt').write_text('\n'.join(cm) + '\n')
    # one breakpoint per flip; the first flip is the one that runs the apply file
    apply = []
    if live: apply += apply_cmds(live)
    apply += ([pokel(base + 6, nearx), pokel(base + 10, neary)] if a.dist else []) + [pokew(base + 0x36, 1)]
    if a.alt: apply.append(pokew(base + 0xe, a.alt))
    for k in range(1, min(B, a.n) + 1):
        cnt = f" :{k+1}"
        apply.append(f"b pc = ${h.FLIP:x}{cnt} :trace :once :file {h.R}/f{k}.txt")
    (h.R / 'apply.txt').write_text('\n'.join(apply) + '\n')
    assert max(len(l) for l in apply) < 230, max(apply, key=len)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {at} && pc = ${h.FLIP:x} :trace :once :file {h.R}/apply.txt")
    wait_gone(h, start, 300)
    t = time.time()
    last = out / f'f{a.n:02d}_npc.bin'
    while not last.exists():
        if time.time() - t > 600: raise TimeoutError('captures incomplete')
        time.sleep(0.5)
    time.sleep(1.0)
    print('captured', a.n, 'flips; v0', v0, 'at', at)
    h.shot(str(out / 'final.png'))
finally:
    h.close()
