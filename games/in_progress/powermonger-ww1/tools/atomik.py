#!/usr/bin/env python3
"""ATOMIK v3.5 (Altair) depacker, transcribed from the stub in WW1.PRG.

The routine is text ``$0c4..$23a``. Bits are pulled MSB-first out of bytes read
backwards from the end of the packed stream, with the packer's refill rule: when
``add.b d7,d7`` clears the buffer, the bit that emptied it is parked in the low
bit of the next byte and the bit actually returned is that byte's high bit
(``move.b -(a6),d7`` / ``addx.b d7,d7``).

Checked against ``work/dumps/c26_image_full.bin`` (the live image at the
hand-over). ``python3 tools/atomik.py`` prints the match; 100.00% is exact.
"""

from __future__ import annotations

import struct


class _Bits:
	"""The ``d7`` shift register at ``$00d8`` / ``$0152`` / the ad-hoc ``add.b`` sites."""

	def __init__(self, buf: bytearray, a6: int):
		self.buf = buf
		self.a6 = a6
		self.d7 = 0
		self.x = 0
		self.c = 0
		self.z = 0

	def prime(self) -> None:
		# ``move.b -(a6),d7`` — loads the first byte raw. X is not used until add.b.
		self.a6 -= 1
		self.d7 = self.buf[self.a6]

	def _add_b(self) -> None:
		self.c = (self.d7 >> 7) & 1
		self.x = self.c
		self.d7 = (self.d7 << 1) & 0xFF
		self.z = self.d7 == 0

	def _refill(self) -> None:
		# ``move.b -(a6),d7`` then ``addx.b d7,d7``.
		# MOVE sets Z from the new byte and leaves X alone; ADDX then folds X in
		# and only clears Z when its result is nonzero.
		self.a6 -= 1
		new = self.buf[self.a6]
		z_after_move = new == 0
		old_x = self.x
		self.c = (new >> 7) & 1
		self.x = self.c
		self.d7 = ((new << 1) & 0xFF) | old_x
		self.z = z_after_move if self.d7 == 0 else False

	def getbit(self) -> int:
		"""One bit, as the ``add.b / bne / refill / bcs`` idiom does it. Returns 0 or 1."""
		self._add_b()
		if self.z:
			self._refill()
		return self.c

	def getbits(self, d6: int) -> int:
		"""``$0152``: ``d6+1`` bits into ``d5``. Z on return is ``d5 == 0``."""
		d5 = 0
		while True:
			self._add_b()
			if self.z:
				self._refill()
			# ``addx.w d5,d5`` — the inserted bit is X. Carry-out replaces X, but the
			# next ``add.b`` overwrites X before anything reads it.
			total = d5 + d5 + self.x
			self.x = 1 if total > 0xFFFF else 0
			self.c = self.x
			d5 = total & 0xFFFF
			if d5 != 0:
				self.z = 0
			if d6 == 0:
				break
			d6 = (d6 - 1) & 0xFFFF
		return d5


def _length_code(bits: _Bits, d3: int) -> int:
	"""The run length at ``$00de``, as ``d2`` after ``$0118``.

	A short code (a 1 bit within ``d3+1`` bits) is just the number of leading
	zeros: ``neg(d5 - d3)`` and it jumps to ``$0114``, past the ``add.w d3,d5``.
	Only the long form (the zero-run ran out) falls into that add.
	"""
	d5 = d3 & 0xFFFF
	phase = "add"
	while True:
		if phase == "add":
			bits._add_b()
			phase = "dbcs"
			continue
		if phase == "dbcs":
			# DBCS: a set carry stops the count; a clear carry decrements d5.
			if bits.c == 0:
				d5 = (d5 - 1) & 0xFFFF
				if d5 != 0xFFFF:
					phase = "add"
					continue
			phase = "beq"
			continue
		if phase == "beq":
			if bits.z:
				bits._refill()
				phase = "dbcs"
				continue
			phase = "bcc"
			continue
		# Carry clear: the zero-run was longer than d3, so the long form, which
		# does add d3 on the way into the copy.
		if bits.c == 0:
			d5 = bits.getbits(3)
			if d5 == 0:
				d5 = bits.getbits(7)
				if d5 == 0:
					d5 = (bits.getbits(0xD) + 0x10E) & 0xFFFF
				else:
					d5 = (d5 + 0xF) & 0xFFFF
			return (d5 + (d3 & 0xFFFF)) & 0xFFFF
		d5 = (d5 - (d3 & 0xFFFF)) & 0xFFFF
		return (-d5) & 0xFFFF


def depack(text: bytes) -> bytes:
	"""Depack one ATOMIK v3.5 linkfile text segment. Returns the plain image."""
	unpacked, packed = struct.unpack_from(">II", text, 0x274)
	# The image is written in place over the packed stream and the (zeroed) BSS.
	# a5 starts at the end of that region; see the stub at text ``$00c4``.
	buf = bytearray(0x278 + unpacked + 4)
	buf[:len(text)] = text
	a0 = 0x27C                       # first packed byte (a6 walks down to here)
	a6 = a0 + packed                 # one past the last packed byte; -(a6) reads it
	a5 = 0x278 + unpacked + 4        # one past the last output byte

	bits = _Bits(buf, a6)
	bits.prime()

	# Distance bases and bit-counts live in the stub at ``$023c`` (not overwritten).
	bases = [struct.unpack_from(">H", buf, 0x23C + 2 * i)[0] for i in range(7)]
	nbits = list(buf[0x24A:0x24A + 8])
	len_tab = [0] * 8
	model = [0] * 16
	have_len = False
	have_model = False

	def byte() -> int:
		bits.a6 -= 1
		return buf[bits.a6]

	def emit(value: int) -> None:
		nonlocal a5
		a5 -= 1
		buf[a5] = value & 0xFF

	def copy_from(dist: int, count: int) -> None:
		nonlocal a5
		src = a5 + (dist - 0x10000 if dist & 0x8000 else dist) + 1
		for _ in range(count):
			src -= 1
			a5 -= 1
			buf[a5] = buf[src]

	def distance(selector: int) -> int:
		extra_bits = nbits[selector]
		if not have_len:
			dist = bits.getbits(extra_bits + 4)
		else:
			d1 = bits.getbits(extra_bits) << 4
			sel2 = bits.getbits(2)
			if sel2 < 7:
				d1 = (d1 & 0xFF00) | ((d1 | len_tab[1 + sel2]) & 0xFF)
				dist = d1
			elif bits.getbits(0) == 0:
				d1 = (d1 & 0xFF00) | ((d1 | len_tab[0]) & 0xFF)
				dist = d1
			else:
				dist = (d1 | (bits.getbits(2) << 1)) & 0xFFFF
		if selector != 0:
			dist = (dist + bases[selector - 1]) & 0xFFFF
		return dist

	def match(selector_bits: int, run: int) -> None:
		# selector_bits is d6, so the selector is selector_bits+1 bits wide.
		copy_from(distance(bits.getbits(selector_bits)), run)

	guard = 0
	while True:
		# ``$01d8`` block header: optional length model, optional byte model, span.
		if bits.getbits(0):
			n = byte()
			len_tab[0] = n
			d1 = 1
			for i in range(1, 8):
				if (d1 & 0xFF) == n:
					d1 += 2
				len_tab[i] = d1 & 0xFF
				d1 += 2
			have_len = True
		else:
			have_len = False
		if bits.getbits(0):
			for i in range(16):
				model[i] = byte()
			have_model = True
		else:
			have_model = False
		d3 = byte()
		span = (byte() << 8) | byte()
		if span & 0x8000:
			span -= 0x10000
		a3 = a5 - span

		while a5 != a3:
			guard += 1
			if guard > unpacked * 4:
				raise RuntimeError(f"depacker did not converge (a5=${a5:x}, a6=${bits.a6:x})")
			if bits.getbit() == 0:
				emit(byte())
				continue
			# ``$00de``: a run length, then either a match or a single patterned byte.
			d2 = _length_code(bits, d3)
			if d2 != 0:
				match(2, d2 + 2)
				continue
			if bits.getbit() == 0:
				match(1, 2)
				continue
			d5 = bits.getbits(3)
			if have_model:
				emit(model[d5])
			else:
				prev = buf[a5]
				delta = d5 & 0xFF
				if delta & 0x08:
					delta = (delta + 0xF0) & 0xFF
				emit((prev - delta) & 0xFF)
		if bits.a6 == a0:
			break

	if a5 != a0:
		raise RuntimeError(f"output stopped at ${a5:x}, image starts at ${a0:x}")
	return bytes(buf[a0:a0 + unpacked])


def _reloc_offsets(image: bytes) -> tuple[int, list[int]]:
	"""GEMDOS reloc offsets, relative to the nested program's text."""
	text_len = struct.unpack_from(">I", image, 2)[0]
	at = 28 + text_len
	first = struct.unpack_from(">I", image, at)[0]
	offs = [first]
	pos = first
	i = at + 4
	while i < len(image):
		b = image[i]
		i += 1
		if b == 0:
			break
		if b == 1:
			pos += 254
			continue
		pos += b
		offs.append(pos)
	return text_len, offs


def _with_relocs(image: bytes, delta: int) -> bytes:
	_, offs = _reloc_offsets(image)
	out = bytearray(image)
	for pos in offs:
		at = 28 + pos
		val = struct.unpack_from(">I", out, at)[0]
		struct.pack_into(">I", out, at, (val + delta) & 0xFFFFFFFF)
	return bytes(out)


# The live capture is not the raw depack buffer. It starts at the game entry
# (`lea $d8c2`, image offset $104) and the stub has already added the load
# address to the GEMDOS relocs. Everything up to the last real text byte matches
# that; the capture then runs off into memory the depacker left as zero padding.
GAME_ENTRY = 0x104


def check_capture(image: bytes, capture: bytes) -> None:
	if image[GAME_ENTRY:GAME_ENTRY + 6] != bytes.fromhex("43f90000d8c2"):
		raise SystemExit("depacked image has no game entry at $104")
	text_len, offs = _reloc_offsets(image)
	text_end = 28 + text_len
	in_view = [p for p in offs if 28 + p >= GAME_ENTRY]
	if not in_view:
		raise SystemExit("no relocation falls inside the captured window")
	at = 28 + in_view[0]
	file_val = struct.unpack_from(">I", image, at)[0]
	cap_at = at - GAME_ENTRY
	cap_val = struct.unpack_from(">I", capture, cap_at)[0]
	delta = (cap_val - file_val) & 0xFFFFFFFF
	fixed = _with_relocs(image, delta)
	last = max(i for i in range(GAME_ENTRY, text_end) if image[i])
	span = last - GAME_ENTRY + 1
	got = fixed[GAME_ENTRY:GAME_ENTRY + span]
	ref = capture[:span]
	same = sum(a == b for a, b in zip(got, ref))
	print(f"unpacked {len(image)} bytes")
	print(f"vs the live capture: {same}/{span} identical ({100 * same / span:.2f}%)")
	if got != ref:
		for i, (a, b) in enumerate(zip(got, ref)):
			if a != b:
				raise SystemExit(f"first mismatch at capture[{i}]: got {a:02x} ref {b:02x}")
		raise SystemExit("capture comparison length mismatch")
	print(f"relocation delta ${delta:x}, {len(offs)} relocs, compared through the last text byte")


if __name__ == "__main__":
	from pathlib import Path
	prg = Path("extracted/cobra26/WW1.PRG").read_bytes()
	text = prg[28:28 + 61622]
	img = depack(text)
	ref_path = Path("work/dumps/c26_image_full.bin")
	if not ref_path.exists():
		print(f"unpacked {len(img)} bytes")
		raise SystemExit(f"no capture at {ref_path}")
	check_capture(img, ref_path.read_bytes())
