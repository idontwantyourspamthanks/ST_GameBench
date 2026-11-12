#!/usr/bin/env python3
"""reenter2.py BUILD MODE MACHINE: ski, walk 3 s, stop, X (leave), Decisions->Skiing again (x2), walk again: does Stark still move forward?
Also S (snipe) and S (ski) in between on the first pass."""
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
S = Sampler(h, [(0x24fae, 4), (0x13542, 2), (0x12c60, 8), (0x15112, 2), (0x12c98, 2), (0x24fba, 2), (0x1efde, 2), (0x12d5e, 4), (0x13c5a, 2), (0x14efa, 2)])
U = lambda r, a: int.from_bytes(r[a], 'big')
def st(tag):
    r = S(); x, z = int.from_bytes(r[0x12c60][:4], 'big'), int.from_bytes(r[0x12c60][4:], 'big')
    P(f"{tag:12s} vbl={r['vbl']} x={x} z={z} speed={U(r,0x15112)} head={U(r,0x12c98)&0x3ff} btn={U(r,0x24fba)} act={U(r,0x1efde)} lever={s16(int.from_bytes(r[0x24fae][:2],'big'))} st13542={U(r,0x13542):04x} step={r[0x12d5e].hex()} fall13c5a={U(r,0x13c5a)} win14efa={U(r,0x14efa)}")
    return r
def walk():
    if MODE == 'M': h.click('1')
    else: kd(h, 'Control_R'); time.sleep(0.4); ku(h, 'Control_R')
def stop():
    if MODE == 'M': h.click('3')
    else: h.cmd('hatari-event keydown 52'); time.sleep(0.4); h.cmd('hatari-event keyup 52')
try:
    if BUILD == 'stock': h.boot_to_options(timeout=600)
    h.boot_to_game(MODE, check=(MACH != 'tt'))
    time.sleep(2)
    for rnd in range(3):
        r0 = st(f'r{rnd} idle')
        if rnd == 0 and os.environ.get('RE2_NOWALK') == '1':
            h.key('x'); time.sleep(8); st('r0 after X'); h.click_at(SKIING_XY, 10); h.center(); time.sleep(2); continue
        walk()
        for i in range(6):
            time.sleep(1.0); r = st(f'r{rnd} walk{i}')
            if rnd == 2 and i == 2 and os.environ.get('RE2_PUSH') == '1':
                if MODE == 'M': h.rel(0, -120)
                else: kd(h, 'Up'); time.sleep(1.5); ku(h, 'Up')
                P('--- pushed forward (mouse up / stick Up)')
        stop(); time.sleep(3); st(f'r{rnd} stopped')
        if rnd == 0 and os.environ.get('RE2_NOWALK') != '1':           # S: snipe and back
            h.key('s'); time.sleep(4); st('snipe?'); h.key('s'); time.sleep(4); st('ski again')
        h.key('x'); time.sleep(8); st(f'r{rnd} after X')
        shutil.copy(h.shot(), f'/tmp/MW1Ski/re2_{BUILD.split("/")[-1]}_{MODE}_{MACH}_{rnd}.png')
        h.click_at(SKIING_XY, 10); h.center(); time.sleep(2)
    P('end')
finally:
    h.close()
