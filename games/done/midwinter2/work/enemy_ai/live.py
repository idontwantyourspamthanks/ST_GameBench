"""Live NPC observation helpers (Hatari harness). Run from games/in_progress/midwinter2.
usage: python3 work/enemy_ai/live.py <scenario> ...
"""
import sys, time, re, struct
sys.path.insert(0, 'tools')
from mw2harness import Hatari

NPC0 = 0x3532
STRIDE = 0x42

def w16(h, addr, *vals):
    bs = []
    for v in vals:
        bs += [(v >> 8) & 255, v & 255]
    h.debug('w $%x ' % addr + ' '.join('$%02x' % b for b in bs), 0.15)

def w32(h, addr, v):
    w16(h, addr, (v >> 16) & 0xffff, v & 0xffff)

def mem(h, addr, n):
    out = h.debug('m $%x %d' % (addr, n), 0.5)
    got = {}
    for m in re.finditer(r'^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} ?)+)', out, re.M | re.I):
        a = int(m.group(1), 16)
        for i, b in enumerate(m.group(2).split()):
            got[a + i] = int(b, 16)
    return bytes(got.get(addr + i, 0) for i in range(n))

def start(snap='ingame_lobos_foot', mem_kb=2048):
    return Hatari(snapshot=f'work/snapshots/{snap}.sav', memsize_kb=mem_kb)
