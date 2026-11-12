#!/usr/bin/env python3
"""Floppy build (MWA in A, MWB in B from power-on, the driveb patch reads the graphics disk from B) -> J mode ski view -> pad test.
  floppy_pad.py [DISKDIR]"""
import shutil, sys, tempfile, time
from jlib import *
import mw1

D = Path(GAME / 'build' / 'jagfl')
MACH = sys.argv[1] if len(sys.argv) > 1 else 'ste'
scratch = Path(tempfile.mkdtemp(prefix='mw1jfl-'))
for s, d in (('MWA.st', 'mwboot.st'), ('MWB.st', 'mwgfx.st'), ('MWC.st', 'mwdata.st')):
    shutil.copy(D / s, scratch / d)
empty = scratch / 'empty'; empty.mkdir()
t0 = time.time()
h = MW1(game_dir=empty, snapshot=None, machine=MACH, memsize_kb=1024 if MACH == 'ste' else 4096, autorun='',
        extra=['--disk-a', str(scratch / 'mwboot.st'), '--disk-b', str(scratch / 'mwgfx.st'), '--fastfdc', 'no'] + PAD)
P = lambda *a: print(*a, flush=True)
S = Sampler(h, [(0xb6bf0, 8), (0x24f98, 8), (0x24fba, 2), (0x12c98, 2), (0x15110, 2), (0x15112, 2), (0x12d5e, 4),
                (0x1efde, 2), (0x2c324, 4), (0x2c176, 6), (0x24faa, 8), (0x24fa2, 8), (0xb2ff8, 4)])


def show(tag):
    r = S(); pj = r[0xb6bf0]
    P(f"{tag:12s} vbl={r['vbl']} PADST={pj[0]:02x} PADJ={pj[1]:02x} BTN={pj[2]:02x} OLD={pj[4:8].hex()} "
      f"vec=({s32(int.from_bytes(r[0x24f98][:4],'big'))/65536:+.1f},{s32(int.from_bytes(r[0x24f98][4:],'big'))/65536:+.1f}) "
      f"$24fba={r[0x24fba].hex()} head={s16(int.from_bytes(r[0x12c98],'big'))} rate={s16(int.from_bytes(r[0x15110],'big'))} "
      f"speed={int.from_bytes(r[0x15112],'big')} step={r[0x12d5e].hex()} menu={r[0x1efde].hex()} key24={r[0x2c324].hex()} "
      f"ptr=({int.from_bytes(r[0x24fa2][:4],'big')>>16},{int.from_bytes(r[0x24fa2][4:],'big')>>16})")
    return r


try:
    ok = h.boot_to_options(timeout=500, first_wait=30)
    P('options reached', ok, f'{time.time() - t0:.0f} s; marker', h.peek(0xb2ff8, 4))
    h.click_at(mw1.MODE_XY['J'])
    P('control mode', h.control_mode())
    for want, xy in ((False, mw1.MORTARS_XY), (False, mw1.BOMBERS_XY)):
        h.click_at(xy)
    h.click_at(mw1.TRAINING_XY)
    h.click_at(mw1.PLAY_XY, 40)
    show('after PLAY')
    h.shot('/tmp/jag_fl_team.png')
    # the pad drives the pointer in the menus exactly as the stick does
    kd(h, 'right'); time.sleep(1.0); show('team right'); ku(h, 'right'); time.sleep(0.5)
    kd(h, 'down'); time.sleep(1.0); show('team down'); ku(h, 'down'); time.sleep(0.5)
    h.click_at(mw1.STARK_XY, 40); h.shot('/tmp/jag_fl_stark.png')
    h.click_at(mw1.DECISIONS_XY, 40); h.shot('/tmp/jag_fl_dec.png')
    h.click_at(mw1.SKIING_XY, 60); h.center()
    P('in_ski', h.in_ski(), f'{time.time() - t0:.0f} s')
    h.shot('/tmp/jag_fl_ski.png')
    r = show('ski')
    assert r[0xb6bf0][0] == 1
    for k in ('left', 'right', 'up', 'down'):
        kd(h, k); time.sleep(1.5); show('hold ' + k); ku(h, k); time.sleep(0.8); show('rel ' + k)
    kd(h, 'B'); time.sleep(3); show('hold B'); ku(h, 'B'); time.sleep(1.0)
    kd(h, 'A'); time.sleep(1.5); show('hold A'); ku(h, 'A'); time.sleep(1.0)
    kd(h, 'n2'); time.sleep(2.0); show('hold 2 (S)'); ku(h, 'n2'); time.sleep(1.0); show('snipe?')
    kd(h, 'n2'); time.sleep(2.0); ku(h, 'n2'); time.sleep(1.0); show('ski again')
    kd(h, 'opt'); time.sleep(1.5); ku(h, 'opt'); time.sleep(2.0); show('after X')
finally:
    h.close()
P(f'total {time.time() - t0:.0f} s')
