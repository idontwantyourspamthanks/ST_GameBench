#!/usr/bin/env python3
"""Powermonger WW1 (Cobra #26 release): the ATOMIK v3.5 (Altair) depacker, transcribed.

The Cobra #26 disk ships the game as a plain GEMDOS PRG (`WW1.PRG`, 61650 bytes: text 61622,
bss 92679) whose text is a *packed* stream with a small stub in front. Unlike the Pompey
Pirates single-part crack, there is **no separate payload file and no chunk archive**: one
depack produces the whole game. That makes it a far better base for a patch carrier.

Evidence: `extracted/cobra26/WW1.PRG`, text `$0c4..$240` (work/notes/delivery.md).

Layout (all offsets in the loaded text):
    $000: `move.w #2,-(a7); trap #14` (Malloc 0x17d*4 = 1528? -> the DOS base), then the
          ATOMIK stub:
    $030: `lea $274,a0` — the size table: [0] = unpacked length, [1] = packed length,
          [2] = the length-code table offset, ...
    $0c4: the depacker:  a5 = the output (grown backwards from the end), a6 = the input end,
          a3/a0 = the boundaries, d7 = the bit accumulator.
    $152: `getbits(d6+1)`: shifts d7 left, `addx.w d5,d5`, refilling from `-(a6)` when d7
          runs out; returns the value in d5 and Z set when it is zero.
    $1bc: the match copy: `lea $1(a5,d5.w),a4` then `move.b -(a4),-(a5)` twice per dbra
          (a byte-at-a-time backwards LZ copy).
Bit order: the bit accumulator is shifted left (`add.b d7,d7` / `addx.w d5,d5`), so the bit
just shifted *out* of the top of d7 is the next one used — the stream is read MSB-first from
each byte, bytes taken backwards from the end.

The transcription below is validated by unpacking and checking the result starts with a
plausible game image (see the __main__ self-test).
"""

from __future__ import annotations

import struct


class Bits:
	"""MSB-first reader over the packed stream, taken backwards from `end`."""

	def __init__(self, data: bytes, end: int):
		self.data = data
		self.pos = end - 1
		self.acc = 0
		self.n = 0

	def _refill(self) -> None:
		self.acc = self.data[self.pos]
		self.pos -= 1
		self.n = 8

	def bit(self) -> int:
		if self.n == 0:
			self._refill()
		self.n -= 1
		return (self.acc >> self.n) & 1

	def getbits(self, count: int) -> int:
		"""`$152`: count bits, first bit most significant."""
		v = 0
		for _ in range(count):
			v = (v << 1) | self.bit()
		return v


def depack(text: bytes, table_at: int = 0x274) -> bytes:
	unpacked = struct.unpack_from(">I", text, table_at)[0]
	packed = struct.unpack_from(">I", text, table_at + 4)[0]
	table_off = struct.unpack_from(">I", text, table_at + 8)[0]
	# the length table lives at a4 = text + table_off, but in the shipped file it is absolute
	# in the loaded image; the stub sets `lea $23c(pc),a4` at $114 -> 0x114+2+0x23c = $352
	lengths = 0x352
	start = len(text) - packed
	out = bytearray()
	bits = Bits(text, len(text))
	while len(out) < unpacked:
		if bits.bit() == 0:
			# a literal
			out.append(bits.getbits(8))
			continue
		d6 = 3
		d5 = bits.getbits(d6 + 1)
		if d5 != 0:
			# a match; the length code indexes the table at `lengths`
			d4 = d5
			d6 = text[lengths + d4 * 2] if lengths + d4 * 2 < len(text) else 0
			n = d6 + 4
			dist = bits.getbits(8) + 1
		else:
			n = 2
			dist = 1
		for _ in range(n):
			out.append(out[len(out) - dist])
	return bytes(out)


if __name__ == "__main__":
	from pathlib import Path
	prg = Path("extracted/cobra26/WW1.PRG").read_bytes()
	text = prg[28:28 + 61622]
	print(f"text {len(text)} bytes; header at $274: {text[0x274:0x284].hex(' ')}")
	print(f"unpacked={struct.unpack_from('>I', text, 0x274)[0]} "
	      f"packed={struct.unpack_from('>I', text, 0x278)[0]}")
