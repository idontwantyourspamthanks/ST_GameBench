#!/usr/bin/env python3
"""Unpack the 'FIRE' files and packed programs of the Paper Bag / Replicants cracks (a Pack-Ice 2.x style backward LZ).

    python3 tools/fire_depack.py FILE out.bin          # a stand-alone 'FIRE' file (magic, packed length, original length, stream)
    python3 tools/fire_depack.py --prg FILE out.bin    # a Replicants-style packed program (HUNTER.PRG)

The bit stream is read BACKWARDS from the end of the packed data and the output is written backwards from its end.  This is
a transliteration of the 68000 routine at $5a6 of Paper Bag's HUNTER.TOS (and $d4 of Replicants' HUNTER.PRG, the same
routine with other registers); it was checked against the RAM that the real routine produced in Hatari (the unpacked game
of Paper Bag's file 800 equals the RAM at $800: 71684 bytes, differences only where the cracker's own patches write).

Stream layout of a FIRE file: 'FIRE', packed length (the whole file, big-endian long), original length, then the bits.
Decoder (bit = one bit of the stream, MSB first; the byte before the stream end holds a sentinel, see _Bits):
  bit 1:   a literal run follows: 0 -> 1 byte; 1 -> counts from 4 tables (2 bits max 3 ... 14 bits, +1/+4/+7/+14 base)
  then, unless the output is complete, a match code: 2 bits 0..3 choose "long match", "byte of 8 bits" (offset only),
  and the three short forms; offsets are 4 / 8 / 12 / 16 bit classes (+0 / +16 / +$110 / +$1110), lengths 2..257.
Only the observable behaviour matters here; the exact bit semantics follow the code below, which is the authority.
"""
from __future__ import annotations

import struct
import sys

_TAB = bytes.fromhex(
    "03ff0009" "00070002" "00030001" "00030001"            # -16..-1: 4 longs (high word = max value, low word = bit count - 1), read backwards
    "0000000e" "00000007" "00000004" "00000001"            # +0..+15: base values of the literal-run classes
    "00030000" "00070010" "000b0110" "000f1110"            # +16: offset pairs (bit count - 1, base)
    "00030005" "00050015" "00070055")                      # +32: length pairs
_A3 = 16


def ice(mem: bytearray, src: int, dst: int, start: int) -> None:
    """mem: memory image.  src = end of the packed stream, dst = end of the output, start = lowest output address."""
    d7 = [mem[src - 1]]
    a2 = [src - 1]
    a4 = [dst]

    def bit() -> int:
        v = d7[0] << 1
        c = (v >> 8) & 1
        d7[0] = v & 0xFF
        if d7[0] == 0:                                   # sentinel shifted out: refill, X (= c) becomes the new sentinel
            a2[0] -= 1
            v = (mem[a2[0]] << 1) + c
            c = (v >> 8) & 1
            d7[0] = v & 0xFF
        return c

    def bits(n: int) -> int:                             # n + 1 bits (the 68000 dbra counter)
        d1 = 0
        for _ in range((n & 0xFFFF) + 1):
            d1 = ((d1 << 1) | bit()) & 0xFFFF
        return d1

    def sw(o: int) -> int:
        return struct.unpack(">h", _TAB[o:o + 2])[0]

    def s658(d1: int) -> int:
        d1 = (d1 * 4) & 0xFFFF
        d0 = sw(_A3 + 0x10 + d1)
        d5 = sw(_A3 + 0x10 + d1 + 2)
        return (bits(d0) + d5) & 0xFFFFFFFF

    def s654() -> int:
        return s658(bits(1))

    def s648():
        d1 = (bits(1) - 1) & 0xFFFF
        if d1 & 0x8000:
            return 0, 0
        return 0xFFFF, s658(d1)

    def put(b: int) -> None:
        a4[0] -= 1
        mem[a4[0]] = b & 0xFF

    def copy(d1: int, d0: int) -> None:
        a0 = (a4[0] + 2 + d1 + (d0 if d0 < 0x8000 else d0 - 0x10000)) & 0xFFFFFFFF
        a0 -= 1
        put(mem[a0])
        for _ in range((d0 & 0xFFFF) + 1):
            a0 -= 1
            put(mem[a0])

    while True:
        if bit():
            d1 = 0
            if bit():
                a0 = _A3
                d3 = 3
                while True:
                    a0 -= 4
                    d0 = struct.unpack(">I", _TAB[a0:a0 + 4])[0]
                    d1 = bits(d0 & 0xFFFF)
                    if d1 != d0 >> 16:
                        break
                    d3 -= 1
                    if d3 < 0:
                        break
                d1 += struct.unpack(">I", _TAB[a0 + 16:a0 + 20])[0]
            for _ in range((d1 & 0xFFFF) + 1):
                a2[0] -= 1
                put(mem[a2[0]])
        if a4[0] <= start:
            return
        d1 = bits(1) - 1
        if d1 < 0:
            d1 = bits(1) - 1
            if d1 < 0:
                v = s654()
                if v == 0:
                    continue
                d0 = mem[a4[0]]
                while True:
                    for _ in range((v & 0xFFFF) + 1):
                        put(d0)
                    v = (v - 0x10000) & 0xFFFFFFFF
                    if v & 0x80000000:
                        break
                continue
            d1 = (d1 * 4) & 0xFFFF
            d0 = sw(_A3 + 0x20 + d1)
            d2 = sw(_A3 + 0x20 + d1 + 2)
            d1 = bits(d0)
            d2 = (d2 + d1) & 0xFFFF
            d1 = s654()
            copy(d1, (d2 - 2) & 0xFFFF)
        elif d1 == 0:
            d1 = bits(7)
            copy(d1, 0)
        else:
            d1 -= 1
            if d1 == 0:
                d0, d1 = s648()
                if d0 == 0:
                    put(0)
                else:
                    copy(d1, 1)
            elif not bit():
                d1 = bits(2)
                put(1 << (d1 & 31))
            elif not bit():
                d0, d1 = s648()
                if d0 == 0:
                    put(mem[a4[0]])
                else:
                    copy(d1, 2)
            else:
                d0, d1 = s648()
                if d0 == 0:
                    put(0xFF)
                else:
                    copy(d1, 3)


def depack_fire(data: bytes) -> bytes:
    """A stand-alone 'FIRE' file -> the original bytes."""
    if data[:4] != b"FIRE":
        raise ValueError("not a FIRE file")
    plen, olen = struct.unpack(">II", data[4:12])
    base, dest = 0x100, 0x100 + 0x600 + 0                # same shape as the loader: output above the packed data start
    mem = bytearray(dest + olen + plen + 0x1000)
    mem[base:base + len(data)] = data
    ice(mem, base + plen, dest + olen, dest)
    return bytes(mem[dest:dest + olen])


def depack_prg(data: bytes) -> bytes:
    """Replicants-style packed program: the stub holds `FIRE`, packed length, original length at a fixed spot; returns the
    unpacked program image (a normal GEMDOS program: header, text, ...)."""
    i = data.find(b"FIRE", 0x28)
    plen, olen = struct.unpack(">II", data[i + 4:i + 12])
    # a0 (start of the output) is the `lea x(pc),a0` of the stub; the packed data END is a0 + (plen_const) - see the stub
    a0 = i + 0x78                                        # Replicants HUNTER.PRG: FIRE at $230, a0 = $2a8
    mem = bytearray(a0 + olen + 0x1000)
    mem[:len(data)] = data
    ice(mem, i + plen, a0 + olen, a0)
    return bytes(mem[a0:a0 + olen])


if __name__ == "__main__":
    args = sys.argv[1:]
    prg = "--prg" in args
    args = [a for a in args if a != "--prg"]
    raw = open(args[0], "rb").read()
    out = (depack_prg if prg else depack_fire)(raw)
    open(args[1], "wb").write(out)
    print(f"unpacked {len(out)} bytes")
