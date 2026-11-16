#!/usr/bin/env python3
"""pf.py: per-presented-flip log ($26e98) of the player pose, the p3cp scheduler words and (optionally) a hash of the picture just drawn.
  --snap PATH  --mach ste|tt  --mhz N (ste)  --live cand|none|NAME  (ste snapshots hold unpatched code; tt snapshots made from a cold boot are patched already)
  --scen stand|fwd|turn|both  --poke addr=hex ...  --hold addr=hex ... (re-poked at every tick, $31586)  --vbls N  --wait S  --frames (hash the 3D window per flip)  --tag T"""
import sys, os, argparse, hashlib
ap = argparse.ArgumentParser()
ap.add_argument('--snap', required=True); ap.add_argument('--mach', default='ste'); ap.add_argument('--mhz', type=int, default=32)
ap.add_argument('--live', default='cand'); ap.add_argument('--scen', default='fwd'); ap.add_argument('--poke', nargs='*', default=[]); ap.add_argument('--hold', nargs='*', default=[])
ap.add_argument('--vbls', type=int, default=200); ap.add_argument('--wait', type=float, default=5); ap.add_argument('--frames', action='store_true'); ap.add_argument('--tag', default=None)
ap.add_argument('--type', type=int, default=None); ap.add_argument('--shots', type=int, default=0)
ap.add_argument('--mouse', default=''); ap.add_argument('--mturn', type=int, default=0)       # real host mouse: 'dx,dy;dx,dy' before the wait; --mturn dx: rel(dx,0) every 0.25 s while logging
a = ap.parse_args()
if a.mach == 'tt': os.environ.setdefault('HATARI', 'hatari')        # the tt snapshots were saved by the system Hatari 2.6.1
from cs import *
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from stharness import MACHINE_TOS
tag = a.tag or (Path(a.snap).stem + '_' + a.mach + '_' + a.scen)
snap = a.snap if '/' in a.snap else str(SNAP / a.snap)
kw = dict(machine='tt', tos=MACHINE_TOS['tt'], memsize_kb=4096, game_dir=GAME / 'build/game', extra=['--mmu', 'true', '--joy1', 'none']) if a.mach == 'tt' else dict(memsize_kb=2048)
live = None
if a.mach != 'tt' and a.live != 'none':
    live = build_live(default_names(), 'cand') if a.live == 'cand' else str(HERE / 'build' / a.live)
def pk(e):
    ad, val = e.split('='); return f"w ${int(ad,16):x} " + ' '.join(f'${b:02x}' for b in bytes.fromhex(val))
h = Hatari(snapshot=snap, **kw)
try:
    time.sleep(2)
    if a.mach != 'tt' and a.mhz != 8: h.set_cpuclock(a.mhz)
    v = h.vbl()
    ty = a.type if a.type is not None else int.from_bytes(bytes.fromhex(re.findall(r'00006220:\s+((?:[0-9a-f]{2} ?){2})', h.debug('m $6220 2', 1.0), re.I)[-1].replace(' ', '')), 'big')
    hit = h.R / 'hit.txt'
    REG = [(0x66e6, 8), (0x6742, 2), (0x764c, 2), (0x676e, 2), (0x767e, 2), (0x6772, 2), (0x6220, 2), (0xb42e0, 16), (0xb8f20, 4), (0xb8f28, 4), (0x34936, 6), (0x6746, 2), (0x674a, 2), (0x674e, 2),
           (0xb8fae, 2), (0xb3400, 4), (0xb6014, 8), (0x67a6, 4), (0x763e, 12), (0x7652, 4)]
    hit.write_text('e VBL\n' + '\n'.join(f'm ${ad:x} {n}' for ad, n in REG) + '\n')
    cmds = (apply_cmds(live) if live else [])
    if a.scen != 'stand': cmds += move_pokes(ty, a.scen in ('fwd', 'both'), a.scen in ('turn', 'both'))
    cmds += [pk(e) for e in a.poke]
    if a.hold:
        hf = h.R / 'hold.txt'; hf.write_text('\n'.join(pk(e) for e in a.hold) + '\n')
        cmds.append(f'b pc = $31486 :trace :file {hf}')
    if cmds: at_flip(h, cmds, v + 60)
    for mv in [m for m in a.mouse.split(';') if m]:
        dx, dy = map(int, mv.split(',')); h.rel(dx, dy); time.sleep(0.3)
    time.sleep(a.wait)
    start = len(h._logtext())
    v0 = h.vbl()
    if a.frames:
        # sampled picture: every 4th row of the 3D window (rows 58-198) of both buffers, as `m` dumps (a chain of :once breakpoints at the same pc stalls Hatari)
        rowsamp = list(range(58, 200, 4))
        hit.write_text('e VBL\n' + '\n'.join(f'm ${ad:x} {n}' for ad, n in REG) + '\n' + '\n'.join(f'm ${base + r*160:x} 160' for base in (0x60000, 0x70000) for r in rowsamp) + '\n')
    h.cmd(f'hatari-debug b pc = $26e98 :trace :file {hit}'); time.sleep(0.2)
    if a.shots:
        for i in range(a.shots):
            time.sleep(0.25); h.shot(str(HERE / 'logs' / f'{tag}_s{i}.png'))
    time.sleep(0.2)
    if a.mturn:
        import threading
        stop = threading.Event()
        def turner():
            k = 0
            while not stop.is_set():
                h.rel(a.mturn if (k // 6) % 2 == 0 else -a.mturn, 0, 5); k += 1; time.sleep(0.05)
        threading.Thread(target=turner, daemon=True).start()
    st2 = len(h._logtext())
    h.cmd(f'hatari-debug b VBL > {v0 + a.vbls} :trace :once')
    t0 = time.time()
    while f'VBL > {v0 + a.vbls} :once :trace\nRemoved' not in h._logtext()[st2:].replace('\t', '') and 'Removed CPU breakpoint' not in h._logtext()[st2:].split(f'VBL > {v0 + a.vbls}')[-1]:
        if time.time() - t0 > 600: raise TimeoutError
        time.sleep(0.5)
    time.sleep(0.5)
    txt = h._logtext()[start:]; h.debug('b all', 0.3)
    open(HERE / 'logs' / f'{tag}.log', 'w').write(txt)
    rows = parse_hits(txt, 0x66e6)
    print(f'# {snap} type {ty} {a.mach} {a.mhz if a.mach != "tt" else 32} MHz live {a.live} {a.scen} poke {a.poke} hold {a.hold}: {len(rows)} flips in {a.vbls} VBL')
    prev = None; nchg = 0; ph = None; npic = 0; i = 0
    for r in rows:
        pose = (rd(r,0x66e6,4), rd(r,0x66ea,4), rd(r,0x6742), rd(r,0x764c,2,True))
        chg = prev is not None and pose != prev; nchg += chg; prev = pose
        pic = ''
        if a.frames:
            base = rd(r, 0x67a6, 4)
            try:
                d = bytes(r[base + rr*160 + k] for rr in range(58, 200, 4) for k in range(160))
                hsh = hashlib.md5(d).hexdigest()[:6]; pic = f'pic {hsh} ' + ('=' if hsh == ph else 'NEW'); npic += hsh != ph; ph = hsh
            except KeyError: pic = 'pic ?'
        i += 1
        print(f"vbl {r['vbl']} clk {rd(r,0xb3400,4)} PH {rd(r,0xb42e6)} SKIP {rd(r,0xb42ec)} ACC {rd(r,0xb42e4,2,True)} INT {rd(r,0xb8f20)} JP {rd(r,0xb8f28)} X {pose[0]} Y {pose[1]} H {pose[2]} alt {pose[3]} bank {rd(r,0x6746,2,True)} lean {rd(r,0x674e,2,True)} 676e {rd(r,0x676e)} spd {rd(r,0x6772,2,True)} ter {rd(r,0x34936,2,True)} sea {rd(r,0x34938,2,True)} v {rd(r,0x7642,2,True)} {rd(r,0x7644,2,True)} {rd(r,0x763e,2,True)} {rd(r,0x7640,2,True)} REST {rd(r,0xb8fae)} nskip {rd(r,0xb6014,4)} nrend {rd(r,0xb6018,4)} {pic} {'*' if chg else ''}")
    print(f'# pose changes {nchg} / {len(rows)-1}' + (f'; picture changes {npic} / {len(rows)}' if a.frames else ''))
    h.shot(str(HERE / 'logs' / f'{tag}.png'))
finally:
    h.close()
