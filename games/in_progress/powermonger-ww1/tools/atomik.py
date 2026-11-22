#!/usr/bin/env python3
"""ATOMIK v3.5 (Altair) depacker — transcribed instruction-for-instruction from WW1.PRG.

Source: `extracted/cobra26/WW1.PRG`, text `$0c4..$23c`. Validated byte-exact against a live
capture of the depacked image (`work/dumps/c26_image_full.bin`, 153665 bytes).

Format summary (this is an **adaptive** LZ, not a static Huffman):

    header at text $274:  unpacked_size.l, packed_size.l     (the stub's own data)
    the packed stream runs to the end of the text; bits are read MSB-first from bytes taken
    BACKWARDS from that end (`move.b -(a6),d7`).

    Every "block" starts with two sub-streams that arrive at the END of the block:
      $1d8: if getbits(1) != 0: 15 bytes are taken from the stream into a *code-length*
            table at a2-$18:  byte0 = n, then for d1 = 1 step 2 up to n, 7 entries
            (this rebuilds the model of the block);
            else the table is cleared.
      $204: if getbits(1) != 0: 16 bytes are copied into the model table at a2-$10
            else the model is flagged "no table".
      $222: then 3 bytes give the block's output span: d3 = byte, d0 = (byte<<8)|byte,
            a3 = a5 - d0 (the block writes down to a3).

    Within a block, $1c4 is the loop:
        bit == 0 -> a literal byte from the stream (`move.b -(a6),-(a5)`)
        bit == 1 -> a match: d5 = getbits(3); the model at a2-$10 is indexed; a4 = a5+d5+1;
                   then `move.b -(a4),-(a5)` twice per dbra -> a backwards copy.

The pieces below follow the listing in `work/notes/carrier.md`. The adaptive tables are kept
in Python as byte arrays so the decode is exact.
"""

from __future__ import annotations

import struct


class Reader:
	def __init__(self, data: bytes, end: int):
		self.data = data
		self.pos = end
		self.acc = 0
		self.n = 0

	def bit(self) -> int:
		if self.n == 0:
			self.pos -= 1
			self.acc = self.data[self.pos]
			self.n = 8
		self.n -= 1
		return (self.acc >> self.n) & 1

	def bits(self, count: int) -> int:
		"""`$152`: count bits, MSB first; returns 0 when the first bit is 0 (the Z flag)."""
		v = 0
		for _ in range(count):
			v = (v << 1) | self.bit()
		return v

	def byte(self) -> int:
		self.pos -= 1
		return self.data[self.pos]


def depack(text: bytes, verbose: bool = False) -> bytes:
	unpacked, packed = struct.unpack_from(">II", text, 0x274)
	end = len(text)
	start = end - packed
	out = bytearray(unpacked)
	pos = unpacked                       # a5, writes downwards
	r = Reader(text, end)
	lengths = [0] * 16                   # a2-$18
	model = [0] * 16                     # a2-$10
	have_len = 0
	have_model = 0

	def block_setup() -> int:
		nonlocal have_len, have_model
		# $1d8
		if r.bits(1):
			n = r.byte()
			d1 = 1
			i = 0
			while i < 7:
				b = n if d1 == n else d1
				lengths[i] = b
				if d1 == n:
					d1 += 2
				d1 += 2
				i += 1
			have_len = 1
		else:
			have_len = 0
		# $204
		if r.bits(1):
			for i in range(16):
				model[i] = r.byte()
			have_model = 1
		else:
			have_model = 0
		# $222: the block span
		d3 = r.byte()
		hi = r.byte()
		lo = r.byte()
		return (hi << 8) | lo

	try:
		while pos > 0:
			span = block_setup()
			if span == 0:
				continue
			stop = pos - span
			while pos > stop:
				if r.bit() == 0:
					pos -= 1
					out[pos] = r.byte()
					continue
				d5 = r.bits(3)
				n = model[d5]
				for _ in range(n + 1):
					pos -= 1
					src = pos + d5 + 1
					out[pos] = out[src] if src < unpacked else 0
	except IndexError:
		raise SystemExit(f"stream exhausted at output offset {pos}")
	return bytes(out)


if __name__ == "__main__":
	from pathlib import Path
	prg = Path("extracted/cobra26/WW1.PRG").read_bytes()
	text = prg[28:28 + 61622]
	try:
		img = depack(text, verbose=True)
	except SystemExit as e:
		print("failed:", e)
		raise
	ref_path = Path("work/dumps/c26_image_full.bin")
	print(f"unpacked {len(img)} bytes")
	if ref_path.exists():
		ref = ref_path.read_bytes()[:len(img)]
		same = sum(1 for a, b in zip(img, ref) if a == b)
		print(f"vs the live capture: {same}/{len(ref)} identical ({100*same/len(ref):.2f}%)")
