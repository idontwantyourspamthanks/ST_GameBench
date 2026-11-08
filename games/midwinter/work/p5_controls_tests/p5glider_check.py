#!/usr/bin/env python3
"""Poke-test of the glider: force the glider step handler $1359a on the ski snapshot,
apply p5live, log at every execution of $13782: VBL, $15110 (turn of this step), $1413a (last value the test
saw), $1354c (exertion) while the mouse moves -150 px.  Also `hit` counts show the glider handler runs."""
import re, sys, time
sys.path[:0] = ['/home/ryan/Code/AtariST/gamebench/tools', '/home/ryan/Code/AtariST/gamebench/games/midwinter/tools']
sys.argv = [sys.argv[0], 'G', 'patched']
exec(open('/home/ryan/Code/AtariST/gamebench/games/midwinter/work/p5_controls_tests/p5gate.py').read().replace('\nmain()\n', '\n'))
which = sys.argv[1]
h = MW1(snapshot=str(SNAP / '1mb_ski_stand.sav'))
try:
    time.sleep(2)
    apply_live(h, ["w $12d5e $00 $01 $37 $3c"])
    cf = h.R / 'bug.txt'
    cf.write_text("e VBL\nm $15110 2\nm $12c9c 2\nm $13b40 2\nm $12c98 2\n")
    h.debug('b all', 0.3)
    n = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $13770 :trace :file {cf}")
    time.sleep(1.5)
    h.center(); h.rel(-150, 0)
    time.sleep(6)
    h.debug('b all', 0.3)
    out = h._logtext()[n:]
    rows = []
    for blk in out.split("Reading debugger commands")[1:]:
        v = re.search(r"#(\d+) \(dec\)", blk)
        m = re.findall(r"^[0-9A-F]{8}: ((?:[0-9a-f]{2} )+)", blk, re.M)
        if v and len(m) >= 4:
            w = lambda x: int.from_bytes(bytes.fromhex(x.replace(' ', ''))[:2], 'big')
            sv = lambda x: w(x) - 0x10000 if w(x) & 0x8000 else w(x)
            rows.append((int(v.group(1)), sv(m[0]), sv(m[1]), w(m[2]), sv(m[3])))
    print('VBL  $15110(turn)  $12c9c(bank)  $13b40  $12c98(heading)   [one row per $13770 = glider step after the turn call]')
    for r in rows:
        print(*r)
    print('glider steps logged:', len(rows))
finally:
    h.close()
