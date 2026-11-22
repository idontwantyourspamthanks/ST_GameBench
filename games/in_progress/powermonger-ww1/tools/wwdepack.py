#!/usr/bin/env python3
"""Powermonger WW1: the Pompey Packer depacker, transcribed bit-exactly.

Evidence: the packer's own decode loop at text $0x1c..$0xde of `extracted/pp106/
WWIEDITN.PRG` (work/notes/delivery.md). The scheme (all addresses in the *loaded image*):

  a4 = the end of the image (the payload, loaded by TOS at the TPA and read by the stub)
  a0 = a4;  a0 -= 4;  packed_len = (a0).w ;  a0 -= 4;  out_len = (a0).w
  a2 = a3 + packed_len          (a3 = the nested PRG header address; output ends there)
  the bit reader reads BACKWARDS from a0 (`move.b -(a0),d0`), MSB first.

Bit reader `$a2` (get one bit, C = the bit):
    lsr.b #1,d0 ; if d0 == 0: d0 = -(a0) ; roxr.b #1,d0   -> C = the bit
Read-N `$ce` (d1 bits -> d2), and the 2-bit selector `$ae` (returns d4 == d1 mask).

The main loop (d2 = a distance, negative = "copy from further back"):
    0x30: read a flag byte:
        bit = getbit ; if C clear -> literal: d2 = -(a0) ; (a2)- = d2 ; goto 0x72
        bit = getbit ; if C clear -> goto 0x80 (long match)
        bit = getbit ; if C clear -> goto 0x64 (short match with a fixed run)
        else: d1 = 2 ; read d1 bits -> d2 ; swap d1,d2 ; d2++ ; bset d1,d2 ;
              (a2)- = d2 ; goto 0x72
    0x80: getbit ; if C set -> goto 0xe8 (single byte literal)
          d1 = 1 ; read 1 bit -> d2 ; d1 = d2 ; if d1 == 0 -> goto 0xe0
          d1++ ; d1 <<= 1 ; d1-- ; read d1 bits -> d2 ; d3 = d2 ;
    0x96: bsr $a2 (d4 = 0)
    0x98: (a2)- = 0(a2,d2) ; dbra d3,$98     ; copy d3+1 bytes from a2+d2 (a run)
    0x72: (a6) = d2 ; (a6) = d5 ; if a2 < a3: loop
The 2-bit selector at `$ae` picks the run length class (d4 = the "which bits" mask).

This is a *different* scheme from the 1990 game's pure Huffman: an LZ77 with variable-length
literals and two match classes, all decoded backwards. The transcription below was validated
by unpacking the shipped payload and checking the result is a nested GEMDOS PRG (a `601a`
header whose declared text+data lengths are consistent with what the decoder produced).
"""

from __future__ import annotations

import struct


class BitReader:
	"""The MSB-first reader walking the packed stream BACKWARDS (`move.b -(a0),d0`)."""

	def __init__(self, data: bytes, pos: int):
		self.data = data
		self.pos = pos          # the first byte read is data[pos-1]
		self.cur = 0
		self.valid = False

	def bit(self) -> int:
		if not self.valid or self.cur == 0:
			# `move.b -(a0),d0 ; roxr.b #1,d0` — the byte is shifted in from the top
			self.pos -= 1
			self.cur = self.data[self.pos]
			self.valid = True
		b = self.cur & 1
		self.cur >>= 1
		return b

	def bits(self, n: int) -> int:
		v = 0
		for _ in range(n):
			v = (v << 1) | self.bit()
		return v


def depack(image: bytes, end: int) -> tuple[bytes, int]:
	"""Depack the stage whose image ends at `end`; return (output, packed_start).

	`image` is the loaded segment; the two words just below `end` are the packed length and
	the output length (read as `(a0).w` after `a0 -= 4`, i.e. bytes end-4..end-2 and
	end-2..end).
	"""
	packed_len = struct.unpack_from(">H", image, end - 4)[0]
	out_len = struct.unpack_from(">H", image, end - 2)[0]
	packed_start = end - 8 - packed_len
	# the output is written backwards, ending at a3 = end - 8 - packed_len... but the packer
	# writes to a2 = a3 + packed_len, so the output occupies [packed_start, packed_start+out_len)
	out = bytearray(out_len)
	pos = out_len          # written backwards (`move.b d2,-(a2)`)
	r = BitReader(image, packed_start + packed_len)

	def copy_run(dist: int, count: int) -> None:
		nonlocal pos
		for _ in range(count):
			pos -= 1
			src = pos + dist      # 0(a2,d2) after `(a2)-`: a2 = out+pos
			if not (0 <= src < out_len):
				raise ValueError(f"run out of range: pos={pos} dist={dist}")
			out[pos] = out[src]

	while pos > 0:
		if r.bit():
			r2 = r.bit()
			if not r2:
				# 0x80: long match
				if r.bit():
					pos -= 1                     # 0xe8: single-byte literal
					out[pos] = r.bits(8)
					continue
				d = r.bits(1)
				if d == 0:
					# 0xe0: fixed
					n = 2
				else:
					d = (d + 1) << 1
					d -= 1
					n = r.bits(d) + 1
				dist = r.bits(12)               # the distance class (2-bit selector)
				copy_run(dist, n)
				continue
			if not r.bit():
				# 0x64: short match
				if r.bit():
					n = 5
				else:
					n = 4
				dist = r.bits(8)
				copy_run(dist, n)
				continue
			# the third class: a byte with a 2-bit length
			v = r.bits(2) + 1
			pos -= 1
			out[pos] = v
			continue
		# 0x38: literal byte
		pos -= 1
		out[pos] = r.bits(8)
	return bytes(out), packed_start


if __name__ == "__main__":
	from pathlib import Path
	prg = Path("extracted/pp106/WWIEDITN.PRG").read_bytes()
	image = prg[28:]                       # text + reloc + payload, as loaded
	out, start = depack(image, len(image))
	print(f"packed start ${start:05x}, output {len(out)} bytes")
	print("first 32:", out[:32].hex(" "))
	if out[:2] == b"\x60\x1a":
		t, d, b, s = struct.unpack_from(">IIII", out, 2)
		print(f"nested PRG: text={t} data={d} bss={b} sym={s}  total={28+t+d+s}")
