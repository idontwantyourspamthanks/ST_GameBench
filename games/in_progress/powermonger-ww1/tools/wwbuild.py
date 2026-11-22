#!/usr/bin/env python3
"""Build a patched WW1.PRG for the Cobra #26 release (file-level, no runtime carrier).

Why this shape: WW1.PRG's text carries **no relocation table** (28 + 61622 == the file
length), so a data segment cannot be appended and the packed text cannot be patched in
place. The way through is to patch the *depacked* program: this tool depacks the ATOMIK
stream, applies the patch sites to the resulting plain image, and writes a NEW plain PRG
whose text is that image. The result is itself a normal GEMDOS PRG (no depacker), so it
loads anywhere and any later patch is trivial.

    python3 tools/wwbuild.py list
    python3 tools/wwbuild.py build [--only NAME ...] [--out DIR]

`build` depacks with tools/atomik.py, checks each site's original bytes, and writes a
plain GEMDOS PRG: the nested program's text plus its own relocation table.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

from atomik import depack

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
PRG = GAME / "extracted" / "cobra26" / "WW1.PRG"
TEXT_LEN = 61622
PAYLOAD = 0x72000          # the payload home proven free at the map view
BASE_GUESS = 0x1265E       # the stub's load address observed live (hand-over at +$238)

# ---------------------------------------------------------------------------------
# Patch sites as offsets into the depacked program's *text* (the nested PRG header is
# not part of that text). The map-view runtime address is $110 below the text offset:
# the pass-head bytes sit at text $13EB0, which is runtime $13DA0. Original bytes were
# checked against the depacked image.
# ---------------------------------------------------------------------------------
TICK_SITES = [
	# (text offset, original, replacement, what)
	(0x13EB0, bytes.fromhex("4a790005a856"), bytes.fromhex("4eb900072000"), "pass head"),
	(0x13F34, bytes.fromhex("4eb90001b90a"), bytes.fromhex("4eb9000720e0"), "weather wrapper"),
	(0x13F46, bytes.fromhex("4eb9000158b2"), bytes.fromhex("4eb900072110"), "men wrapper"),
	(0x13F52, bytes.fromhex("4eb9000074e0"), bytes.fromhex("4eb900072140"), "terrain wrapper"),
	(0x8F6,   bytes.fromhex("0002ed90"),     bytes.fromhex("00072180"), "click stamp (right)"),
	(0x952,   bytes.fromhex("0002ed90"),     bytes.fromhex("00072180"), "click stamp (left)"),
	(0x145C4, bytes.fromhex("0002ed90"),     bytes.fromhex("00072180"), "click expiry"),
]

PATCHES = {
	"tick": TICK_SITES,
}


def prg_parts(path: Path = PRG):
	data = path.read_bytes()
	magic, text, data_len, bss, sym = struct.unpack_from(">HIIII", data, 0)
	if magic != 0x601A:
		raise SystemExit(f"{path}: not a GEMDOS PRG (magic ${magic:04x})")
	reloc_at = 28 + text + data_len + sym
	if reloc_at != len(data):
		raise SystemExit(
			f"{path}: reloc table at {reloc_at} but the file is {len(data)} bytes — this is not "
			"the shape this tool expects (no reloc table, text ends the file)")
	return dict(header=data[:28], text=data[28:28 + text], text_len=text, bss=bss, sym=sym)


def plain_prg(packed_text: bytes, sites: list[tuple]) -> bytes:
	"""Depack `packed_text`, patch `sites` (text offsets), return a GEMDOS PRG.

	The depacked blob is itself a PRG: 28-byte header, text, then a reloc table and
	nothing else. TOS must see that reloc table, because the entry `jmp` is one of
	the relocs. The blob's own header is not part of the text TOS should load.
	"""
	image = depack(packed_text)
	magic, text_len, data_len, bss, sym = struct.unpack_from(">HIIII", image, 0)
	if magic != 0x601A or data_len or sym:
		raise SystemExit(
			f"depacked image is not a text-only PRG (magic ${magic:04x}, data {data_len}, sym {sym})")
	reloc_at = 28 + text_len
	if image[reloc_at + 4:].find(0) < 0:
		raise SystemExit("depacked image has no reloc terminator")
	body = bytearray(image[28:reloc_at])
	reloc = image[reloc_at:]
	for off, orig, new, what in sites:
		cur = bytes(body[off:off + len(orig)])
		if cur != orig:
			raise SystemExit(f"{what} at text ${off:05x}: expected {orig.hex(' ')}, found {cur.hex(' ')}")
		if len(new) != len(orig):
			raise SystemExit(f"{what}: replacement length {len(new)} != original {len(orig)}")
		body[off:off + len(orig)] = new
	header = bytearray(28)
	struct.pack_into(">HIIII", header, 0, 0x601A, len(body), 0, bss, 0)
	return bytes(header) + bytes(body) + reloc


def build(only: list[str], out: Path) -> Path:
	parts = prg_parts()
	sites = [s for name in only for s in PATCHES[name]]
	prg = plain_prg(parts["text"], sites)
	out.mkdir(parents=True, exist_ok=True)
	dest = out / "WW1.PRG"
	dest.write_bytes(prg)
	text_len = struct.unpack_from(">I", prg, 2)[0]
	print(f"wrote {dest} ({dest.stat().st_size} bytes, {text_len} text, sites: {len(sites)})")
	return dest


def main() -> None:
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	sub = ap.add_subparsers(dest="cmd", required=True)
	sub.add_parser("list")
	b = sub.add_parser("build")
	b.add_argument("--only", nargs="*", default=["tick"])
	b.add_argument("--out", type=Path, default=GAME / "build" / "patched")
	args = ap.parse_args()

	if args.cmd == "list":
		for name, sites in PATCHES.items():
			print(f"{name}: {len(sites)} sites")
			for off, orig, new, what in sites:
				print(f"   ${off:05x} {what:22s} {orig.hex(' ')} -> {new.hex(' ')}")
		return
	build(args.only, args.out)


if __name__ == "__main__":
	main()
