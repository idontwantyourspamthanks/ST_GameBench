#!/usr/bin/env python3
"""skistate.py BUILD MODE MACHINE: start walking, then force the true skiing state ($13542 = $ffff, lever $24fae = -256/-512) and watch x,z,speed; mouse forward/back moves the lever."""
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
S = Sampler(h, [(0x12c60, 8), (0x15112, 2), (0x12c98, 2), (0x24fba, 2), (0x24fae, 4), (0x13542, 2), (0x152a8, 2), (0x13540, 2), (0x1efde, 2), (0x4d66, 2), (0x15116, 2)])
U = lambda r, a: int.from_bytes(r[a], 'big')
def st(tag):
    r = S(); x, z = int.from_bytes(r[0x12c60][:4], 'big'), int.from_bytes(r[0x12c60][4:], 'big')
    P(f"{tag:10s} vbl={r['vbl']} x={x} z={z} speed={U(r,0x15112)} btn={U(r,0x24fba)} lever={s16(int.from_bytes(r[0x24fae][:2],'big'))} st13542={U(r,0x13542):04x} v152a8={U(r,0x152a8)} v13540={U(r,0x13540):04x} act={U(r,0x1efde)} skill4d66={U(r,0x4d66)} v15116={s16(U(r,0x15116))}")
    return r
try:
    if BUILD == 'stock': h.boot_to_options(timeout=600)
    h.boot_to_game(MODE, check=(MACH != 'tt'))
    time.sleep(2); st('idle')
    if MODE == 'M': h.click('1')
    else: kd(h, 'Control_R'); time.sleep(0.4); ku(h, 'Control_R')
    for i in range(9): st(f'walk{i}'); time.sleep(1.0)
    if MODE == 'M': h.click('1')          # second left click while the speed command is above $13540: the real skiing state ($13408)
    else: kd(h, 'Control_R'); time.sleep(0.4); ku(h, 'Control_R')
    for i in range(6): st(f'skiA{i}'); time.sleep(1.0)
    if MODE == 'M': h.rel(0, 100)
    else: kd(h, 'Down'); time.sleep(1.5); ku(h, 'Down')
    P('--- mouse down / stick Down')
    for i in range(4): st(f'skiBack{i}'); time.sleep(0.8)
    if MODE == 'M': h.rel(0, -100)
    else: kd(h, 'Up'); time.sleep(1.5); ku(h, 'Up')
    P('--- mouse up / stick Up')
    for i in range(5): st(f'skiFwd{i}'); time.sleep(0.8)
finally:
    h.close()
