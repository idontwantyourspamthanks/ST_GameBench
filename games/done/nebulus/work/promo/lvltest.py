#!/usr/bin/env python3
"""Play a nightmare.py level in the real game (stock-code tower-1 start snapshot, grid poked in at a loop top) and log the creatures per game loop.

    python3 lvltest.py LEVEL_INDEX LOOPS [INPUTS] [--avi OUT.avi]
        INPUTS = "loop:byte,loop:byte" IKBD joystick byte poked at the top of that loop (bit0 up, 1 down, 2 left, 3 right, 7 fire); default none.

Writes /tmp/promo/lvl<N>.log (per loop: frog x y state; slots x y state kind speed) and prints a compact trajectory table.  The grid replaces the level
exactly as the editor's playtest does (cells + rows), so what runs here is what the campaign plays, only the colours/time come from tower 1.
"""
import re, sys, time
from pathlib import Path
BENCH = Path(__file__).resolve().parents[5]
NEB = BENCH / 'games/done/nebulus'
sys.path.insert(0, str(BENCH / 'tools')); sys.path.insert(0, str(NEB / 'tools')); sys.path.insert(0, str(Path(__file__).resolve().parent))
from nebulus import Nebulus, ORIGIN   # noqa: E402
import nightmare                      # noqa: E402

SNAP = Path('/home/ryan/Videos/AtariST/Nebulus-promos/release/snap/ste_stock_t1.sav')
LOOP_TOP, FLIP = 0x3dcf4, 0x3868e
AVI_ARGS = ['--avi-vcodec', 'png', '--avi-fps', '50', '--statusbar', 'false', '--borders', 'false', '--crop', 'true', '--zoom', '1']


def main():
    args = sys.argv[1:]
    avi = None
    if '--avi' in args:
        i = args.index('--avi'); avi = args[i + 1]; del args[i:i + 2]
    idx, loops = int(args[0]), int(args[1])
    inputs = {}
    if len(args) > 2:
        for x in args[2].split(','):
            a, b = x.split(':'); inputs[int(a)] = int(b, 0)
    d = nightmare.LEVELS[idx]()
    g = d['grid']
    blob = bytearray(16 * 256)
    for c in range(16):
        for r in range(d['rows']):
            blob[c * 256 + r] = g[c][r]
    wd = Path('/tmp/promo/lvl'); wd.mkdir(parents=True, exist_ok=True)
    for f in wd.glob('*.cmd'):
        f.unlink()
    (wd / 'g.bin').write_bytes(blob)
    ev = ['e 1000001', 'e VBL', f'loadbin {wd}/g.bin $327f0', f'w $33912 $00 ${d["rows"]-1:02x}', 'w $3792c $30 $39',
          'w $3393c $00 $03 $27 $f0', 'w $3ad98 $00 $48 $00 $48 $00 $48', 'w $338fc $00 $00']
    ev += [f'w ${0x33944 + 0x48 + 2 * k:x} 0 0' for k in range(4)]
    (wd / 'flip.cmd').write_text('e VBL\nm $33a16 12\nm $33944 8\nm $33950 8\nm $3398c 8\nm $339b0 8\nm $33998 8\n')
    ev.append(f'b pc = ${FLIP:x} :trace :file {wd}/flip.cmd')
    for i, byte in inputs.items():
        (wd / f'in{i}.cmd').write_text(f'w $38498 ${byte:02x}\n')
        ev.append(f'b pc = ${LOOP_TOP:x} :{i} :once :trace :file {wd}/in{i}.cmd' if i > 0 else f'w $38498 ${byte:02x}')
    (wd / 'end.cmd').write_text('e 1000002\nb all\n')
    ev.append(f'b pc = ${LOOP_TOP:x} :{loops} :once :trace :file {wd}/end.cmd')
    (wd / 'event.cmd').write_text('\n'.join(ev) + '\n')
    extra = AVI_ARGS + (['--avi-file', avi] if avi else [])
    for attempt in range(4):
        try:
            h = Nebulus(snapshot=str(SNAP), workdir=str(wd / 'run'), game=ORIGIN, extra=extra)
            break
        except RuntimeError:
            if attempt == 3:
                raise
            time.sleep(2)
    try:
        time.sleep(1.5)
        if avi:
            h.cmd('hatari-shortcut recanim'); time.sleep(1.0)
        h.debug('b all', 0.3)
        h.cmd(f'hatari-debug b pc = ${LOOP_TOP:x} :once :trace :file {wd}/event.cmd')
        t0 = time.time()
        while time.time() - t0 < 120 and '#1000002' not in h._logtext():
            time.sleep(0.4)
        time.sleep(0.8)
        if avi:
            h.cmd('hatari-shortcut recanim'); time.sleep(1.5)
        log = h._logtext()
    finally:
        h.close()
    Path(f'/tmp/promo/lvl{idx}.log').write_text(log)
    i0 = log.index('#1000001')
    body = log[i0:log.index('#1000002')]
    blocks = body.split('> e VBL')[2:]
    print('loop  frog(x,y,st) | slots x,y,state,kind,speed')
    for n, blk in enumerate(blocks):
        rows = re.findall(r'^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} ?)+)', blk, re.M | re.I)
        mem = {int(a, 16): bytes.fromhex(b.replace(' ', '')) for a, b in rows}
        w = lambda a, i: int.from_bytes(mem[a][2 * i:2 * i + 2], 'big', signed=True)
        try:
            frog = (w(0x33A16, 0), w(0x33A16, 1), w(0x33A16, 2 + 3))
            sl = [(w(0x33944, k), w(0x33950, k), w(0x3398C, k), w(0x339B0, k), w(0x33998, k)) for k in range(4)]
        except KeyError:
            continue
        if n % 2 == 0 or '-v' in sys.argv:
            print('%3d %s | %s' % (n, frog, ' '.join('(%d,%d,s%d,k%d,v%d)' % t if t[2] else '-' for t in sl)))


if __name__ == '__main__':
    main()
