#!/usr/bin/env python3
"""Delivery gates for the trainer build.  usage: gate.py LABEL GAMEDIR [--megaste] [--neg] [--full]
LABEL names the log/shots.  --neg: negative control (corrupted build): expects NEPF, nothing applied, T/E inert.
--full: the extended player-flow phases (pause, forced life loss, forced door entry)."""
import sys, time, struct, argparse
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from pathlib import Path
from nebulus import Nebulus, TOS
G = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus')
ap = argparse.ArgumentParser(); ap.add_argument('label'); ap.add_argument('game'); ap.add_argument('--megaste', action='store_true')
ap.add_argument('--neg', action='store_true'); ap.add_argument('--full', action='store_true'); a = ap.parse_args()
SH = G / 'work/train/shots/gate'
kw = dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096) if a.megaste else {}
h = Nebulus(workdir=f'/tmp/strun-ntg-{a.label}', game=Path(a.game).resolve(), **kw)
def grab(addr, n):
    p = f'/tmp/ntg_{a.label}.bin'; Path(p).unlink(missing_ok=True)
    h.debug(f"savebin {p} ${addr:x} ${n:x}", 0.6)
    for _ in range(30):
        if Path(p).exists() and Path(p).stat().st_size == n: break
        time.sleep(0.2)
    d = Path(p).read_bytes(); Path(p).unlink(); return d
def W(addr, n=1): return struct.unpack('>%dH' % n, grab(addr, 2 * n))
def S(tag):
    big = grab(0x33900, 0x4c00)      # $33900..$3a2ff: game variables, creature states, timer words ($3ad98 is beyond: second grab), $38498 last ikbd byte
    g = lambda ad, n: big[ad - 0x33900: ad - 0x33900 + 2 * n]
    w = lambda ad, n=1: struct.unpack('>%dH' % n, g(ad, n))
    t = W(0x3ad98, 3); b = grab(0x76c00, 6)
    r = dict(timer=t, states=w(0x3398c, 4), run=w(0x33938)[0], pl=w(0x33a20)[0], tower=w(0x3390c)[0], lastkey='%02x' % big[0x38498 - 0x33900],
             blob='prev=%02x frz=%04x noen=%04x' % (b[0], struct.unpack('>H', b[2:4])[0], struct.unpack('>H', b[4:6])[0]))
    print(f'[{a.label}] {tag}: timer {t} states {r["states"]} run {r["run"]} player {r["pl"]} tower {r["tower"]} | {r["blob"]} | lastkey {r["lastkey"]}  t={time.time()-t0:.0f}s', flush=True)
    return r
FLAG = {'t': 0x76c02, 'e': 0x76c04}
def tap(k, hold=1.0, tries=4):
    """press key k (hold 1.0 s: only the LAST ikbd byte is kept and the loop may stall in death/level sequences), until its blob flag changes"""
    before = grab(FLAG[k], 2)
    for n in range(1, tries + 1):
        h.key(k, hold=hold)
        time.sleep(0.4)
        if grab(FLAG[k], 2) != before:
            print(f'[{a.label}] tap {k}: flag {before.hex()} -> {grab(FLAG[k], 2).hex()} after {n} press(es)', flush=True); return True
    print(f'[{a.label}] tap {k}: flag UNCHANGED {before.hex()} after {tries} presses', flush=True); return False
def P(*x): print(f'[{a.label}]', *x, flush=True)
t0 = time.time()
try:
    if a.megaste:
        ok = h.boot_to_title(timeout=400, space_until=380)
        P('boot_to_title', ok, '%.0fs' % (time.time() - t0))
        time.sleep(2); h.key('Right', hold=0.5); time.sleep(0.5); h.key('Control_R', hold=1.0); time.sleep(4.0)
        ok = bool(h.peekw(Nebulus.TIMER))
    else:
        ok = h.boot_to_game(timeout=120)
    P('boot_to_game ->', ok, '%.0fs' % (time.time() - t0))
    h.shot(str(SH / f'{a.label}_00_tower.png'))
    mk = grab(0xB0020, 8); P('marker $B0020:', mk[:4], 'count $B0024 =', struct.unpack('>H', mk[4:6])[0])
    for ad, n in ((0x3dcf4, 6), (0x3b0a4, 6), (0x3792c, 6)):
        P('site $%x: %s' % (ad, grab(ad, n).hex()))
    P('blob $76c00 (118 B): %s' % grab(0x76c00, 118).hex())
    S('ready')
    # wait until a tower is really running
    for _ in range(40):
        if W(0x33938)[0] == 1 and W(0x33a20)[0] == 0: break
        time.sleep(0.3)
    S('running')
    # --- control: no key, the clock counts (2 quick samples: the unattended frog is killed within seconds with enemies on)
    for i in range(2):
        S(f'control (no key){i}')
    h.shot(str(SH / f'{a.label}_01_control.png'))
    # --- E (pressed asap: otherwise the frog loses its lives unattended)
    tap('e'); S('after E'); h.shot(str(SH / f'{a.label}_02_E_on.png'))
    time.sleep(2.0); S('E on +2s'); h.shot(str(SH / f'{a.label}_02b_E_on.png'))
    for i in range(3):
        time.sleep(1.0); S(f'E on, timer still counting{i}')
    if a.neg:
        h.key('t', hold=1.0); time.sleep(5.0); S('after T +5s'); time.sleep(5.0); S('after T +10s'); h.shot(str(SH / f'{a.label}_03_neg.png'))
        raise SystemExit
    # --- T
    tap('t'); time.sleep(0.5)
    for i in range(5):
        S(f'frozen{i}'); time.sleep(5.0)
    h.shot(str(SH / f'{a.label}_03_T_on.png'))
    tap('t'); time.sleep(0.5)
    for i in range(3):
        S(f'T off, counting{i}'); time.sleep(1.5)
    if not a.full:
        # E off: creatures return
        tap('e'); time.sleep(1.0)
        for i in range(8):
            r = S(f'E off{i}')
            if any(r['states']): break
            time.sleep(2.0)
        time.sleep(2.0); S('E off, +2s'); h.shot(str(SH / f'{a.label}_04_E_off.png'))
        raise SystemExit
    # --- both on, forced life loss
    tap('t'); time.sleep(1.0); S('T+E on')
    h.debug('w $33938 0 0', 0.3); h.debug('w $33a20 0 8', 0.3); h.debug('w $33a1e 0 0', 0.3); h.debug('w $33a18 0 0', 0.3)   # = what $3a744 sets
    for i in range(14):
        time.sleep(1.5); r = S(f'death{i}')
    h.shot(str(SH / f'{a.label}_06_after_death.png'))
    # --- forced door entry with both on
    h.debug('w $33a46 0 1', 0.3); h.debug('w $33a20 0 4', 0.3); h.debug('w $33a1e 0 0', 0.3)
    for i in range(16):
        time.sleep(1.5); r = S(f'door{i}')
        if r['tower'] == 1 and r['run'] == 1: break
    h.shot(str(SH / f'{a.label}_07_next_tower.png'))
    for i in range(3):
        S(f'tower2 frozen{i}'); time.sleep(5.0)
    # --- pause with both ON: taps ignored
    h.key('p', hold=0.3); time.sleep(1.0); S('paused'); h.shot(str(SH / f'{a.label}_05_paused.png')); time.sleep(2.0); S('paused+2s')
    h.key('t', hold=0.3); time.sleep(0.5); h.key('e', hold=0.3); time.sleep(0.5); S('paused, after T and E taps')
    h.key('Control_R', hold=0.5); time.sleep(1.0); S('unpaused by fire'); time.sleep(2.0); S('unpaused+2s')
    # --- E off in tower 2: creatures return
    tap('e'); time.sleep(1.0)
    for i in range(10):
        r = S(f'tower2 E off{i}')
        if any(r['states']): break
        time.sleep(2.0)
    h.shot(str(SH / f'{a.label}_08_tower2_E_off.png'))
finally:
    h.close()
