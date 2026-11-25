#!/usr/bin/env python3
"""Pasti .stx -> plain .st for a normal 1-side/80-track/10-sector FAT12 disk (the EA WW1 original).
Sector data is taken by (track, sector id); tracks 80-83 carry raw track images and no sectors (ignored).
Result is a 409600-byte image Hatari boots directly (verified: WW1 title reached)."""
import struct, sys
d = open(sys.argv[1], 'rb').read()
off, sec = 16, {}
for _ in range(d[10]):
    size, fuzz, sc, flags, tlen, tn, typ = struct.unpack('<IIHHHBB', d[off:off+16]); rec = d[off:off+size]
    base = 16 + 16*sc + fuzz
    for s in range(sc):
        doff, bp, rt, idt, idh, idn, ids, c1, c2, fl, rs = struct.unpack('<IHHBBBBBBBB', rec[16+16*s:32+16*s])
        assert ids == 2 and fl == 0, (tn, idn, ids, fl)
        sec[(tn & 0x7f, idn)] = rec[base+doff:base+doff+512]
    off += size
open(sys.argv[2], 'wb').write(b''.join(sec[(t, n)] for t in range(80) for n in range(1, 11)))
