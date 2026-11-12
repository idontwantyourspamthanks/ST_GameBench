#!/usr/bin/env python3
"""reenter.py BUILD MODE MACHINE: default Game Options, walk until the action mode ends (or 60 s), screenshot, then try again via Decisions->Skiing."""
import os, sys, time, shutil
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/work/jagpad']
from jlib import *
from mw1 import *
BUILD, MODE, MACH = sys.argv[1], sys.argv[2].upper(), (sys.argv[3] if len(sys.argv) > 3 else 'ste')
cfg = {'ste': dict(machine='ste', memsize_kb=1024), 'tt': dict(machine='tt', memsize_kb=4096, extra=['--mmu', 'true'])}[MACH]
extra = (cfg.pop('extra', None) or []) + ['--joy1', 'keys']
if MACH == 'tt':
    extra += ['--monitor', 'vga', '--cpuclock', '32']
h = MW1(snapshot=None, game_dir=(str(GAME) if BUILD == 'stock' else BUILD), extra=extra, **cfg)
P = lambda *a: print(*a, flush=True)
S = Sampler(h, [(0x12c60, 8), (0x15112, 2), (0x12c98, 2), (0x24fba, 2), (0x1efde, 2), (0x14ef6, 2), (0x12d5e, 4), (0x2c422, 2)])
U = lambda r, a: int.from_bytes(r[a], 'big')
OUT = '/tmp/MW1Ski/re_' + os.environ.get('FWD_TAG', 'x'); os.makedirs(OUT, exist_ok=True)
def st(tag):
    r = S(); x, z = int.from_bytes(r[0x12c60][:4], 'big'), int.from_bytes(r[0x12c60][4:], 'big')
    P(f"{tag:10s} vbl={r['vbl']} x={x} z={z} speed={U(r,0x15112)} head={U(r,0x12c98)&0x3ff} btn={U(r,0x24fba)} act={U(r,0x1efde)} exitflag={U(r,0x14ef6)} step={r[0x12d5e].hex()} $2c422={U(r,0x2c422)}")
    return r
def walk():
    if MODE == 'M': h.click('1')
    else: kd(h, 'Control_R'); time.sleep(0.4); ku(h, 'Control_R')
try:
    if BUILD == 'stock': h.boot_to_options(timeout=600)
    h.boot_to_game(MODE, bombers=True, mortars=True, training=False, check=(MACH != 'tt'))
    time.sleep(2); st('idle')
    walk(); t = time.time(); n = 0
    while time.time() - t < 70:
        r = st(f'w{n}'); n += 1
        if n % 3 == 0: shutil.copy(h.shot(), f'{OUT}/w{n:02d}.png')
        if U(r, 0x1efde) != 0: break
        time.sleep(1.5)
    shutil.copy(h.shot(), f'{OUT}/ended.png'); time.sleep(5); shutil.copy(h.shot(), f'{OUT}/ended2.png')
finally:
    h.close()
