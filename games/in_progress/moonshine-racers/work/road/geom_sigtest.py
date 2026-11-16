"""Reuse robustness: call 1 (speed 0, saves), then call 2 with ONE signature word changed: output must equal stock on the changed input (full path taken)."""
import sys
from rdlib import *
prefix = sys.argv[1]
SITES = [(0x100b4, 0x100c0)]
def masked(m):
    m = bytearray(m)
    for a, b in SITES: m[a:b] = bytes(b - a)
    return bytes(m)
sig = [0x1308,0x130a,0x130c,0x1316,0x1318,0x13ae,0x1bba,0x1bb8,0x23c6,0x102c,0x13a2,0x13a4,0x13a6,0x13a8,0x13aa,0x13ac,0x23bc,0x23be,0x27c8,
       0x1bb0,0x1bb2,0x1bb4,0x1bb6,0x23c0,0x23c2,0x27da,0x27dc,0x27ca,0x27cc,0x27ce,0x27d0,0x27d2,0x27d4]
f = load('grid', 3); ram0 = ram_for(f, 'a')
e = Emu(ram0); apply_live(e, prefix); e.call(0x17c24); e.call(0x100b4); keep = e.rd(0xD0000, 0xB000)
bad = 0; n = 0; reuse_hits = 0
for a in sig:
    for delta in (1, 0x100):
        ram = bytearray(ram0)
        v = int.from_bytes(ram[a:a + 2], 'big'); ram[a:a + 2] = ((v ^ delta) & 0xffff).to_bytes(2, 'big')
        ram = bytes(ram)
        e1 = Emu(ram); e1.call(0x17c24); e1.call(0x100b4); m1 = masked(e1.rd(0, 0xB2700))
        e2 = Emu(ram); apply_live(e2, prefix); e2.wr(0xD0000, keep); e2.call(0x17c24); c = e2.call(0x100b4); m2 = masked(e2.rd(0, 0xB2700))
        n += 1
        if c < 30000: reuse_hits += 1
        if m1 != m2:
            bad += 1; print('MISMATCH sig word', hex(a), delta)
print('sig tests', n, 'mismatches', bad, 'wrongly taken reuse path (cycles<30k):', reuse_hits)
