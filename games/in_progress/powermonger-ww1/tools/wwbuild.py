#!/usr/bin/env python3
"""Build a patched WW1.PRG for the Cobra #26 release (file-level, no runtime carrier).

Why this shape: WW1.PRG's text carries **no relocation table** (28 + 61622 == the file
length), so a data segment cannot be appended and the packed text cannot be patched in
place. The way through is to patch the *depacked* program: this tool depacks the ATOMIK
stream, applies the patch sites to the resulting plain image, and writes a NEW plain PRG
whose text is that image. The result is itself a normal GEMDOS PRG (no depacker), so it
loads anywhere and any later patch is trivial.

The tick payload is the image already proven at `$72000` (`work/tickproto/tick.bin`).
TOS only loads `28 + text + data`, so the bytes ride in the **data segment**, and a stub
there copies them to `$72000` before entering the game. The sites stay `jsr $72000`:
the startup copies the game text from `$686` to `$576`, so a site's bytes land at
`text_offset - $110` with their absolute addresses unchanged. Pointing them at
`load_base + offset` aims at empty memory once that copy has run.

    python3 tools/wwbuild.py list
    python3 tools/wwbuild.py build [--only NAME ...] [--out DIR]

`build` depacks with tools/atomik.py, checks each site's original bytes, and writes a
plain GEMDOS PRG: the nested program's text, the copy stub and payload as its data
segment, and the relocation table (plus one entry for the stub's entry jump).
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
VARS_END = 0x18C           # PASS..KIND sit just past tick.bin; the copy clears them
ENTRY_JMP = 0x24054        # text 0 is `jmp` here: Supexec of the startup
STUB_JMP_AT = 0x16         # the address long inside the copy stub (must be relocated)
TICK_BIN = GAME / "work" / "tickproto" / "tick.bin"

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


def _copy_stub(nbytes: int) -> bytes:
	"""Copy the `nbytes` that follow this stub to `$72000`, then enter the game.

	The source is PC-relative, so the load address does not matter. The `jmp $24054`
	is absolute and has to be in the reloc table; the `lea $72000` must not be.
	"""
	if not 1 <= nbytes <= 0x10000:
		raise SystemExit(f"tick payload is {nbytes} bytes; the copy stub counts with a word")
	stub = bytearray.fromhex(
		"41fa0018"        # lea payload(pc), a0
		"43f900072000"    # lea $72000.l, a1   (fixed RAM, not a reloc)
		"303c0000"        # move.w #nbytes-1, d0
		"12d8"            # move.b (a0)+, (a1)+
		"51c8fffc"        # dbra d0, loop
		"4ef900024054"    # jmp $24054.l
	)
	struct.pack_into(">H", stub, 0x0C, nbytes - 1)
	if len(stub) != 0x1A or stub[STUB_JMP_AT:STUB_JMP_AT + 4] != ENTRY_JMP.to_bytes(4, "big"):
		raise SystemExit("copy stub layout drifted; STUB_JMP_AT is wrong")
	return bytes(stub)


def _reloc_offsets(table: bytes) -> list[int]:
	"""GEMDOS relocation offsets. `table` starts at the first-offset long."""
	if len(table) < 5 or 0 not in table[4:]:
		raise SystemExit("reloc table has no terminator")
	first = struct.unpack_from(">I", table, 0)[0]
	offs = [first]
	pos = first
	i = 4
	while i < len(table):
		b = table[i]
		i += 1
		if b == 0:
			break
		if b == 1:
			pos += 254
			continue
		pos += b
		offs.append(pos)
	else:
		raise SystemExit("reloc table is unterminated")
	return offs


def _append_reloc(table: bytes, new_off: int) -> bytes:
	"""Add one relocation after the last entry. Distances of 255 stay one byte (a 1 means +254 and no reloc)."""
	offs = _reloc_offsets(table)
	gap = new_off - offs[-1]
	if gap < 2:
		raise SystemExit(f"reloc ${new_off:x} is not after the last (${offs[-1]:x})")
	extra = bytearray()
	while gap > 255:
		extra.append(1)
		gap -= 254
	extra.append(gap)
	end = table.index(0, 4)
	return table[:end] + bytes(extra) + table[end:]


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

	The tick image is appended as the data segment, preceded by a stub that copies
	it to `$72000`. The entry's existing reloc is retargeted at that stub, and one
	new reloc is added for the stub's jump back to `$24054`.
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
	if body[:6] != bytes.fromhex("4ef900024054"):
		raise SystemExit(f"entry is {body[:6].hex()}, expected jmp ${ENTRY_JMP:x}")
	if not sites:
		# An unpatched build still has to be the original program: no stub, no data.
		header = bytearray(28)
		struct.pack_into(">HIIII", header, 0, 0x601A, len(body), 0, bss, 0)
		return bytes(header) + bytes(body) + reloc
	payload = bytearray(TICK_BIN.read_bytes())
	if payload[:8] != bytes.fromhex("2f082f002f0152b9"):
		raise SystemExit("tick.bin does not start with the payload signature")
	if len(payload) < VARS_END:
		payload.extend(b"\0" * (VARS_END - len(payload)))
	stub = _copy_stub(len(payload))
	struct.pack_into(">I", body, 2, len(body))   # existing reloc: entry jumps to the data segment
	data = stub + bytes(payload)
	reloc = _append_reloc(reloc, len(body) + STUB_JMP_AT)
	header = bytearray(28)
	struct.pack_into(">HIIII", header, 0, 0x601A, len(body), len(data), bss, 0)
	prg = bytes(header) + bytes(body) + data + reloc
	_audit(prg, len(body), data)
	return prg


def _audit(prg: bytes, text_len: int, data: bytes) -> None:
	"""The file TOS will load: entry reaches the stub, the stub returns to the real entry, sites copy to $72000."""
	magic, got_text, got_data, bss, sym = struct.unpack_from(">HIIII", prg, 0)
	if (magic, got_text, got_data, bss, sym) != (0x601A, text_len, len(data), 0, 0):
		raise SystemExit(f"header mismatch: text ${got_text:x} data {got_data}")
	body = prg[28:28 + text_len]
	if struct.unpack_from(">I", body, 2)[0] != text_len:
		raise SystemExit("entry does not jump to the data segment")
	offs = _reloc_offsets(prg[28 + text_len + len(data):])
	stub_jmp = text_len + STUB_JMP_AT
	if 2 not in offs or stub_jmp not in offs:
		raise SystemExit(f"missing reloc for the entry or the stub jmp ${stub_jmp:x}")
	if text_len + 6 in offs:
		raise SystemExit("the stub's lea $72000 was relocated; the copy would miss")
	jmp_at = 28 + stub_jmp
	if struct.unpack_from(">I", prg, jmp_at)[0] != ENTRY_JMP:
		raise SystemExit("stub does not jump back to the original entry")
	# The startup copies text $686.. to $576. A patched site must arrive intact.
	for off, _orig, new, what in TICK_SITES:
		runtime = off - 0x110
		if body[off:off + len(new)] != new:
			raise SystemExit(f"{what} was not patched")
		if runtime != {0x13EB0: 0x13DA0, 0x13F34: 0x13E24, 0x13F46: 0x13E36,
		               0x13F52: 0x13E42, 0x8F6: 0x7E6, 0x952: 0x842, 0x145C4: 0x144B4}[off]:
			raise SystemExit(f"{what}: runtime ${runtime:x} is not the map-view address")


def build(only: list[str], out: Path) -> Path:
	parts = prg_parts()
	sites = [s for name in only for s in PATCHES[name]]
	prg = plain_prg(parts["text"], sites)
	out.mkdir(parents=True, exist_ok=True)
	dest = out / "WW1.PRG"
	dest.write_bytes(prg)
	text_len, data_len = struct.unpack_from(">II", prg, 2)
	print(f"wrote {dest} ({dest.stat().st_size} bytes, {text_len} text, {data_len} data, sites: {len(sites)})")
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
