#!/usr/bin/env python3
"""Build patched Entombed (STe Enhanced) from originals/stf30a.msa + patches/entombed_patch.s."""
from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
TOOLS_DIR = GAME_DIR / "tools"
PATCH_SRC = GAME_DIR / "patches" / "entombed_patch.s"
WORK_DIR = GAME_DIR / "work"
OVERLAY_DIR = WORK_DIR / "disk_overlay"
UNPACKED_PRG = WORK_DIR / "extracted" / "ENTOMBED_UNPACKED.PRG"
PATCH_PRG = WORK_DIR / "entombed_patch.tos"
OUT_PRG = OVERLAY_DIR / "ENTOMBED.PRG"

ORIG_LOAD = 0x012576       # Reference RAM load address from Hatari dump
ORIG_TEXT_LEN = 0x1D446
ORIG_BSS_LEN = 0x34456
PATCH_OFF = 0x1D448        # 4-byte aligned start of appended patch code
PATCH_SLOT = 0x4000        # 16 KB reserved for patch TEXT+DATA
BSS_SHIFT = (PATCH_OFF - ORIG_TEXT_LEN) + PATCH_SLOT  # 0x4002


def read_tos_relocs(rel: bytes) -> list[int]:
    if len(rel) < 4:
        return []
    (off,) = struct.unpack_from(">I", rel, 0)
    if off == 0:
        return []
    out = [off]
    pos = 4
    while pos < len(rel):
        b = rel[pos]
        pos += 1
        if b == 0:
            break
        elif b == 1:
            off += 254
        else:
            off += b
            out.append(off)
    return out


def encode_tos_relocs(offs: list[int]) -> bytes:
    if not offs:
        return b"\x00\x00\x00\x00"
    offs = sorted(set(offs))
    out = bytearray(struct.pack(">I", offs[0]))
    prev = offs[0]
    for o in offs[1:]:
        d = o - prev
        assert d > 0 and (d % 2) == 0, f"Invalid reloc delta {d} at {o:#x}"
        while d > 254:
            out.append(1)
            d -= 254
        out.append(d)
        prev = o
    out.append(0)
    return bytes(out)


def ensure_unpacked() -> bytes:
    if not UNPACKED_PRG.exists():
        subprocess.run([sys.executable, str(TOOLS_DIR / "unpack_entombed.py")], check=True)
    return UNPACKED_PRG.read_bytes()


def assemble_patch() -> tuple[bytes, int, list[int]]:
    cmd = [
        "vasmm68k_mot",
        "-Ftos",
        "-m68000",
        "-quiet",
        f"-DPATCH_OFF=${PATCH_OFF:x}",
        f"-DBSS_SHIFT=${BSS_SHIFT:x}",
        f"-DORIG_LOAD=${ORIG_LOAD:x}",
        "-o",
        str(PATCH_PRG),
        str(PATCH_SRC),
    ]
    subprocess.run(cmd, check=True)
    raw = PATCH_PRG.read_bytes()
    magic, ptlen, pdlen, pblen, pslen = struct.unpack_from(">HIIII", raw, 0)
    assert magic == 0x601A
    pcode = raw[28 : 28 + ptlen + pdlen]
    assert len(pcode) <= PATCH_SLOT, f"Patch size {len(pcode):#x} > slot {PATCH_SLOT:#x}"
    prelocs = read_tos_relocs(raw[28 + ptlen + pdlen + pslen :])
    return pcode, pblen, prelocs


def write_jsr(buf: bytearray, relocs: set[int], orig_ram_addr: int, target_off: int, nops: int = 0):
    off = orig_ram_addr - ORIG_LOAD
    buf[off : off + 2] = b"\x4e\xb9"  # jsr abs.l
    struct.pack_into(">I", buf, off + 2, target_off)
    relocs.add(off + 2)
    for i in range(nops):
        buf[off + 6 + i * 2 : off + 8 + i * 2] = b"\x4e\x71"


def write_jmp(buf: bytearray, relocs: set[int], orig_ram_addr: int, target_off: int, nops: int = 0):
    off = orig_ram_addr - ORIG_LOAD
    buf[off : off + 2] = b"\x4e\xf9"  # jmp abs.l
    struct.pack_into(">I", buf, off + 2, target_off)
    relocs.add(off + 2)
    for i in range(nops):
        buf[off + 6 + i * 2 : off + 8 + i * 2] = b"\x4e\x71"


def build():
    orig = ensure_unpacked()
    magic, tlen, dlen, blen, slen = struct.unpack_from(">HIIII", orig, 0)
    assert magic == 0x601A and tlen == ORIG_TEXT_LEN and dlen == 0 and blen == ORIG_BSS_LEN

    orig_text = bytearray(orig[28 : 28 + tlen])
    orig_relocs = set(read_tos_relocs(orig[28 + tlen + dlen + slen :]))

    # Shift all original BSS references (>= ORIG_TEXT_LEN) by +BSS_SHIFT
    shifted = 0
    for roff in orig_relocs:
        (val,) = struct.unpack_from(">I", orig_text, roff)
        if val >= ORIG_TEXT_LEN:
            struct.pack_into(">I", orig_text, roff, val + BSS_SHIFT)
            shifted += 1

    # Assemble patch code
    pcode, patch_bss, patch_relocs = assemble_patch()
    patch_td_len = len(pcode)

    # Combine TEXT: orig_text (padded to PATCH_OFF) + pcode (padded to PATCH_SLOT)
    full_text = bytearray(PATCH_OFF + PATCH_SLOT)
    full_text[:tlen] = orig_text
    full_text[PATCH_OFF : PATCH_OFF + patch_td_len] = pcode

    # Relocate patch internal references
    patch_bss_base = PATCH_OFF + PATCH_SLOT + ORIG_BSS_LEN
    for proff in patch_relocs:
        (val,) = struct.unpack_from(">I", full_text, PATCH_OFF + proff)
        if val < patch_td_len:
            new_val = val + PATCH_OFF
        else:
            new_val = (val - patch_td_len) + patch_bss_base
        struct.pack_into(">I", full_text, PATCH_OFF + proff, new_val)
        orig_relocs.add(PATCH_OFF + proff)

    # ---- Hook sites (jump table at PATCH_OFF + 0, 4, 8, ...) ----
    # [0]  Entry startup: $012576 (replaces 8 bytes: move.w #0,-(sp); move.w #$15,-(sp))
    write_jsr(full_text, orig_relocs, 0x012576, PATCH_OFF + 0, nops=1)
    # [4]  Title copyright hook: $013172 (replaces 6 bytes: jsr $179c4.l)
    write_jsr(full_text, orig_relocs, 0x013172, PATCH_OFF + 4)
    # [8]  In-game keyboard poll: $012a4a (replaces 8 bytes: cmp.b #$70,d0; beq.w $12aa4)
    write_jsr(full_text, orig_relocs, 0x012A4A, PATCH_OFF + 8, nops=1)
    # [12] In-game screen swap/vsync: $0129b4 (replaces 6 bytes: jsr $1348a.l)
    write_jsr(full_text, orig_relocs, 0x0129B4, PATCH_OFF + 12)
    # [16] Tile cache build: $014472 (replaces 6 bytes: move.w $183c8.l,d7 -> jmp hook_tile_cache)
    write_jmp(full_text, orig_relocs, 0x014472, PATCH_OFF + 16)
    # [20] Tilemap renderer: $013504 (replaces 6 bytes: move.w $18142.l,d0 -> jmp hook_render_map)
    write_jmp(full_text, orig_relocs, 0x013504, PATCH_OFF + 20)
    # [24] HUD draw: $012992 (replaces 6 bytes: jsr $12e7e.l)
    write_jsr(full_text, orig_relocs, 0x012992, PATCH_OFF + 24)
    # [28] Sprite draw (normal): $015fd8 (replaces 6 bytes: sub.w $18142.l,d1 -> jmp hook_spr_normal)
    write_jmp(full_text, orig_relocs, 0x015FD8, PATCH_OFF + 28)
    # [32] Sprite draw (alt 1): $0161ac (replaces 6 bytes: sub.w $18142.l,d1 -> jmp hook_spr_alt1)
    write_jmp(full_text, orig_relocs, 0x0161AC, PATCH_OFF + 32)
    # [36] Sprite draw (alt 2): $016334 (replaces 6 bytes: sub.w $18142.l,d1 -> jmp hook_spr_alt2)
    write_jmp(full_text, orig_relocs, 0x016334, PATCH_OFF + 36)
    # [40] Leave gameplay (Tomb Select): $012718 (replaces 6 bytes: jsr $12b2a.l)
    write_jsr(full_text, orig_relocs, 0x012718, PATCH_OFF + 40)
    # [44] Leave gameplay (Game Over / High Score): $0128ac (replaces 6 bytes: jsr $17a72.l)
    write_jsr(full_text, orig_relocs, 0x0128AC, PATCH_OFF + 44)
    # [48] Leave gameplay (All Tombs Complete): $012a20 (replaces 6 bytes: jsr $17a72.l)
    write_jsr(full_text, orig_relocs, 0x012A20, PATCH_OFF + 44)
    # [52] Level load reset: $012730 (replaces 6 bytes: jsr $1535e.l)
    write_jsr(full_text, orig_relocs, 0x012730, PATCH_OFF + 48)

    total_text = len(full_text)
    total_bss = ORIG_BSS_LEN + patch_bss
    reloc_bytes = encode_tos_relocs(list(orig_relocs))

    header = struct.pack(">HIIIIIIH", 0x601A, total_text, 0, total_bss, 0, 0, 0, 0)
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    OUT_PRG.write_bytes(header + bytes(full_text) + reloc_bytes)
    print(
        f"Built {OUT_PRG}: TEXT={total_text:#x} ({total_text:,} B), "
        f"BSS={total_bss:#x} ({total_bss:,} B), patch={patch_td_len:,} B, "
        f"relocs={len(orig_relocs)} (shifted {shifted} BSS refs)"
    )


if __name__ == "__main__":
    build()
