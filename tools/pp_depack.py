#!/usr/bin/env python3
"""Unpack a self-extracting RUNME.TOS from PP's HAGA hard-disk conversions.

    python3 tools/pp_depack.py RUNME.TOS out.tos

The packed program's text section is a 230-byte stub. It moves the packed data
to the top of the TPA, then expands it over its own header with a simple LZ:
  0            end
  1..$7F       literal run of n bytes
  $80|n        (bit 6 clear) copy n+3 bytes from 1-byte offset back
  $C0|n        (bit 6 set)   copy n+4 bytes from 2-byte offset back
The output is a complete GEMDOS program (header, text, data, relocations).
Format verified on Midwinter 2's RUNME.TOS (2014-12-15): it unpacks to text $4520,
data 22, bss 111206. Check the stub constants on other games before trusting it.
"""
import re
import struct
import sys


def depack(packed: bytes) -> bytes:
    hdr = struct.unpack(">HIIIIIIH", packed[:28])
    body = packed[28:]
    stub = body[:hdr[1]]
    # The stub has `adda.l #<end>,a0` (end of packed data) and `move.l #<n>,d2` (long count).
    end = struct.unpack(">I", stub[stub.index(b"\xd1\xfc") + 2:][:4])[0]
    n = struct.unpack(">I", stub[stub.index(b"\x24\x3c") + 2:][:4])[0]
    src = body[end - n * 4:end]
    out = bytearray()
    i = 0
    while True:
        c = src[i]; i += 1
        if c == 0:
            break
        if c < 0x80:
            out += src[i:i + c]; i += c
            continue
        cnt = c & 0x3F
        if c & 0x40:
            cnt += 3; off = (src[i] << 8) | src[i + 1]; i += 2
        else:
            cnt += 2; off = src[i]; i += 1
        for _ in range(cnt + 1):
            out.append(out[-off])
    return bytes(out)


if __name__ == "__main__":
    data = depack(open(sys.argv[1], "rb").read())
    open(sys.argv[2], "wb").write(data)
    t, d, b = struct.unpack(">III", data[2:14])
    print(f"unpacked {len(data)} bytes: text ${t:x}, data {d}, bss {b}")
