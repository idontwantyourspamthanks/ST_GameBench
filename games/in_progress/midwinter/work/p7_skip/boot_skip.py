#!/usr/bin/env python3
"""Cold boot of a built set (default build + p7_skip_*) to the ski view and exercise the static-frame skip.
    python3 boot_skip.py NAME MACHINE(ste|megaste) TOS(1.62|2.06) MEM_KB GAME_DIR [--spawn]
Standing / walking / turning: flips per 1000 VBL with the skip live vs reverted (both sites restored to their original bytes at a
flip, same session), skip counters (D = $b6000).  --spawn: Training OFF (mortars/bombers OFF as well): wait for the enemy object
($1ce02 slot) and log what the skip does while it approaches (counters, slot, screenshots)."""
import sys, json, time, struct, shutil, traceback, re
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench')
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'games/in_progress/midwinter/tools')]
from mw1 import MW1
from stharness import TOS
sys.path.insert(0, str(ROOT / 'games/in_progress/midwinter/work/p7_skip'))
import vloop
name, machine, tos, mem, game = sys.argv[1:6]
spawn = '--spawn' in sys.argv
doverify = '--verify' in sys.argv
out = ROOT / 'games/in_progress/midwinter/work/p7_skip/boot'; out.mkdir(exist_ok=True)
spec = json.load(open('/tmp/p7s/sk.json'))
SITES = [s for s in spec['sites'] if s['name'] in ('p7_skip_sky', 'p7_skip_render')]
assert len(SITES) == 2
ZERO = Path('/tmp/p7s/zero.bin'); ZERO.write_bytes(bytes(2112))
log = []
def L(*a):
    s = ' '.join(str(x) for x in a); log.append(s); print(s, flush=True)
def cnt(h):
    f = out / f'{name}_cnt.bin'
    if f.exists(): f.unlink()
    h.debug(f'savebin {f} $b6000 $40', 1.0)
    raw = f.read_bytes(); l = lambda o: int.from_bytes(raw[o:o+4], 'big')
    return dict(GEN=int.from_bytes(raw[4:6], 'big'), NSKIP=l(16), NREND=l(20), NCHG=l(24), NMK=l(28), NFORCE=l(32), NINV=l(36), NUNS=l(40))
def at_flip(h, cmds):
    f = h.R / 'atflip.txt'; f.write_text("\n".join(cmds) + "\n")
    h.debug("b all", 0.3)
    start = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $bd9a :trace :once :file {f}")
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[start:]:
        if time.time() - t > 60: raise TimeoutError('flip')
        time.sleep(0.2)
    time.sleep(0.3)
def sites(h, key):
    cmds = []
    if key == 'new':
        cmds.append(f'loadbin {ZERO} $b6000')            # clean state, as at boot
    for s in SITES:
        cmds.append(f"w ${s['addr']:x} " + ' '.join(f'${b:02x}' for b in bytes.fromhex(s[key])))
    at_flip(h, cmds)
def pos(h):
    return (h.peekl(0x12c60), h.peekl(0x12c64), h.peekw(0x12c98) & 0x3ff)
def meas(h, tag, vbls=1000):
    c0 = cnt(h); f = h.fps(vbls); c1 = cnt(h)
    d = {k: c1[k] - c0[k] for k in ('NSKIP', 'NREND', 'NCHG', 'NMK', 'NFORCE', 'NINV', 'NUNS')}
    L(f'  {tag}: {f["flips"]} flips / {vbls} VBL ({f["fps"]:.2f} fps)  counter deltas {d}  pos {pos(h)}')
    return f['flips']
h = None
try:
    kw = dict(snapshot=None, memsize_kb=int(mem), game_dir=ROOT / game, tos=TOS[tos])
    if machine != 'ste': kw['machine'] = machine
    h = MW1(**kw)
    L('cell', name, machine, tos, mem, game, 'spawn' if spawn else '')
    t0 = time.time()
    if spawn: h.boot_to_game('M', training=False, mortars=False, bombers=False)
    else: h.boot_to_game('M')
    L(f'boot_to_game ok in {time.time()-t0:.0f}s; gstate {h.gstate()}')
    L('MWPO:', h.peek(0xb2ff8, 4))
    for s in SITES: L(f"site ${s['addr']:x}:", h.peek(s['addr'], 6).hex(), '(new', s['new'] + ')')
    h.center(); time.sleep(4)
    L('counters after boot (standing):', cnt(h))
    shutil.copy(h.shot(), out / f'{name}_stand.png')
    if spawn:
        L('training/mortars/bombers flags', h.options_flags())
        seen = False; did_verify = False
        prev = cnt(h)
        for i in range(400):
            time.sleep(0.6)
            slot = h.peek(0x1cd7e + 3 * 0x2c, 0x2c)
            flag = struct.unpack('>h', slot[0x26:0x28])[0]
            if flag >= 0 or i % 20 == 0:
                x, y = struct.unpack('>II', slot[6:14]); px, pz = h.peekl(0x12c60), h.peekl(0x12c64)
                c = cnt(h); dd = {k: c[k] - prev[k] for k in ('NSKIP', 'NREND', 'NCHG', 'NUNS')}; prev = c
                L(f'  sample {i:3d}: slot3 flag {flag} pos ({x},{y}) dist ({x-px},{y-pz}) $26 {flag} counter deltas since the last sample {dd} act {h.peekw(0x1efde)}')
                if flag >= 0:
                    seen = True
                    if i % 3 == 0: shutil.copy(h.shot(), out / f'{name}_enemy_{i:03d}.png')
            if flag >= 0 and doverify and not did_verify:
                did_verify = True
                L('  self-check of the skip decisions with the enemy active (A = buffers at the skip decision, B = after the forced render):')
                ok, bad = vloop.run_checks(h, '/tmp/p7s/sk', 12, maxwait=40, log=L)
                L(f'  self-check: {ok} identical, {bad} MISMATCH')
            if h.peekw(0x1efde) != 0:
                L('  action mode ended (enemy reached the player) -> Decisions'); break
        L('enemy seen:', seen)
        raise SystemExit
    L('STANDING, skip live / reverted (both sites), same session:')
    r = {}
    for key in ('new', 'orig', 'new', 'orig'):
        sites(h, key); time.sleep(2); r.setdefault(key, []).append(meas(h, 'skip live' if key == 'new' else 'skip reverted'))
    sites(h, 'new'); time.sleep(2)
    p0 = pos(h)
    h.walk(); time.sleep(6)
    p1 = pos(h)
    L('walk', p0, '->', p1, 'moved' if p0[:2] != p1[:2] else 'NOT moved')
    shutil.copy(h.shot(), out / f'{name}_walk.png')
    L('WALKING (500 VBL windows):')
    for key in ('new', 'orig'):
        sites(h, key); time.sleep(1); meas(h, 'skip live' if key == 'new' else 'skip reverted', 500)
    sites(h, 'new')
    h.stop(); time.sleep(10)
    c0 = cnt(h); p2 = pos(h); time.sleep(5); c1 = cnt(h); p3 = pos(h)
    L('after stopping: pos', p2, '->', p3, 'counter delta', {k: c1[k] - c0[k] for k in c0 if k != 'GEN'})
    h0 = h.peekw(0x12c98) & 0x3ff
    for i in range(6):
        h.rel(60, 0); time.sleep(1)
    h1 = h.peekw(0x12c98) & 0x3ff
    L('TURN: heading', h0, '->', h1, 'turned' if h0 != h1 else 'NOT turned (mouse offset persists: the yoke turns while displaced)')
    shutil.copy(h.shot(), out / f'{name}_turn.png')
    L('TURNING (500 VBL windows, pointer still displaced):')
    for key in ('new', 'orig'):
        sites(h, key); time.sleep(1); meas(h, 'skip live' if key == 'new' else 'skip reverted', 500)
    sites(h, 'new')
    h.center(); time.sleep(10)
    c0 = cnt(h); time.sleep(5); c1 = cnt(h)
    L('after the turn (pointer centred): heading', h.peekw(0x12c98) & 0x3ff, 'counter delta', {k: c1[k] - c0[k] for k in c0 if k != 'GEN'})
    shutil.copy(h.shot(), out / f'{name}_stand2.png')
    L('final counters', cnt(h))
    L('RESULT flips/1000VBL standing', r)
except SystemExit:
    pass
except Exception as e:
    L('EXC', repr(e)); L(traceback.format_exc())
    try: shutil.copy(h.shot(), out / f'{name}_exc.png')
    except Exception: pass
finally:
    if h: h.close()
    (out / f'{name}.json').write_text(json.dumps(log, indent=1))
