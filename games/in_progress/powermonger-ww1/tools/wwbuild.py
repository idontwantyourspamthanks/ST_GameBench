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

# Copy protection: the "passed" state is one long word at runtime $15998, a slot in a jump
# table of `bra.w` instructions. It reads `60 00 15 ea` (bra.w) until the question is answered;
# a right answer stores $0000002c, which disassembles as `ori.b #$2c,d0` and falls through into
# the next `bra.w`. Writing $2c there is exactly what a correct answer does, so every reader of
# the word sees the answered state and the check never starts. This is the 1990 project's
# `pm_noprot` site ($14e4e there); the surrounding structure matches instruction for instruction
# (work/notes/protection.md).
#   runtime $15998 -> text offset $15998 + $110 = $15AA8
NOPROT_SITES = [
	(0x15AA8, bytes.fromhex("600015  ea".replace(" ", "")), bytes.fromhex("0000002c"), "protection pass flag"),
]

# Part 2: the "Please Wait For The Protection Check" box. Clearing the pass flag stops the
# check from starting, but the box is opened separately and unconditionally: the first
# instruction of the new-conquest start ($13d52) is `jsr $bbd2`, and $bbd2 is
#
#     $bbd2  lea $bbe8.l,a1        ; the box descriptor (its text at $bc04)
#     $bbd8  jsr $759a.l           ; claim a panel slot
#     $bbde  beq.s $bbe6
#     $bbe0  jsr $a2ce.l           ; draw it
#     $bbe6  rts
#
# The original closes it from the protection check ($b2d4 -> $b440), which never runs once
# the flag is preset, so the box would sit on screen forever. Only one caller exists, so
# replacing the body with `rts` removes the box and nothing else. This is the 1990
# project's `pm_noprot_box`; the routine is the same shape (work/notes/protection.md).
#   runtime $bbd2 -> text offset $bbd2 + $110 = $BCE2
NOPROT_BOX_SITES = [
	(0xBCE2, bytes.fromhex("43f90000bbe8"), bytes.fromhex("4e754e714e71"), "protection box"),
]

# Keyboard shortcuts (work/notes/input.md section 5.3; prototype work/keyproto/keys.s).
# A letter key does what a click on its command icon does: the IKBD key path records the
# scancode, and just before the map view's own click dispatch the hook writes the same words
# a real click writes (the cell centre + the left latch + the pass stamp). Keys:
# A D E F G H I L M N O Q R S T X Y for the commands, 1/2/3 for the postures.
#
#   runtime $f30  `move.b d0,$1d2b0`  -> jsr $72400   (the IKBD key path store)
#   runtime $13e6a `jsr $d62a`        -> jsr $72480   (just before the input section)
KEY_SITES = [
	(0x1040, bytes.fromhex("13c00001d2b0"), bytes.fromhex("4eb900072400"), "key capture"),
	(0x13F7A, bytes.fromhex("4eb90000d62a"), bytes.fromhex("4eb900072480"), "key dispatch"),
]

PATCHES = {
	"tick": TICK_SITES,
	"noprot": NOPROT_SITES + NOPROT_BOX_SITES,
	"keys": KEY_SITES,
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


def plain_prg(packed_text: bytes, sites: list[tuple], only: list[str]) -> bytes:
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
	if not sites or not any(name in only for name in PAYLOADS):
		# No payload patch: no stub, no data (a build with only in-text patches stays a
		# plain PRG).
		header = bytearray(28)
		struct.pack_into(">HIIII", header, 0, 0x601A, len(body), 0, bss, 0)
		return bytes(header) + bytes(body) + reloc
	payload = _payload_image(only)
	stub = _copy_stub(len(payload))
	struct.pack_into(">I", body, 2, len(body))   # existing reloc: entry jumps to the data segment
	data = stub + payload
	reloc = _append_reloc(reloc, len(body) + STUB_JMP_AT)
	header = bytearray(28)
	struct.pack_into(">HIIII", header, 0, 0x601A, len(body), len(data), bss, 0)
	prg = bytes(header) + bytes(body) + data + reloc
	_audit(prg, len(body), data)
	return prg


# The payload blobs, each assembled to its own fixed runtime address. One copy stub carries
# the whole span from the lowest to the highest: the bytes below a blob's start are simply
# never executed, so a sparse image is cheaper than a stub per blob.
PAYLOADS = {
	"tick": (0x72000, GAME / "work" / "tickproto" / "tick.bin",
	         bytes.fromhex("2f082f002f0152b9")),      # `move.l a0,-(a7)` ...
	"keys": (0x72400, GAME / "work" / "keyproto" / "keys.bin",
	         bytes.fromhex("2f01")),                   # KEYHOOK: `move.l d1,-(a7)`
}
BASE = 0x72000
END = 0x72810          # past keys' variables at $72800..$72809 (LASTV ends $7280A)


def _payload_image(only: list[str]) -> bytes:
	"""The sparse image from $72000 to END holding every requested blob at its address."""
	need = [name for name in ("tick", "keys") if name in only]
	if not need:
		raise SystemExit("no payload-bearing patch was requested")
	image = bytearray(END - BASE)
	for name in need:
		addr, path, sig = PAYLOADS[name]
		if not path.exists():
			raise SystemExit(f"{path} is missing; assemble it from its .s first")
		blob = path.read_bytes()
		if not blob.startswith(sig):
			raise SystemExit(f"{path} does not start with its signature {sig.hex(' ')}")
		image[addr - BASE:addr - BASE + len(blob)] = blob
	return bytes(image)


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
	prg = plain_prg(parts["text"], sites, only)
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
	b.add_argument("--only", nargs="*", default=["tick", "noprot", "keys"])
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
