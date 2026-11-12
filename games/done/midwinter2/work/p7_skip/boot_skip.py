#!/usr/bin/env python3
"""Cold boot of a built set (default set + p7_skip_*) to the 3D view and exercise the static-frame skip.
    python3 work/p7_skip/boot_skip.py NAME MACHINE(ste|megaste) TOS(162|206) MEM_KB GAME_DIR
Standing / NPC-in-view / walking / turning: flips per 1000 VBL with the skip live vs reverted (p7_skip_render site restored to
its original bytes, same session), skip counters (D = $b6000), screenshots, positions."""
import sys, json, time, struct, shutil, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
name, machine, tos, mem, game = sys.argv[1:6]
TOS = {'206': ROOT / 'tos/TOS_2_06.img', '162': Path.home() / 'Emulators/BIOS/AtariST/TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img'}
out = ROOT / 'work/p7_skip/boot'; out.mkdir(exist_ok=True)
sites = {s['name']: s for s in json.load(open('/tmp/sk/skip.json'))['sites']}
S = sites['p7_skip_render']
log = []
def L(*a):
    s = ' '.join(str(x) for x in a); log.append(s); print(s, flush=True)
def cnt(h):
    f = out / f'{name}_cnt.bin'
    if f.exists(): f.unlink()
    h.debug(f'savebin {f} $b6000 $40', 1.0)
    raw = f.read_bytes(); l = lambda o: int.from_bytes(raw[o:o+4], 'big')
    return dict(VAL=struct.unpack('>2H', raw[0:4]), WV=struct.unpack('>2H', raw[4:8]), NSKIP=l(0x14), NREND=l(0x18), NINV=l(0x1c), NUNS=l(0x24), NSC=l(0x28), NOBJ=l(0x2c), NWAV=l(0x30))
def site(h, key):
    h.debug(f"w ${S['addr']:x} " + ' '.join(f'${b:02x}' for b in bytes.fromhex(S[key])), 0.3)
def pos(h):
    return (h.peekw(0x66e6) << 16 | h.peekw(0x66e8), h.peekw(0x66ea) << 16 | h.peekw(0x66ec), h.peekw(0x6742))
def meas(h, tag, vbls=1000):
    c0 = cnt(h); f = h.fps(vbls); c1 = cnt(h)
    d = {k: c1[k] - c0[k] for k in ('NSKIP', 'NREND', 'NINV', 'NUNS', 'NSC', 'NOBJ', 'NWAV')}
    L(f'  {tag}: {f["flips"]} flips / {vbls} VBL ({f["fps"]:.2f} fps)  counter deltas {d}  pos {pos(h)}')
    return f['flips']
h = None
try:
    h = Hatari(snapshot=None, memsize_kb=int(mem), game_dir=ROOT / game, machine=machine, tos=TOS[tos])
    L('cell', name, machine, tos, mem, game)
    h.boot_to_game('M')
    L('3D view: $6220=%x $700a=%x' % (h.peekw(0x6220), h.peekw(0x700A)))
    L('MWPO:', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    for n, s in sites.items():
        h.debug(f"m ${s['addr']:x} 8", 0.4)
    L('site $1dbbe now:', h.debug('m $1dbbe 6', 0.6).strip().splitlines()[-1], '(expect 4e f9 00 0b 75 10)')
    h.center(); time.sleep(4)
    L('counters after boot (standing):', cnt(h))
    p = h.shot(); shutil.copy(p, out / f'{name}_stand.png')
    L('STANDING, skip live / reverted (p7_skip_render site), same session:')
    r = {}
    for key in ('new', 'orig', 'new', 'orig'):
        site(h, key); time.sleep(2); r.setdefault(key, []).append(meas(h, 'skip live' if key == 'new' else 'skip reverted'))
    site(h, 'new'); time.sleep(2)
    # walk
    time.sleep(3)
    p0 = pos(h)
    h.rel(0, -200); h.center(); h.rel(0, -200); time.sleep(3)
    p1 = pos(h)
    L('walk', p0, '->', p1, 'moved' if p0[:2] != p1[:2] else 'NOT moved')
    p = h.shot(); shutil.copy(p, out / f'{name}_walk.png')
    L('WALKING (300 VBL windows; the walk is kept short: the cliff 6000 units west turns the player into another type):')
    for key in ('new', 'orig'):
        site(h, key); time.sleep(1); meas(h, 'skip live' if key == 'new' else 'skip reverted', 300)
    site(h, 'new')
    # stop (return the mouse to the dead zone) and turn
    h.center(); h.rel(0, 200); h.center(); time.sleep(12)
    c0 = cnt(h); p2 = pos(h); time.sleep(4); c1 = cnt(h); p3 = pos(h)
    L('after stopping: pos', p2, '->', p3, 'skip delta', c1['NSKIP'] - c0['NSKIP'], 'render delta', c1['NREND'] - c0['NREND'])
    # what still changes while the position does not? (diff of the staged scalar block $b6110 over 1 s)
    names = ['$6220','$66e0','$66e6h','$66e6l','$66eah','$66eal','$670a','$670c','$6f78','$67be','$6806','pad'] + [f'$763e+{2*i}' for i in range(18)] + ['$17fc4','$18768'] + [f'$18556+{2*i}' for i in range(6)] + [f'$18772+{2*i}' for i in range(4)] + ['$18784','$18786','$18788','$18796','$18798','$1879a','$53ac','$53ae','$53da','$53dc']
    def stage():
        f = out / f'{name}_stg.bin'
        if f.exists(): f.unlink()
        h.debug(f'savebin {f} $b6110 104', 1.0)
        raw = f.read_bytes(); return [int.from_bytes(raw[i:i+2], 'big') for i in range(0, 104, 2)]
    st0 = stage(); time.sleep(1.2); st1 = stage(); time.sleep(1.2); st2 = stage()
    L('  staged scalars that changed over 2.4 s:', [(names[i], hex(a), hex(b), hex(c)) for i, (a, b, c) in enumerate(zip(st0, st1, st2)) if not (a == b == c)])
    L('  $6220 type', hex(h.peekw(0x6220)), ' $40b6', hex(h.peekw(0x40b6)), ' msg timers', hex(h.peekw(0x7590)), hex(h.peekw(0x7582)), hex(h.peekw(0x759c)), ' $6298', hex(h.peekw(0x6298)))
    try:
        h.savemem(str(out / f'{name}_after_stop.sav'))
    except Exception as e:
        L('  savemem failed', repr(e))
    h0 = h.peekw(0x6742)
    for i in range(6):
        h.rel(60, 0); time.sleep(1)
    h1 = h.peekw(0x6742); time.sleep(8)
    L('TURN: heading', hex(h0), '->', hex(h1), 'turned' if h0 != h1 else 'NOT turned')
    p = h.shot(); shutil.copy(p, out / f'{name}_turn.png')
    c0 = cnt(h); time.sleep(4); c1 = cnt(h); h2 = h.peekw(0x6742)
    L('after the turn: heading', hex(h1), '->', hex(h2), 'skip delta', c1['NSKIP'] - c0['NSKIP'], 'render delta', c1['NREND'] - c0['NREND'])
    p = h.shot(); shutil.copy(p, out / f'{name}_stand2.png')
    # NPC in view (poked), standing: a moving unit must keep the view updating
    L('NPC poked 1200 units ahead of the standing player (moving):')
    for a, v in (('$3538', 0x00005b50), ('$353c', 0x00006400)):
        h.debug(f"w {a} " + ' '.join('$%02x' % ((v >> s) & 255) for s in (24, 16, 8, 0)), 0.3)
    h.debug('w $3560 $00 $01', 0.3); h.debug('w $356c $00 $00', 0.3)
    for i in range(3):
        time.sleep(3); p = h.shot(); shutil.copy(p, out / f'{name}_npc{i}.png')
        L('  npc0 x,y', h.debug('m $3538 8', 0.5).strip().splitlines()[-1][:60], ' counters', cnt(h))
    meas(h, 'NPC near, skip live')
    site(h, 'orig'); time.sleep(2); meas(h, 'NPC near, skip reverted'); site(h, 'new'); time.sleep(2)
    h.debug('w $3560 $ff $ff', 0.3)          # unit off again
    L('final counters', cnt(h))
    L('RESULT flips/1000VBL standing', r)
except Exception as e:
    L('EXC', repr(e)); L(traceback.format_exc())
    try: h.shot(out / f'{name}_exc.png')
    except Exception: pass
finally:
    if h: h.close()
    (out / f'{name}.json').write_text(json.dumps(log, indent=1))
