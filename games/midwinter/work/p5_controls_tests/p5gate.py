#!/usr/bin/env python3
"""P5 control gates (MW1): log the master heading $12c98 every 0.5 s while an input is applied.

  p5gate.py M|J|K unpatched|patched [out.log]

Restores 1mb_ski_stand / _J / _K, optionally applies p5live (p5_ctl_turn + p5_ctl_buggy) at a flip
breakpoint (never while the CPU runs), then samples (VBL, $12c98, $15110, $24faa, $b3bf0) with ONE
debugger `parse` file per sample.  Rows: wall s, VBL, heading, rate $15110, acc $24faa(hi word), REM.
Input script:
  M: rel(-150,0) at 1 s (10 xdotool steps)
  J: xdotool keydown Left at 1 s (--joy1 keys), keyup at 4 s (3 s held)
  JM: J snapshot, mouse rel(-150,0) (is the mouse live in J mode?)
  K: hatari-event keydown 106 (KP4) at 1 s, keyup at 4 s
"""
import re, sys, time
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/midwinter/tools']
from pathlib import Path
from mw1 import MW1, SNAP

T = Path('/home/ryan/Code/AtariST/gamebench/games/midwinter/work/p5_controls_tests')
FLIP = 0xBD9A


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def apply_live(h, extra_cmds=()):
    import json
    spec = json.loads((T / 'p5live.json').read_text())
    cmds = [f"loadbin {T / 'p5live.img'} ${spec['img_base']:x}"]
    for s in spec['sites']:
        cmds.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s['new'])))
    app = h.R / 'apply.txt'
    cmds += list(extra_cmds)
    app.write_text("\n".join(cmds) + "\nm $12fe2 6\nm $13618 6\nm $b3800 8\n")
    h.debug('b all', 0.3)
    n = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${FLIP:x} :trace :once :file {app}")
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[n:]:
        if time.time() - t > 120:
            raise TimeoutError('apply bp never fired')
        time.sleep(0.3)
    time.sleep(0.5)
    out = h._logtext()[n:]
    print(re.findall(r'^[0-9A-F]{8}: .*$', out, re.M))


def apply_live_pokes_only(h, pk):
    app = h.R / 'apply.txt'
    app.write_text("\n".join(pk) + "\n")
    h.debug('b all', 0.3)
    n = len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${FLIP:x} :trace :once :file {app}")
    t = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[n:]:
        if time.time() - t > 120:
            raise TimeoutError('apply bp never fired')
        time.sleep(0.3)
    time.sleep(0.5)


SAMPLE = None


def sample(h):
    global SAMPLE
    if SAMPLE is None:
        SAMPLE = h.R / 'sample.txt'
        SAMPLE.write_text("e VBL\nm $12c98 2\nm $15110 2\nm $24faa 2\nm $b3bf0 4\n")
    n = len(h._logtext())
    h.cmd(f"hatari-debug parse {SAMPLE}")
    for _ in range(40):
        time.sleep(0.05)
        out = h._logtext()[n:]
        if len(re.findall(r'^[0-9A-F]{8}: ', out, re.M)) >= 4:
            break
    vbl = int(re.findall(r'#(\d+) \(dec\)', out)[-1])
    ms = re.findall(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} )+)', out, re.M)
    d = {int(a, 16): bytes.fromhex(b.replace(' ', '')) for a, b in ms}
    w = lambda a: int.from_bytes(d[a][:2], 'big')
    return vbl, s16(w(0x12c98)), s16(w(0x15110)), s16(w(0x24faa)), int.from_bytes(d[0xb3bf0][:4], 'big', signed=True)


def main():
    mode, which = sys.argv[1].upper(), sys.argv[2]
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else T / f'{which}_{mode}.log'
    snap = {'M': 'stand', 'B': 'stand', 'G': 'stand', 'J': 'stand_J', 'K': 'stand_K', 'JM': 'stand_J', 'KT': 'stand_K'}[mode]
    extra = ['--joy1', 'keys'] if mode in ('J', 'JM') else None
    h = MW1(snapshot=str(SNAP / f'1mb_ski_{snap}.sav'), extra=extra)
    rows = []
    try:
        time.sleep(2)
        # B / G: force the buggy ($1359a) / glider ($1373c) step handler on the ski snapshot (poke test)
        pk = {'B': ["w $12d5e $00 $01 $35 $9a", "w $13598 $01 $04", "w $14774 $00 $00"],
              'G': ["w $12d5e $00 $01 $37 $3c"]}.get(mode, ())
        if which == 'patched':
            apply_live(h, pk)
        elif pk:
            apply_live_pokes_only(h, pk)
        h.center()
        time.sleep(0.5)
        if mode in ('M', 'JM', 'B', 'G'):
            acts = [(1.0, lambda: h.rel(-150, 0))]
        elif mode == 'J':
            acts = [(1.0, lambda: h._xdo('keydown', '--window', h.win, 'Left')),
                    (4.0, lambda: h._xdo('keyup', '--window', h.win, 'Left'))]
        elif mode == 'KT':      # 0.2 s tap of KP4
            acts = [(1.0, lambda: h.cmd('hatari-event keydown 106')),
                    (1.2, lambda: h.cmd('hatari-event keyup 106'))]
        else:
            acts = [(1.0, lambda: h.cmd('hatari-event keydown 106')),
                    (4.0, lambda: h.cmd('hatari-event keyup 106'))]
        t0 = time.time()
        end = 12.0
        nxt = 0.0
        while time.time() - t0 < end:
            t = time.time() - t0
            if acts and t >= acts[0][0]:
                acts.pop(0)[1]()
                print(f't={t:5.2f} ACTION')
                continue
            if t >= nxt:
                r = sample(h)
                rows.append((round(t, 2),) + r)
                nxt += 0.5
            else:
                time.sleep(0.02)
    finally:
        h.close()
    lines = ['wall_s  VBL    heading  rate15110  acc24faa  REM']
    for i, r in enumerate(rows):
        lines.append(f'{r[0]:6.2f} {r[1]:6d} {r[2]:7d} {r[3]:9d} {r[4]:9d} {r[5]:6d}')
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


main()
