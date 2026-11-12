#!/usr/bin/env python3
"""Quick snapshot test of the jag set: 1mb_ski_stand_J + live patch, pad on host keys (pad.cfg).
  snap_pad.py [jag|nojag]"""
import sys, time
from jlib import *

which = sys.argv[1] if len(sys.argv) > 1 else 'jag'
h = MW1(snapshot=str(SNAP / '1mb_ski_stand_J.sav'), extra=PAD)
S = Sampler(h, [(0xb6bf0, 8), (0x24f98, 8), (0x24fba, 2), (0x12c98, 2), (0x15110, 2), (0x15112, 2), (0x12d5e, 4),
                (0x1efde, 2), (0x2c324, 4), (0x2c176, 6), (0x24faa, 8), (0x2c29a, 128)])


def show(tag):
    r = S()
    kd_ = [f'{i:02x}' for i, b in enumerate(r[0x2c29a]) if b]
    pj = r[0xb6bf0]
    print(f"{tag:14s} vbl={r['vbl']} PADST={pj[0]:02x} PADJ={pj[1]:02x} BTN={pj[2]:02x} OLD={pj[4:8].hex()} "
          f"vec=({s32(int.from_bytes(r[0x24f98][:4],'big'))/65536:+.1f},{s32(int.from_bytes(r[0x24f98][4:],'big'))/65536:+.1f}) "
          f"$24fba={r[0x24fba].hex()} head={s16(int.from_bytes(r[0x12c98],'big'))} rate={s16(int.from_bytes(r[0x15110],'big'))} "
          f"speed={int.from_bytes(r[0x15112],'big')} step={r[0x12d5e].hex()} menu={r[0x1efde].hex()} key24={r[0x2c324].hex()} "
          f"keydown={kd_}", flush=True)
    return r


try:
    time.sleep(2)
    if which == 'jag':
        apply_live(h, str(HERE / 'jaglive'))
    time.sleep(1.5)
    print('modes $2c176..', S()[0x2c176].hex())
    show('idle')
    for k in ['left', 'right', 'up', 'down', 'B', 'A', 'C', 'opt', 'pause', 'n1', 'n2', 'n3']:
        kd(h, k); time.sleep(1.2); show('hold ' + k); ku(h, k); time.sleep(0.8)
        show('rel ' + k)
finally:
    h.close()
