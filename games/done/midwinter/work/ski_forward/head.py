#!/usr/bin/env python3
"""head.py BUILD MODE MACHINE: walk from standing at headings 0/256/512/768 (heading word $12c98 poked while standing), 5 s each, M or J start.
Prints x,z,speed at 0/1/2/3/5 s and the displacement."""
import os, sys, time
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/work/jagpad']
from jlib import *
BUILD, MODE, MACH = sys.argv[1], sys.argv[2].upper(), (sys.argv[3] if len(sys.argv) > 3 else 'ste')
cfg = {'ste': dict(machine='ste', memsize_kb=1024), 'tt': dict(machine='tt', memsize_kb=4096, extra=['--mmu', 'true'])}[MACH]
extra = (cfg.pop('extra', None) or []) + ['--joy1', 'keys']
if MACH == 'tt':
    extra += ['--monitor', 'vga', '--cpuclock', '32']
h = MW1(snapshot=None, game_dir=(str(GAME) if BUILD == 'stock' else BUILD), extra=extra, **cfg)
P = lambda *a: print(*a, flush=True)
S = Sampler(h, [(0x12c60, 8), (0x15112, 2), (0x12c98, 2), (0x24fba, 2), (0x1efde, 2)])
U = lambda r, a: int.from_bytes(r[a], 'big')
def st():
    r = S(); return (r['vbl'], int.from_bytes(r[0x12c60][:4], 'big'), int.from_bytes(r[0x12c60][4:], 'big'), U(r, 0x15112), U(r, 0x12c98) & 0x3ff, U(r, 0x1efde))
try:
    if BUILD == 'stock':
        h.boot_to_options(timeout=600)
    h.boot_to_game(MODE, check=(MACH != 'tt'))
    time.sleep(2)
    for hd in (0, 256, 512, 768):
        h.debug(f'w $12c98 ${hd >> 8:02x} ${hd & 255:02x}', 0.5)
        time.sleep(1.5)
        r0 = st()
        if MODE == 'M': h.click('1')
        else: kd(h, 'Control_R'); time.sleep(0.4); ku(h, 'Control_R')
        rows = []
        t = time.time()
        while time.time() - t < 6:
            rows.append(st()); time.sleep(0.8)
        if MODE == 'M': h.click('3')
        else: h.cmd('hatari-event keydown 52'); time.sleep(0.4); h.cmd('hatari-event keyup 52')
        time.sleep(3)
        r1 = st()
        P(f'heading {hd}: start x,z={r0[1:3]} -> rows(speed)={[r[3] for r in rows]} end x,z={rows[-1][1:3]} d=({rows[-1][1]-r0[1]},{rows[-1][2]-r0[2]}) head_now={rows[-1][4]} act={rows[-1][5]} after-stop x,z={r1[1:3]}')
finally:
    h.close()
