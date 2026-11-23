#!/usr/bin/env python3
"""Resident game image of the EA WW1 disk, derived from `AUTO\\WW1.PRG` alone (no emulator).

AUTO\\WW1.PRG = a 110-byte loader + a 76 KB stub that (1) copies itself to $514, (2) unpacks the RNC-method-1 variant that follows
(this stub's own decoder, text $d0..$244: no CRC fields, the bit stream is read BACKWARDS from the end of the packed data and the
output is written backwards), (3) treats the result as a TOS program: relocates it by adding the load base $576 and (4) copies
text+data to $576 and jumps there.  This module re-implements steps 2-3 and nothing else; its result is checked byte for byte
against a RAM dump taken at the hand-over in Hatari (`tools/wwpatch.py dumps` / `verify`), which is how it was validated.

    python3 tools/wwdepack.py [AUTO/WW1.PRG]      # prints sizes and md5s
"""
from __future__ import annotations
import hashlib
import struct
import sys
from pathlib import Path

HDR = 0x1C
TEXT_LEN = 0x12A10          # WW1.PRG text size (no data / bss / symbols; relocation table = one zero long)
RNC_OFF = 0x2FE             # text offset of 'RNC\1'
BASE = 0x576                # where the stub copies the relocated nested program (= its RAM address)
IMAGE_END = 0x1D2AE         # end of the resident image (text + data of the nested program); RAM above is cleared by the stub

LIT_BITS = (0x0A, 3, 2, 2)           # stub $19a: literal-run size code, index d1 = 3..0
LIT_BASE = (0x0E, 7, 4, 1)
LEN_BITS = (0x0A, 2, 1, 0, 0)        # stub $1d4: match-length code, index 0..4
LEN_BASE = (0x0A, 6, 4, 3, 2)
OFF_BITS = (0x0B, 4, 7)              # stub $22c: bit counts - 1 (read count + 1 bits)
OFF_BASE = (0x120, 0, 0x20)


class _Bits:
    """The stub's `get bit` ($142): lsl.b #1,d3 ; bne ; (d3 = -(a6) ; roxl.b #1,d3).  Bytes are taken from the end of the data."""

    def __init__(self, data: bytes, end: int):
        self.d, self.p = data, end
        self.b = self._next()

    def _next(self) -> int:
        self.p -= 1
        return self.d[self.p]

    def bit(self) -> int:
        c = self.b >> 7
        self.b = (self.b << 1) & 0xFF
        if self.b:
            return c
        self.b = self._next()
        c2 = self.b >> 7
        self.b = ((self.b << 1) & 0xFF) | c      # roxl.b: the old carry (the sentinel 1) enters at bit 0
        return c2

    def bits(self, n: int) -> int:
        v = 0
        for _ in range(n):
            v = (v << 1) | self.bit()
        return v


def rnc_unpack(packed: bytes, unpacked_len: int) -> bytes:
    """packed = the bytes after the 12-byte header 'RNC\\1 <unpacked.l> <packed.l>'."""
    b = _Bits(packed, len(packed))
    out = bytearray(unpacked_len + 1)               # +1: a zero-offset run reads a3+1 when nothing is written yet (never happens)
    a3 = unpacked_len                               # write pointer, moves down
    while True:
        # literal run ($14c)
        n = 0
        if b.bit():
            if not b.bit():
                n = 1
            else:
                d1 = 3
                while True:
                    d5 = b.bits(LIT_BITS[d1])
                    if d1 == 0 or d5 != (1 << LIT_BITS[d1]) - 1:
                        break
                    d1 -= 1
                n = d5 + LIT_BASE[d1] + 1
            for _ in range(n):
                a3 -= 1
                b.p -= 1
                out[a3] = packed[b.p]
        if b.p <= 0:
            break
        # match length ($1a2)
        k = 0
        while k < 4 and b.bit():
            k += 1
        idx = 4 - k
        d6 = b.bits(LEN_BITS[idx]) + LEN_BASE[idx]
        # match offset ($1de)
        if d6 == 2:
            if b.bit():
                d7 = b.bits(9) + 0x40
            else:
                d7 = b.bits(6)
        else:
            j = 0
            while j < 2 and b.bit():
                j += 1
            idx = 2 - j
            d7 = b.bits(OFF_BITS[idx] + 1) + OFF_BASE[idx]
        d6 -= 1
        a0 = a3 + d7 + d6 if d7 else a3 + 1
        for _ in range(d6 + 1):
            a0 -= 1
            a3 -= 1
            out[a3] = out[a0]
    assert a3 == 0, f"decoder ended at output offset {a3}, expected 0"
    return bytes(out[:unpacked_len])


def nested_prg(prg: bytes) -> bytes:
    text = prg[HDR:HDR + TEXT_LEN]
    assert text[RNC_OFF:RNC_OFF + 4] == b"RNC\x01"
    unp, packed_len = struct.unpack_from(">II", text, RNC_OFF + 4)
    start = RNC_OFF + 12
    return rnc_unpack(text[start:start + packed_len], unp)


def resident_image(prg: bytes) -> bytes:
    """text+data of the nested program, relocated to BASE: what sits at RAM $576.. at the hand-over."""
    n = bytearray(nested_prg(prg))
    assert n[:2] == b"\x60\x1a"
    tl, dl, sl = struct.unpack_from(">I", n, 2)[0], struct.unpack_from(">I", n, 6)[0], struct.unpack_from(">I", n, 14)[0]
    assert struct.unpack_from(">H", n, 0x1A)[0] == 0, "relocation disabled flag set"
    img = bytearray(n[HDR:HDR + tl + dl])
    p = HDR + tl + dl + sl
    first = struct.unpack_from(">I", n, p)[0]
    p += 4
    if first:
        a = first
        while True:
            struct.pack_into(">I", img, a, (struct.unpack_from(">I", img, a)[0] + BASE) & 0xFFFFFFFF)
            while True:
                d = n[p]
                p += 1
                if d == 0:
                    break
                if d == 1:
                    a += 254
                    continue
                a += d
                break
            if d == 0:
                break
    return bytes(img)


if __name__ == "__main__":
    prg = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "extracted/ea/AUTO/WW1.PRG").read_bytes()
    n = nested_prg(prg)
    img = resident_image(prg)
    print(f"nested program {len(n)} B md5 {hashlib.md5(n).hexdigest()}")
    print(f"resident image {len(img)} B (RAM ${BASE:x}..${BASE + len(img):x}) md5 {hashlib.md5(img).hexdigest()}")
