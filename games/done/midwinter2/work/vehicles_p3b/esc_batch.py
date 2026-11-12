#!/usr/bin/env python3
"""esc_batch.py MHZ TYPES(comma) DV(comma) [--ticks N]: Esc exactness. For each type and Esc phase (poke VBL offset DV after the apply flip; the key table $7687
is poked every 4 VBL for 40 VBL as runtype 'esc<dv>'), run A and P and print: the tick at which $6220 changes (and the values), and runtype's per-tick diff summary."""
import sys, subprocess, pickle
H = '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b'
NAMES = "Tank Jeep Truck Bus Train Foot Speedboat Crawler Minisub Submarine Ship Frogman Biplane Helicopter Zeppelin Balloon Rocket Parachute FlyingBoat Hovercraft FlyingSub Swimming".split()
mhz = sys.argv[1]; types = [int(x) for x in sys.argv[2].split(',')]; dvs = sys.argv[3].split(',')
ticks = sys.argv[sys.argv.index('--ticks') + 1] if '--ticks' in sys.argv else '25'
def typeseq(name):
    rows = pickle.load(open(f'/tmp/vg/{name}.pkl', 'rb'))
    return [(r[0x6220] << 8) | r[0x6221] for r in rows]
for t in types:
    for dv in dvs:
        scen = 'esc' + dv
        r = subprocess.run(['python3', H + '/runtype.py', str(t), scen, 'P', '--ticks', ticks, '--mhz', mhz], capture_output=True, text=True)
        tag = f'{NAMES[t]}_{scen}_{mhz}'
        a = typeseq(tag + '_A'); p = typeseq(tag + '_P')
        def chg(s):
            for i in range(1, len(s)):
                if s[i] != s[i-1]: return i + 1, s[i-1], s[i]
            return None
        n = min(len(a), len(p))
        summ = [l for l in r.stdout.splitlines() if 'ticks compared' in l]
        print(f'ESC type {t} {NAMES[t]} dv {dv} {mhz}MHz: A type change {chg(a)} | P type change {chg(p)} | type seq equal {a[:n] == p[:n]} | {summ[0].split(": ",1)[1] if summ else r.stdout[-300:]}', flush=True)
