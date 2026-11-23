"""NebGateCore: input-stall gate on the SHIPPED build (work/ikbd/ r2/r5/mksnap logic, parametrised for machine and game path).
usage: ikg.py snap MACHINE            boot shipped, snapshot at START's stub call (STE $1b162 / Mega STE $213de), before the masked window
       ikg.py sweep MACHINE [GAME]    taps 0.0 0.3 0.6 0.9 1.2 1.4 s after the window start (80 ms) + a no-tap control
       ikg.py rand MACHINE N SEED     N random-tap trials (r5.py generator: 1-3 events of space/a/Return/Control_R/Right/MOUSE at 0..3 s, hold .04/.08/.15)
       ikg.py ctl                     control: old `patched` build (no ni_ikbd) snapshot, one tap at 0.3 s (expected dead = the harness can see the stall)"""
import sys, json, random, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
MY = G / 'work/gate_NebGateCore'
SHIP = MY / 'unz/NEBULUS'
CFG = {'ste': dict(stub=0x1b162, win=0x1b172, kw={}), 'megaste': dict(stub=0x213de, win=0x213ee, kw=dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096))}

def mk(machine, game, snapshot=None, tag='r'):
    return Nebulus(game=game, workdir=f'/tmp/strun-gc{tag}_{machine}', snapshot=snapshot, **CFG[machine]['kw'])

def snap(machine, game=SHIP, name='ship', tag='s'):
    h = mk(machine, game, tag=tag)
    try:
        h.cmd(f'hatari-debug b pc = ${CFG[machine]["stub"]:x} :trace :once')
        m, n = wait_log(h, r'matched 1 times', 0, timeout=400)
        f = MY / f'snap_{name}_{machine}.sav'
        h.savemem(str(f)); print('saved', f, f.stat().st_size, 'hit', bool(m), flush=True)
    finally:
        h.close()

def trial(machine, spec, game=SHIP, snapf=None, post_wait=4.0, win=None, tag='r'):
    taps = []
    if spec != 'none':
        for part in spec.split(','):
            f = part.split(':'); taps.append((float(f[0]), f[1] if len(f) > 1 else 'space', float(f[2]) if len(f) > 2 else 0.08))
    h = mk(machine, game, snapshot=str(snapf or MY / f'snap_ship_{machine}.sav'), tag=tag)
    res = {'machine': machine, 'spec': spec}
    try:
        ev = Path(h.R) / 'ev.txt'; ev.write_text('e VBL\n')
        h.cmd(f'hatari-debug b pc = ${(win or CFG[machine]["win"]):x} :trace :once :file {ev}')
        m, n = wait_log(h, r'#(\d+) \(dec\)', 0, timeout=90, step=0.005)
        t0 = time.time()
        res['win_vbl'] = int(m.group(1)) if m else None
        for dt, key, hold in sorted(taps):
            while time.time() - t0 < dt: time.sleep(0.002)
            tap(h, key, hold)
        time.sleep(max(0.0, 2.6 + post_wait - (time.time() - t0)))
        res['marker'] = h._marker_present()
        res['isr_hits'] = probe(h)
        res['alive'] = res['isr_hits'] >= 2
    finally:
        h.close()
    return res

def emit(r, out):
    print(json.dumps(r), flush=True)
    with open(MY / out, 'a') as f: f.write(json.dumps(r) + '\n')

if __name__ == '__main__':
    cmd, machine = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else 'ste')
    if cmd == 'snap':
        snap(machine)
    elif cmd == 'sweep':
        for dt in ('none', '0.0', '0.3', '0.6', '0.9', '1.2', '1.4'):
            spec = 'none' if dt == 'none' else f'{dt}:space:0.08'
            emit(trial(machine, spec), f'out/sweep_{machine}.jsonl')
    elif cmd == 'rand':
        n, seed = int(sys.argv[3]), int(sys.argv[4]); rng = random.Random(seed)
        for i in range(n):
            k = rng.choice([1, 1, 2, 3])
            ev = sorted((round(rng.uniform(0.0, 3.0), 2), rng.choice(['space', 'a', 'Return', 'Control_R', 'Right', 'MOUSE'])) for _ in range(k))
            spec = ','.join(f'{t}:{key}:{rng.choice([0.04, 0.08, 0.15])}' for t, key in ev)
            r = trial(machine, spec); r['in_window'] = any(t <= 1.3 for t, _ in ev)
            emit(r, f'out/rand_{machine}.jsonl')
    elif cmd == 'ctl':      # control = the default set minus ni_ikbd (/tmp/nebgc_noik): a tap inside the window must leave it dead
        NOIK = Path('/tmp/nebgc_noik')
        snap(machine, NOIK, 'noik', 'c')
        for spec in ('0.3:space:0.08', '0.9:space:0.08'):
            emit(trial(machine, spec, game=NOIK, snapf=MY / f'snap_noik_{machine}.sav', tag='c'), f'out/ctl_{machine}.jsonl')
