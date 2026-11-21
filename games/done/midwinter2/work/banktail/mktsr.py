#!/usr/bin/env python3
"""Write a TSR PRG that Ptermres()s KEEP bytes (basepage included): mktsr.py OUT.PRG KEEP_HEX  - stand-in for a resident driver (HDDRIVER, accessories, RAM disks)."""
import struct, sys
out, keep = sys.argv[1], int(sys.argv[2], 16)
code = bytes.fromhex("3f3c0000") + b"\x2f\x3c" + struct.pack(">I", keep) + bytes.fromhex("3f3c00314e41")   # move.w #0,-(sp); move.l #keep,-(sp); move.w #$31,-(sp); trap #1
hdr = struct.pack(">HIIIIIIH", 0x601A, len(code), 0, 0, 0, 0, 0, 0)
assert len(hdr) == 28
open(out, "wb").write(hdr + code)
