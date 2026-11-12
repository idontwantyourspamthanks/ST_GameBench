#!/usr/bin/env python3
"""Does Stark move forward on skis?  fwd.py BUILD MODE [MACHINE] [TAG]
  BUILD: path of an HD build dir (or 'stock' = the game dir as shipped), MODE: M | J | K
  MACHINE: ste (1 MB TOS 1.62, default) | st | megast | megaste | tt | falcon
Cold boot -> Options -> mode -> PLAY -> Team -> Stark -> Decisions -> Skiing, then the forward control of the manual:
  M: left click = walk, then mouse back / forward on the lever;  J: fire (Control_R) = walk, then stick Down/Up;
  K: '<' key = walk, then KP2 / KP8.  Then right button / '>' to stop.  One row per ~1 s: VBL, x, z, speed, lever, buttons.
"""
import re, sys, time
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/work/..', '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/work/jagpad']
from jlib import *

BUILD = sys.argv[1]
MODE = sys.argv[2].upper()
MACH = sys.argv[3] if len(sys.argv) > 3 else 'ste'
cfg = {'ste': dict(machine='ste', memsize_kb=1024), 'st': dict(machine='st', memsize_kb=1024),
       'megast': dict(machine='megast', memsize_kb=1024), 'megaste': dict(machine='megaste', memsize_kb=4096),
       'megaste1': dict(machine='megaste', memsize_kb=1024),
       'tt': dict(machine='tt', memsize_kb=4096, extra=['--mmu', 'true']),
       'falcon': dict(machine='falcon', memsize_kb=4096)}[MACH]
import os, shutil
from pathlib import Path as _P
extra = (cfg.pop('extra', None) or []) + ['--joy1', 'keys']
if MACH == 'tt' and os.environ.get('FWD_RGB') != '1':      # dist/run_tt.sh: --monitor vga --cpuclock 32 --mmu true
    extra += ['--monitor', 'vga', '--cpuclock', '32']
extra += os.environ.get('FWD_EXTRA', '').split()
gd = str(GAME) if BUILD == 'stock' else BUILD
WN = int(os.environ.get('FWD_WALK', '8'))
P = lambda *a: print(*a, flush=True)
t0 = time.time()
VHD = os.environ.get('FWD_VHD')      # a drive image (ACSI + HDDRIVER, the user's boot path); BUILD is then just a label
if VHD:
    sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
    import tempfile, shutil
    from pathlib import Path as _P
    import test_hd_image as thi
    _R = _P(tempfile.mkdtemp(prefix='strun-'))
    _src = thi.test_image(_P(VHD), _P(tempfile.mkdtemp(prefix='hdsrc-')) / 'test.img', 'mw1', original=os.environ.get('FWD_ORIG') == '1')
    shutil.copy(_src, _R / 'hd.img')
    h = MW1(workdir=str(_R), files=[], autorun='', extra=thi.hd_args(_R) + extra, **cfg)
    thi.wait_drive_c(h)
else:
    h = MW1(snapshot=None, game_dir=gd, extra=extra, **cfg)
# x,z  speed($15112)  heading($12c98)  turn($15110)  btn($24fba)  Y-lever/acc long($24fae)  X acc($24faa)  $152a8  $13548  step ptr  mode flags  action($1efde) MWPO
S = Sampler(h, [(0x12c60, 8), (0x15112, 2), (0x12c98, 2), (0x15110, 2), (0x24fba, 2), (0x24fae, 4), (0x24faa, 4), (0x152a8, 2),
                (0x13548, 2), (0x12d5e, 4), (0x2c176, 6), (0x1efde, 2), (0xb2ff8, 4), (0x24f40, 8)])
U = lambda r, a: int.from_bytes(r[a], 'big')
last = {}


def row(tag):
    r = S()
    x, z = U(r, 0x12c60) >> 32, U(r, 0x12c60) & 0xffffffff
    x, z = int.from_bytes(r[0x12c60][:4], 'big'), int.from_bytes(r[0x12c60][4:], 'big')
    P(f"{tag:14s} vbl={r['vbl']} x={x} z={z} speed={U(r,0x15112)} head={s16(U(r,0x12c98))} turn={s16(U(r,0x15110))} btn={U(r,0x24fba)} "
      f"leverY={s16(int.from_bytes(r[0x24fae][:2],'big'))} accX={s16(int.from_bytes(r[0x24faa][:2],'big'))} v152a8={U(r,0x152a8)} f13548={U(r,0x13548):04x} "
      f"step={r[0x12d5e].hex()} step24f40={r[0x24f40].hex()} flags={r[0x2c176].hex()} act={U(r,0x1efde)} mwpo={r[0xb2ff8]}")
    last[tag] = (x, z, U(r, 0x15112), r['vbl'])
    return r


SHOTS = os.environ.get('FWD_SHOTS') == '1'
SHOTDIR = _P('/tmp/MW1Ski/shots_' + os.environ.get('FWD_TAG', 'x')); 
if SHOTS: SHOTDIR.mkdir(parents=True, exist_ok=True)


def run(seconds, tag, every=1.0):
    t = time.time()
    n = 0
    while time.time() - t < seconds:
        row(f'{tag}{n}')
        if SHOTS and tag in ('idle', 'walk', 'fwd'):
            shutil.copy(h.shot(), SHOTDIR / f'{tag}{n:02d}.png')
        n += 1
        time.sleep(every)


def xz(tag):
    return last[tag][0], last[tag][1]


try:
    P('config', BUILD, MODE, MACH, cfg, extra)
    if BUILD in ('stock', 'vhdorig'):
        P('stock boot to options:', h.boot_to_options(timeout=600))
    if os.environ.get('FWD_DEF') == '1':     # Game Options exactly as shipped: Mortars ON, Bombers ON, Training OFF (what a user gets by just clicking PLAY)
        h.boot_to_game(MODE, bombers=True, mortars=True, training=False, check=(MACH not in ('tt', 'falcon')))
    else:
        h.boot_to_game(MODE, check=(MACH not in ('tt', 'falcon')))
    P(f'boot_to_game {MODE} ok in {time.time() - t0:.0f} s; control mode {h.control_mode()}; mwpo {h.peek(0xb2ff8, 4)!r}')
    time.sleep(2)
    row('idle')
    run(3, 'idle', 1.0)
    # ---------- walk start with the left-button equivalent
    if MODE == 'M':
        h.click('1')
    elif MODE == 'J':
        kd(h, 'Control_R'); time.sleep(0.5); ku(h, 'Control_R')
    else:
        h.cmd('hatari-event keydown 51'); time.sleep(0.5); h.cmd('hatari-event keyup 51')
    P('--- walk started (left button)')
    run(WN, 'walk', 1.0)
    # ---------- lever: back then forward
    if MODE == 'M':
        h.rel(0, 100); time.sleep(0.2)
    elif MODE == 'J':
        kd(h, 'Down'); time.sleep(2.0); ku(h, 'Down')
    else:
        h.cmd('hatari-event keydown 110'); time.sleep(2.0); h.cmd('hatari-event keyup 110')
    P('--- lever pulled back (mouse down / stick Down / KP2)')
    run(3, 'back', 1.0)
    if MODE == 'M':
        h.rel(0, -100); time.sleep(0.2)
    elif MODE == 'J':
        kd(h, 'Up'); time.sleep(2.0); ku(h, 'Up')
    else:
        h.cmd('hatari-event keydown 104'); time.sleep(2.0); h.cmd('hatari-event keyup 104')
    P('--- lever pushed forward (mouse up / stick Up / KP8)')
    run(4, 'fwd', 1.0)
    # ---------- stop
    if MODE == 'M':
        h.click('3')
    elif MODE == 'J':
        h.cmd('hatari-event keydown 52'); time.sleep(0.4); h.cmd('hatari-event keyup 52')
    else:
        h.cmd('hatari-event keydown 52'); time.sleep(0.4); h.cmd('hatari-event keyup 52')
    P('--- stop (right button / ">")')
    run(3, 'stop', 1.0)
    # summary
    LASTWALK = max((k for k in last if k.startswith('walk')), key=lambda k: int(k[4:]))
    w0, w1 = xz('walk0'), xz(LASTWALK)
    moved = max(abs(w1[0] - w0[0]), abs(w1[1] - w0[1]))
    P(f"SUMMARY build={BUILD.split('/')[-1]} mode={MODE} machine={MACH}: walk0 x,z={w0} walkL x,z={w1} |delta|max={moved} speed(walkLast)={last[LASTWALK][2]} -> forward={'YES' if moved > 50 and last[LASTWALK][2] > 0 else 'NO'}")
    h.shot(f'/tmp/MW1Ski/fwd_{BUILD.split("/")[-1]}_{MODE}_{MACH}.png')
finally:
    h.close()
P(f'total {time.time() - t0:.0f} s')
