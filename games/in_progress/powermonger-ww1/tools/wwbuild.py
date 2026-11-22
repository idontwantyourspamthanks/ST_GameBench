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

At the time of writing the ATOMIK depacker is not yet exact (tools/atomik.py), so `build`
refuses unless `--allow-unverified` is passed and says so loudly.
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
PRG = GAME / "extracted" / "cobra26" / "WW1.PRG"
TEXT_LEN = 61622
PAYLOAD = 0x72000          # the payload home proven free at the map view
BASE_GUESS = 0x1265E       # the stub's load address observed live (hand-over at +$238)

# ---------------------------------------------------------------------------------
# The patch sites, as (runtime address, original bytes, replacement bytes).
# The runtime address minus the load base gives the *loaded image* offset, which is what
# wwbuild writes into the rebuilt image. Everything here was verified live on this build
# (work/notes/tickproto.md, work/notes/cobra26.md).
# ---------------------------------------------------------------------------------
TICK_SITES = [
	# (image offset, original, replacement, what)
	(0x13DA0, bytes.fromhex("4a790005a856"), bytes.fromhex("4eb9000720 00".replace(" ", "")), "pass head"),
	(0x13E24, bytes.fromhex("4eb90001b90a"), bytes.fromhex("4eb9000720 e0".replace(" ", "")), "weather wrapper"),
	(0x13E36, bytes.fromhex("4eb9000158b2"), bytes.fromhex("4eb9000721 10".replace(" ", "")), "men wrapper"),
	(0x13E42, bytes.fromhex("4eb9000074e0"), bytes.fromhex("4eb9000721 40".replace(" ", "")), "terrain wrapper"),
	(0x7E6,   bytes.fromhex("0002ed90"),     bytes.fromhex("00072180"), "click stamp (right)"),
	(0x842,   bytes.fromhex("0002ed90"),     bytes.fromhex("00072180"), "click stamp (left)"),
	(0x144B4, bytes.fromhex("0002ed90"),     bytes.fromhex("00072180"), "click expiry"),
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


def build(only: list[str], out: Path, allow_unverified: bool) -> Path:
	parts = prg_parts()
	image = parts["text"]          # the ATOMIK stub + the packed stream (not the game)

	if not allow_unverified:
		raise SystemExit(
			"the ATOMIK depacker (tools/atomik.py) is not yet verified, so the game image cannot\n"
			"be produced and the sites cannot be applied. Re-run with --allow-unverified to write\n"
			"the unpatched rebuild (useful only to check the PRG plumbing).")

	sites = [s for name in only for s in PATCHES[name]]
	for off, orig, new, what in sites:
		cur = image[off:off + len(orig)]
		if cur != orig:
			raise SystemExit(f"{what} at image ${off:05x}: expected {orig.hex(' ')}, found {cur.hex(' ')}")
		if len(new) != len(orig):
			raise SystemExit(f"{what}: replacement length {len(new)} != original {len(orig)}")
		image = image[:off] + new + image[off + len(new):]

	out.mkdir(parents=True, exist_ok=True)
	header = bytearray(parts["header"])
	struct.pack_into(">I", header, 2, len(image))
	# no reloc table: a zero long terminator
	dest = out / "WW1.PRG"
	dest.write_bytes(bytes(header) + image + b"\0\0\0\0")
	print(f"wrote {dest} ({dest.stat().st_size} bytes, {len(image)} text, sites: {len(sites)})")
	return dest


def main() -> None:
	ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	sub = ap.add_subparsers(dest="cmd", required=True)
	sub.add_parser("list")
	b = sub.add_parser("build")
	b.add_argument("--only", nargs="*", default=["tick"])
	b.add_argument("--out", type=Path, default=GAME / "build" / "patched")
	b.add_argument("--allow-unverified", action="store_true")
	args = ap.parse_args()

	if args.cmd == "list":
		for name, sites in PATCHES.items():
			print(f"{name}: {len(sites)} sites")
			for off, orig, new, what in sites:
				print(f"   ${off:05x} {what:22s} {orig.hex(' ')} -> {new.hex(' ')}")
		return
	build(args.only, args.out, args.allow_unverified)


if __name__ == "__main__":
	main()
