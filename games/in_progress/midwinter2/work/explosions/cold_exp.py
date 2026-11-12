"""cold_exp.py MACHINE(ste1|tt4) BUILDDIR TAG [--n N] [--reuse]
Cold boot BUILDDIR -> Raids map -> Dhafra (Jeep) -> fire a missile, put its detonation in front of the camera, turn the camera with the real mouse
while both screen buffers are dumped at every flip (n flips).  Output: /tmp/ex/cold_TAG/ (f%03d_60000.bin, ...), screenshots shots_*.png, log."""
import sys, re, time, threading
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
import coldboot
from coldboot import *
mach, bdir, tag = sys.argv[1], sys.argv[2], sys.argv[3]
N = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 140
c = CFG[mach]
coldboot.BUILD = GAME / bdir
out = Path('/tmp/ex') / f'cold_{tag}'; out.mkdir(parents=True, exist_ok=True)
mapsav = f'/tmp/ex/cold_{tag}_map.sav'
B = 12
def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)
h = None if '--reuse' in sys.argv else coldboot.mk(c)
if h is not None:
    try:
        t0 = time.time(); cold_to_raid_map(h)
        log(tag, 'cold boot to the raid map: %d s, marker %s' % (time.time() - t0, memb(h, 0xb2ff8, 4)))
        h.savemem(mapsav)
    finally:
        h.close()
h = coldboot.mk(c, mapsav)
try:
    if c['clock']: h.set_cpuclock(c['clock'])
    time.sleep(float(sys.argv[sys.argv.index('--pre') + 1]) if '--pre' in sys.argv else 4)
    r = enter_raid(h, 446, 177); log('entered', r, 'marker', memb(h, 0xb2ff8, 4))
    time.sleep(6)
    log('type', hex(h.peekw(0x6220)), 'view', h.peekw(0x700a))
    h.shot(str(out / 'shot_00_start.png'))
    # the missile always takes NPC slot 3 here (free-slot search from the table start); poke it right after firing,
    # before it can detonate on its own far away (a TT runs the 19-tick life in about 4 s)
    import math
    px, py = uw(memb(h, 0x66e6, 4)), uw(memb(h, 0x66ea, 4)); hd = uw(memb(h, 0x6742, 2))
    th = hd * 2 * math.pi / 1024
    dist = 700
    nx, ny = int(px + dist * math.sin(th)), int(py + dist * math.cos(th))
    base = 0x3532 + 3 * 0x42
    log('player', px, py, 'heading', hd, '-> detonate at', nx, ny, 'type', hex(h.peekw(0x6220)))
    for k in range(1, N + 1):
        cm = [f"savebin {out}/f{k:03d}_60000.bin $60000 $7d00", f"savebin {out}/f{k:03d}_70000.bin $70000 $7d00",
              f"savebin {out}/f{k:03d}_ptr.bin $67a6 8", f"savebin {out}/f{k:03d}_kb.bin $b4680 20", f"savebin {out}/f{k:03d}_ty.bin $6220 2",
              f"savebin {out}/f{k:03d}_vbl.bin $b3400 4", f"savebin {out}/f{k:03d}_npc.bin ${base:x} $42"]
        if k % B == 0 and k < N:
            for j in range(k + 1, min(k + B, N) + 1):
                cm.append(f"b pc = ${h.FLIP:x} :{j-k+1} :trace :once :file {h.R}/f{j}.txt")
        (h.R / f'f{k}.txt').write_text('\n'.join(cm) + '\n')
    apply = [pokel(base + 6, nx), pokel(base + 10, ny), pokew(base + 0x36, 1)]
    for k in range(1, min(B, N) + 1):
        apply.append(f"b pc = ${h.FLIP:x} :{k+1} :trace :once :file {h.R}/f{k}.txt")
    (h.R / 'apply.txt').write_text('\n'.join(apply) + '\n')
    h.debug('b all', 0.3)
    for tries in range(10):
        h.key('space', hold=0.25); time.sleep(0.4)
        sl = memb(h, base, 0x42)
        if sw(sl[0x2e:0x30]) in (27, 28): break
    log('fire tries', tries + 1, 'slot3 type', sw(sl[0x2e:0x30]), 'state', sw(sl[0x3a:0x3c]), 'life', sw(sl[0x36:0x38]))
    h.cmd(f"hatari-debug b pc = ${h.FLIP:x} :trace :once :file {h.R}/apply.txt")
    # turn the camera with the real mouse while the dumps run
    def turn():
        time.sleep(1.5)
        for k in range(14):
            h.rel(30 if k < 7 else -30, 0, steps=3); time.sleep(0.25)
    th = threading.Thread(target=turn); th.start()
    t = time.time()
    last = out / f'f{N:03d}_vbl.bin'
    while not last.exists():
        if time.time() - t > 900: log('TIMEOUT'); break
        time.sleep(1)
    th.join(); time.sleep(1)
    h.shot(str(out / 'shot_99_end.png'))
    if '--flipcheck' in sys.argv:
        # view redraw while driving: count flips by three registers over 500 VBL ($ff8201 = the harness default, $ff8203, and the game's own draw pointer $67a6)
        h.rel(0, -200); time.sleep(0.3); h.rel(0, -200); time.sleep(0.5)
        def count(expr, vbls=500):
            h.debug('b all', 0.3)
            h.cmd(f'hatari-debug b {expr} :trace'); time.sleep(0.3)
            st = h._arm_vbl(vbls); o = h._wait_removed(st); h.debug('b all', 0.3)
            return len(re.findall(r'CPU breakpoint condition\(s\) matched|matched \d+ times', o)), o
        res = {}
        for nm, ex in (('$ff8201', '($ff8201).b ! ($ff8201).b'), ('$ff8203', '($ff8203).b ! ($ff8203).b'), ('$67a6', '($67a6).l ! ($67a6).l')):
            n, o = count(ex)
            res[nm] = max(len(re.findall(r'condition\(s\) matched', o)), len(re.findall(re.escape(nm) + r' = ', o)))
        pa = memb(h, 0x66e6, 8); time.sleep(1.0); pb = memb(h, 0x66e6, 8)
        log('FLIPCHECK flips per 500 VBL:', res, 'fps $ff8201 = %.2f' % (res['$ff8201'] * 50 / 500), '| player pos moved', pa != pb, pa.hex(), pb.hex())
    log('done', 'type', hex(h.peekw(0x6220)), 'bus error' if 'bus error' in h._logtext().lower() else 'no bus error')
finally:
    h.close()
