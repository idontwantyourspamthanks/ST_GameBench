#!/usr/bin/env python3
"""MSA floppy image to raw .st converter.

Standard MSA: 10-byte header (ID $0143, cylinders, sides-1, start cyl, end cyl).
The Pompey Pirates / Cobra / Fuzion menu disks use a variant header (ID $0E0F):
sectors per track, sides-1, start cyl, end cyl; cylinders are implied by start..end.
Both are followed per track-side by a word = compressed byte length, then RLE data:
$E5 <byte> <word count> = byte repeated count times; $E5 $E5 $0000 = one literal $E5.
"""

import argparse
import sys
from pathlib import Path


def unrle(data: bytes, out_len: int) -> bytes:
	out = bytearray()
	i = 0
	while i < len(data):
		b = data[i]
		if b == 0xE5:
			if i + 3 >= len(data):
				raise ValueError("truncated RLE run")
			repeat = data[i + 1]
			count = int.from_bytes(data[i + 2 : i + 4], "big")
			if count == 0:
				out.append(repeat)  # literal (standard MSA)
				i += 4
			else:
				# this variant's literal $E5 is a count-1 run
				out.extend(bytes([repeat]) * count)
				i += 4
		else:
			out.append(b)
			i += 1
	if len(out) != out_len:
		raise ValueError(f"track unrle length {len(out)} != expected {out_len}")
	return bytes(out)


def msa_to_st(msa: bytes) -> bytes:
	header_id = int.from_bytes(msa[0:2], "big")
	if header_id == 0x0143:
		cyls = int.from_bytes(msa[2:4], "big")
		sides = int.from_bytes(msa[4:6], "big") + 1
		start = int.from_bytes(msa[6:8], "big")
		end = int.from_bytes(msa[8:10], "big")
		sectors = 512 * 10  # assume standard ST 10-sector disks
	elif header_id == 0x0E0F:
		spt = int.from_bytes(msa[2:4], "big")
		sides = int.from_bytes(msa[4:6], "big") + 1
		start = int.from_bytes(msa[6:8], "big")
		end = int.from_bytes(msa[8:10], "big")
		cyls = end + 1
		sectors = 512 * spt
	else:
		raise ValueError(f"not an MSA image (ID ${header_id:04x})")
	track_len = sectors
	out = bytearray()
	pos = 10
	for cyl in range(cyls):
		for side in range(sides):
			if not (start <= cyl <= end):
				out.extend(b"\xe5" * track_len)
				continue
			(length,) = int.from_bytes(msa[pos : pos + 2], "big"),
			pos += 2
			track = msa[pos : pos + length]
			pos += length
			if length == track_len:
				out.extend(track)  # stored raw, no escaping
			else:
				out.extend(unrle(track, track_len))
	return bytes(out)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("msa", type=Path)
	parser.add_argument("out", type=Path, help="raw .st output")
	args = parser.parse_args()
	raw = msa_to_st(args.msa.read_bytes())
	args.out.write_bytes(raw)
	print(f"{args.msa} -> {args.out}: {len(raw)} bytes")


if __name__ == "__main__":
	main()
