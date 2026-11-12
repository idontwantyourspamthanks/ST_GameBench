#!/usr/bin/env python3
"""Fire-rate measurement: count projectiles per single press, VBL-exact presses injected into the IKBD state.

usage: fire.py LABEL SNAPSHOT MACHINE MEM MODE WEAPON_IDX [--live PREFIX] [--clock MHZ] [--game DIR] [--presses 4,10,20,100] [--real]
  MODE J = joystick fire ($75a2 bit0 = IKBD right button = joystick-1 fire, read by $26bea in J mode -> $6872)
       M = mouse mode, fire key Space (ISR make/break replayed: $7684/$7686/$75ac/$770a/$770c)
       B = M mode, left+right mouse buttons (IKBD header $f8|3 -> $6fbe), must not fire
  presses = VBLs held (1 VBL = 20 ms at 50 Hz): 4 = 80 ms, 10 = 200 ms, 20 = 400 ms, 100 = held 2 s
Counters (Hatari trace breakpoints, one log line per hit): TICK pc=$3148e (world tick, PH 1), KEYC pc=$1aaa4 (key/fire consumer entered),
FIRE pc=$1ab8e (fire dispatch = weapon handler jump), SPAWN pc=$35152 (projectile spawn); plus the ammo byte $ef8a[idx] before/after.
"""
import sys, time, re, json
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/jagpad')
from jt import *
from stharness import MACHINE_TOS

BPS = {'TICK': 0x3148e, 'KEYC': 0x1aaa4, 'FIRE': 0x1ab8e, 'SPAWN': 0x35152, 'SPAWN2': 0x2a474}

def main():
    a = sys.argv[1:]
    label, snap, machine, mem, mode, widx = a[:6]
    widx = int(widx)
    opt = {'--live': None, '--clock': None, '--game': None, '--presses': '80x6,200x6,400x4,2000', '--hz': '50', '--cpu': '8', '--gap': '53', '--type': None}
    real = '--real' in a
    i = 6
    while i < len(a):
        if a[i] in opt: opt[a[i]] = a[i+1]; i += 2
        else: i += 1
    hz = float(opt['--hz']); cpu = float(opt['--cpu'])
    pms = []
    for tok in opt['--presses'].split(','):
        ms, _, n = tok.partition('x')
        pms += [int(ms)] * int(n or 1)
    presses = [max(1, round(ms * hz / 1000)) for ms in pms]
    gap = int(opt['--gap'])
    tt = machine == 'tt'
    extra = ['--joy1', 'keys' if real else 'none'] + (['--mmu', 'true'] if tt else [])
    kw = {}
    if opt['--game']: kw['game_dir'] = G / opt['--game']
    h = Hatari(snapshot=str(G / snap), machine=machine, tos=MACHINE_TOS[machine], memsize_kb=int(mem), extra=extra, **kw)
    res = {'label': label, 'snapshot': snap, 'machine': machine, 'mode': mode, 'weapon': widx, 'live': opt['--live'], 'clock': opt['--clock'], 'rows': []}
    try:
        time.sleep(5)
        if opt['--clock']:
            h.set_cpuclock(int(opt['--clock']))
        if opt['--live']:
            apply_live(h, str(G / opt['--live']))
            time.sleep(2)
        if opt['--type']:
            t1 = time.time()
            while w(h, 0x6220) != int(opt['--type']):
                if time.time() - t1 > 600: raise TimeoutError('vehicle type never reached')
                time.sleep(3)
            time.sleep(3)
        if mode == 'J': jmode(h)
        else: mmode(h)
        res['type'] = w(h, 0x6220); res['view'] = w(h, 0x700a)
        res['modes'] = [w(h, 0xeb76), w(h, 0xeb78), w(h, 0xeb7a)]
        h.debug(f'w $18112 $00 ${widx:02x}', 0.4)
        h.debug(f'w ${0xef8a+widx:x} $fa', 0.4)
        res['sel'] = w(h, 0x18112); res['ammo0'] = memb(h, 0xef8a + widx, 1)[0]
        # cadence of the 25 Hz/5 Hz passes is whatever the machine does; settle
        time.sleep(3)
        h.debug('b all', 0.3)
        for n, adr in BPS.items():
            h.cmd(f'hatari-debug b pc = ${adr:x} :trace'); time.sleep(0.4)
        # build the event chain
        d = h.R / 'ev'; d.mkdir(exist_ok=True)
        v0 = h.vbl() + 120
        ev = []   # (vbl, name, lines)
        t = v0
        for L in presses:
            if mode == 'J':
                dn, up = ['w $75a2 $01'], ['w $75a2 $00']
            elif mode == 'B':
                dn, up = ['w $75a2 $03'], ['w $75a2 $00']
            else:
                dn = ['w $7684 $00 $39', 'w $76bf $ff', 'w $75ac $ff $ff', 'w $770a $00 $39', 'w $770c $00 $00']
                up = ['w $76bf $00', 'w $770a $00 $00', 'w $7708 $00 $39']
            ev.append((t, f'down{L}', dn)); ev.append((t + L, f'up{L}', up))
            t += L + gap
        ev.append((t, 'end', []))
        res['events'] = [(v, n) for v, n, _ in ev]
        # M mode break: the ISR leaves $7684 = $b9 if the make was not fetched yet ($75ac != 0), else clears it ($75ac == 0, nothing to do).
        # Two complementary conditional breakpoints (a flag word per press makes sure only one chain step runs).
        # M mode break: the ISR would leave $7684 = $b9 if the make was not fetched yet, else clear it. Either way exactly one event with scancode $39
        # (the make latch gives the same $39 & $7f), so the break is replayed as table/$770a/$7708 only (no conditional breakpoints: they hung Hatari on TT / Mega STE).
        def arm(k):
            return [f'b VBL > {ev[k][0]} :trace :once :file {d}/e{k}.txt']
        for k, (v, name, lines) in enumerate(ev):
            nxt = arm(k + 1) if k + 1 < len(ev) else []
            (d / f'e{k}.txt').write_text('\n'.join(['e VBL', 'e CycleCounter', f'm ${0xef8a+widx:x} 1'] + lines + nxt) + '\n')
        # clear the per-press flag words used by the M-mode break breakpoints (free RAM, but not guaranteed zero)
        for off in range(0, 80, 20):
            h.debug(f'w ${0xbc000 + off:x} ' + ' '.join(['$00'] * 20), 0.4)
        start = len(h._logtext())
        a0 = memb(h, 0xef8a + widx, 1)[0]
        if real:
            res['note'] = 'real keys: Right Ctrl/space via xdotool, wall-clock holds'
        for c in arm(0): h.cmd('hatari-debug ' + c); time.sleep(0.4)
        t0 = time.time()
        while True:
            lg = h._logtext()[start:]
            if len(re.findall(r'> e VBL', lg)) >= len(ev) and len(re.findall(r'> e CycleCounter', lg)) >= len(ev): break
            if time.time() - t0 > 1500: raise TimeoutError('chain did not finish')
            time.sleep(2)
        time.sleep(1)
        lg = h._logtext()[start:]
        h.debug('b all', 0.3)
        res['ammo1'] = memb(h, 0xef8a + widx, 1)[0]
        (h.R / 'log.txt').write_text('')
        res['rawlog'] = lg
        (G / 'work/fire/out').mkdir(exist_ok=True); (G / 'work/fire/out' / f'{label}.raw').write_text(lg)
        # partition
        mm = list(re.finditer(r'> e VBL\n= [^\n]*#(\d+) \(dec\)[^\n]*\n> e CycleCounter\n= [^\n]*#(\d+)[^\n]*\(dec\)', lg))
        marks = [(m.start(), ev[k][1], int(m.group(1))) for k, m in enumerate(mm)]
        cyc = [int(m.group(2)) for m in mm]
        res['marks'] = [(n, vv) for _, n, vv in marks]
        res['press_ms'] = {}
        for k in range(len(mm) - 1):
            if ev[k][1].startswith('down'):
                res['press_ms'][ev[k][1]] = round(((cyc[k+1] - cyc[k]) % 2**32) / (cpu * 1000.0), 1)
        res['cycles_per_vbl'] = round(((cyc[-1] - cyc[0]) % 2**32) / (marks[-1][2] - marks[0][2]))
        for j, (pos, name, _) in enumerate(marks[:-1]):
            seg = lg[pos: marks[j+1][0]]
            cnt = {n: 0 for n in BPS}
            for m in re.finditer(r'\n\tpc = \$([0-9a-f]+) :trace', seg):
                for n, adr in BPS.items():
                    if int(m.group(1), 16) == adr: cnt[n] += 1
            res['rows'].append({'ev': name, **cnt})
    finally:
        h.close()
    out = G / 'work/fire/out'; out.mkdir(exist_ok=True)
    raw = res.pop('rawlog', '')
    (out / f'{label}.log').write_text(raw)
    (out / f'{label}.json').write_text(json.dumps(res, indent=1))
    print(label, 'press_ms', res.get('press_ms'), 'cycles/VBL', res.get('cycles_per_vbl'))
    print(label, res['machine'], 'mode', mode, 'weapon', widx, 'type', res.get('type'), 'sel', res.get('sel'), 'ammo', res.get('ammo0'), '->', res.get('ammo1'), 'modes', res.get('modes'))
    agg = {}
    for r in res['rows']:
        if r['ev'].startswith('down'):
            agg.setdefault(r['ev'], []).append(r)
    for ev_, rs in agg.items():
        print('  %-9s n=%d  FIRE/press %s  SPAWN %s SPAWN2 %s KEYC %s TICK %s' % (ev_, len(rs), [r['FIRE'] for r in rs], sum(r['SPAWN'] for r in rs), sum(r['SPAWN2'] for r in rs), sum(r['KEYC'] for r in rs), sum(r['TICK'] for r in rs)))

main()
