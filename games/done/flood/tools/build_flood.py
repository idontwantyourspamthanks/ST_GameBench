#!/usr/bin/env python3
"""
Build patched Flood executable (FLO.PRG) + Amiga audio data files (AM_MUS.BIN, AM_SFX.BIN)
from originals/FLOODGX/FILES/FLO.FIC, alt/amiga/*.adf, and patches/flood_patch.s.

Never modifies originals/ or alt/. Writes output to work/disk_overlay/.
"""
import argparse
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG_FLO = ROOT / "originals" / "FLOODGX" / "FILES" / "FLO.FIC"
AMIGA_ADF = ROOT / "alt" / "amiga" / "Flood (Bullfrog + Electronic Arts).adf"
PATCH_ASM = ROOT / "patches" / "flood_patch.s"
OUT_DIR = ROOT / "work" / "disk_overlay"

AM_LOAD_BASE = 0x009530
AM_SLICE_S = 0x00D0A8
AM_SLICE_E = 0x00E004
AM_RAM_S = AM_SLICE_S + AM_LOAD_BASE  # 0x0165D8
AM_RAM_E = AM_SLICE_E + AM_LOAD_BASE  # 0x017534
# Two false-positive 4-byte matches in opcode stream (not pointers!):
AM_FALSE_PTR_OFFS = {0x0A4E, 0x0B12}


def unpack_c3(data: bytes) -> bytes:
    assert data[:2] == b"C3", f"Expected C3 header, got {data[:4]!r}"
    unpacked_len = struct.unpack(">I", data[6:10])[0]
    p = 32
    out = bytearray()
    while p < len(data):
        b = data[p]
        p += 1
        if b == 0:
            break
        if b < 0x80:
            out.extend(data[p : p + b])
            p += b
        else:
            d2 = b & 0x3F
            if not (b & 0x40):
                ln = d2 + 3
                dist = data[p]
                p += 1
            else:
                ln = d2 + 4
                dist = (data[p] << 8) | data[p + 1]
                p += 2
            for _ in range(ln):
                out.append(out[-dist])
    assert len(out) == unpacked_len, f"Unpack size mismatch: {len(out)} != {unpacked_len}"
    return bytes(out)


def unpack_bf(data: bytes) -> bytes:
    """Bullfrog word-tag LZ77 decompressor (used by both ST and Amiga Flood)."""
    _plen, ulen = struct.unpack(">II", data[:8])
    p = 8
    out = bytearray()
    while len(out) < ulen and p + 2 <= len(data):
        tag = struct.unpack(">h", data[p : p + 2])[0]
        p += 2
        if tag >= 0:
            ln = tag + 1
            out.extend(data[p : p + ln])
            p += ln
        else:
            ln = (-tag) + 1
            off = struct.unpack(">H", data[p : p + 2])[0]
            p += 2
            for i in range(ln):
                out.append(out[off + i])
    assert len(out) == ulen, f"BF unpack mismatch: {len(out)} != {ulen}"
    return bytes(out)


def read_amiga_file(adf: bytes, wanted: str) -> bytes:
    off = 0x1600
    while off < 0x1800 and adf[off] != 0:
        name = adf[off : off + 8].decode("ascii").rstrip("\x00 ")
        s_trk, _e_trk, length = struct.unpack(">HHI", adf[off + 8 : off + 16])
        if name == wanted:
            return adf[s_trk * 0x1600 : s_trk * 0x1600 + length]
        off += 16
    raise FileNotFoundError(f"{wanted} not found in Amiga ADF")


def am_to_ste_color(c: int) -> int:
    out = 0
    for sh in (8, 4, 0):
        n = (c >> sh) & 0xF
        out |= (((n >> 1) | ((n & 1) << 3)) & 0xF) << sh
    return out


def parse_tos_relocs(prg: bytes, td_len: int, sym_len: int) -> list[int]:
    rp = 0x1C + td_len + sym_len
    first = struct.unpack(">I", prg[rp : rp + 4])[0]
    rp += 4
    relocs = []
    if first != 0:
        off = first
        relocs.append(off)
        while rp < len(prg):
            b = prg[rp]
            rp += 1
            if b == 0:
                break
            if b == 1:
                off += 254
            else:
                off += b
                relocs.append(off)
    return relocs


def encode_tos_relocs(relocs: list[int]) -> bytes:
    relocs = sorted(set(relocs))
    if not relocs:
        return b"\x00\x00\x00\x00"
    out = bytearray(struct.pack(">I", relocs[0]))
    prev = relocs[0]
    for off in relocs[1:]:
        diff = off - prev
        assert diff > 0 and (diff & 1) == 0, f"Invalid reloc diff {diff} at 0x{off:x}"
        while diff > 254:
            out.append(1)
            diff -= 254
        out.append(diff)
        prev = off
    out.append(0)
    return bytes(out)


def prepare_amiga_audio_blob(am_run_prog: bytes, blob_base: int, patch_base: int) -> tuple[bytearray, list[int]]:
    """
    Extract RUN_PROG[0xd0a8:0xe004] (3932 B), relocate all 80 internal pointers to blob_base,
    and redirect Amiga Paula/CIA hardware writes to our Virtual Paula routines in flood_patch.s.
    """
    blob = bytearray(am_run_prog[AM_SLICE_S:AM_SLICE_E])
    blob_relocs = []

    # 1. Relocate all genuine internal pointers in [AM_RAM_S, AM_RAM_E]
    for off in range(0, len(blob) - 3, 2):
        if off in AM_FALSE_PTR_OFFS:
            continue
        val = struct.unpack(">I", blob[off : off + 4])[0]
        if AM_RAM_S <= val <= AM_RAM_E:
            new_val = (val - AM_RAM_S) + blob_base
            struct.pack_into(">I", blob, off, new_val)
            blob_relocs.append(blob_base + off)

    def patch_blob(off: int, data: bytes, reloc_offs=()):
        # Remove any old relocs inside overwritten bytes
        nonlocal blob_relocs
        end = off + len(data)
        blob_relocs = [r for r in blob_relocs if not (blob_base + off <= r < blob_base + end)]
        blob[off:end] = data
        for ro in reloc_offs:
            blob_relocs.append(blob_base + off + ro)

    # 2. Patch am_stop_all (blob+$06ee = file 0xd796, 18 bytes): jmp vpaula_stop_all
    patch_blob(0x06EE, struct.pack(">HI", 0x4EF9, patch_base + 52), reloc_offs=(2,))

    # 3. Patch Paula channel update (blob+$0aa2 = file 0xdb4a..0xdc02):
    #    jsr vpaula_update; bra.w $dc02 (at blob+$0b5a -> disp = 0x0b5a - (0x0aa8 + 2) = +$00b0)
    #    Note: $dc02 is `movem.l (a7)+, d0-d3/a0-a2` which balances $db4a's `movem.l`,
    #    so jump straight to $dc06 (blob+$0b5e -> disp = 0x0b5e - 0x0aaa = +$00b4)!
    disp_dc06 = 0x0B5E - (0x0AA8 + 2)
    patch_blob(0x0AA2, struct.pack(">HIHh", 0x4EB9, patch_base + 44, 0x6000, disp_dc06), reloc_offs=(2,))
    # Clear unused bytes in $0aac..$0b5a to NOPs so hwscan never sees old $dff0a0/$dff096!
    patch_blob(0x0AAC, b"\x4e\x71" * ((0x0B5A - 0x0AAC) // 2))

    # 4. Patch am_tick_core return (blob+$0b84 = file 0xdc2c..0xdc3a): rts (skip $dff09c + rte!)
    patch_blob(0x0B84, struct.pack(">H", 0x4E75) + b"\x4e\x71" * 6)

    # 5. Patch unused CIA-B ISR wrapper (blob+$0a3c..0x0a66 = file 0xdae4..0xdb0e) to NOPs (removes $bfdd00/$15ace)
    patch_blob(0x0A3C, b"\x4e\x71" * ((0x0A66 - 0x0A3C) // 2))

    # 6. Patch Paula channel stop (blob+$0e8c = file 0xdf34..0xdf58): jmp vpaula_stop_ch
    patch_blob(0x0E8C, struct.pack(">HI", 0x4EF9, patch_base + 48) + b"\x4e\x71" * 16, reloc_offs=(2,))

    return blob, blob_relocs


def build(out_dir: Path, disable_blitter: bool = False):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "FLO.PRG"

    # 1. Unpack FLO.FIC
    orig_prg = unpack_c3(ORIG_FLO.read_bytes())
    tlen, dlen, blen, slen = struct.unpack(">IIII", orig_prg[2:18])
    td = tlen + dlen
    assert slen == 0, f"Unexpected symbol table {slen}"
    relocs = parse_tos_relocs(orig_prg, td, slen)

    # 2. Assemble flood_patch.s -> TOS .PRG
    tmp_tos = Path("/tmp/flood_neon/flood_patch.tos")
    tmp_tos.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["vasmm68k_mot", "-Ftos", "-m68000", "-spaces", "-quiet", "-o", str(tmp_tos), str(PATCH_ASM)],
        check=True,
    )
    ptos = tmp_tos.read_bytes()
    pt_tlen, pt_dlen, pt_blen, pt_slen = struct.unpack(">IIII", ptos[2:18])
    pt_td = pt_tlen + pt_dlen
    pt_relocs = parse_tos_relocs(ptos, pt_td, pt_slen)
    pt_body = bytearray(ptos[0x1C : 0x1C + pt_td])
    if len(pt_body) & 1:
        pt_body.append(0)

    # 3. Extract Amiga assets from ADF
    adf = AMIGA_ADF.read_bytes()
    am_run_prog = read_amiga_file(adf, "RUN_PROG")

    # Write AM_MUS.BIN (TRACK.DA unpacked 9344 B + INSTR.DA 120576 B = 129920 B)
    am_track = unpack_bf(read_amiga_file(adf, "TRACK.DA"))
    am_instr = read_amiga_file(adf, "INSTR.DA")
    assert len(am_track) == 9344 and len(am_instr) == 120576
    (out_dir / "AM_MUS.BIN").write_bytes(am_track + am_instr)

    # Write AM_SFX.BIN (FLDFX.DU 2111 B + 1 pad + FLDFX.IN 97348 B = 99460 B)
    am_fldfx_du = read_amiga_file(adf, "FLDFX.DU")
    am_fldfx_in = read_amiga_file(adf, "FLDFX.IN")
    assert len(am_fldfx_du) == 2111 and len(am_fldfx_in) == 97348
    (out_dir / "AM_SFX.BIN").write_bytes(am_fldfx_du + b"\x00" + am_fldfx_in)

    # Append relocated Amiga audio sequencer blob to patch body
    patch_base = td
    am_blob_off = len(pt_body)
    am_blob, am_blob_relocs = prepare_amiga_audio_blob(am_run_prog, patch_base + am_blob_off, patch_base)
    pt_body.extend(am_blob)
    if len(pt_body) & 1:
        pt_body.append(0)
    patch_size = len(pt_body)

    # 4. Shift original BSS relocations (>= td) by +patch_size
    body = bytearray(orig_prg[0x1C : 0x1C + td])
    for roff in relocs:
        val = struct.unpack(">I", body[roff : roff + 4])[0]
        if val >= td:
            struct.pack_into(">I", body, roff, val + patch_size)

    # 5. Relocate patch's own internal relocs + Amiga blob relocs
    for proff in pt_relocs:
        val = struct.unpack(">I", pt_body[proff : proff + 4])[0]
        struct.pack_into(">I", pt_body, proff, val + patch_base)
        relocs.append(patch_base + proff)
    relocs.extend(am_blob_relocs)

    # 6. Fill pointer slots in patch header (+60..+148)
    ptrs = [
        (60,  0x085D2),                      # ptr_orig_init (RAM $1ab48)
        (64,  0x0C3B6 + patch_size),         # ptr_vbl_cnt (RAM $1e92c)
        (68,  0x143EC + patch_size),         # ptr_vbl_flag (RAM $26962)
        (72,  0x011F6),                      # ptr_tiles_cpu_eq (RAM $1376c)
        (76,  0x01178),                      # ptr_tiles_cpu_ne (RAM $136ee)
        (80,  0x0BCD8),                      # ptr_spr32_cpu (RAM $1e24e)
        (84,  0x0C2FE),                      # ptr_scroll_x (DATA, RAM $1e874)
        (88,  0x0C182),                      # ptr_player_x (DATA, RAM $1e6f8)
        (92,  0x08F84),                      # ptr_orig_vbl_mus (RAM $1b4fa)
        (96,  0x02792),                      # ptr_orig_title (RAM $14d08)
        (100, 0x00876),                      # ptr_orig_game (RAM $12dec)
        (104, 0x09250),                      # ptr_orig_sfx_cont (RAM $1b7c6)
        (108, 0x09022),                      # ptr_orig_exit (RAM $1b598)
        (112, patch_base + am_blob_off),     # ptr_am_blob
        (116, 0x0926A),                      # ptr_max_scroll_x (RAM $1b7e0)
        (120, 0x01134),                      # ptr_cam_y_cont (RAM $136aa)
        (124, 0x01096),                      # ptr_cam_x_cpu (RAM $1360c)
        (128, 0x0C1E6),                      # ptr_water_map (DATA, RAM $1e75c)
        (132, 0x0C268),                      # ptr_wblocks_ptr (DATA, RAM $1e7de)
        (136, 0x0C0FE),                      # ptr_water_tog (DATA, RAM $1e674)
        (140, 0x0C300),                      # ptr_scroll_y (DATA, RAM $1e876)
        (144, 0x143E4 + patch_size),         # ptr_backbuf (BSS, RAM $2695a)
        (148, 0x0141C),                      # ptr_water_cpu (RAM $13992)
        (152, 0x143E0 + patch_size),         # ptr_frontbuf (BSS, RAM $26956)
        (156, 0x144F2 + patch_size),         # ptr_joy_byte (BSS, RAM $26a68)
        (160, 0x002CE),                      # ptr_orig_kbd_key (RAM $12844)
        (168, 0x0C248),                      # ptr_surf_bits (DATA, RAM $1e7be)
        (172, 0x07C1C),                      # ptr_water_depth (TEXT, RAM $1a192)
    ]
    for slot_off, target in ptrs:
        struct.pack_into(">I", pt_body, slot_off, target)
        relocs.append(patch_base + slot_off)

    full_body = body + pt_body
    new_dlen = dlen + patch_size
    new_blen = blen + pt_blen

    def patch_bytes(text_off: int, data: bytes, reloc_offsets=()):
        full_body[text_off : text_off + len(data)] = data
        for r in reloc_offsets:
            relocs.append(text_off + r)

    def remove_relocs_in(start: int, end: int):
        relocs[:] = [r for r in relocs if not (start <= r < end)]

    # Hook 0: Copy-protection bypass (text+$0c64: bra.b +$48)
    patch_bytes(0x0C64, bytes([0x60, 0x48]))

    # Phase 2a: Restore Amiga 12-bit STE palettes for BLOCKB (pal 1) and BLOCKC (pal 2)
    for pal_idx, am_off in ((1, 0xEA3C), (2, 0xEA7C)):
        am_pal = struct.unpack(">16H", am_run_prog[am_off : am_off + 32])
        ste_pal = struct.pack(">16H", *(am_to_ste_color(c) for c in am_pal))
        patch_bytes(0x01DA + pal_idx * 32, ste_pal)

    # Hook 1: Startup init (text+$0042: jsr patch_init)
    remove_relocs_in(0x0042, 0x0048)
    patch_bytes(0x0042, struct.pack(">HI", 0x4EB9, patch_base + 0), reloc_offsets=(2,))

    # Hook 2: 25 Hz fixed-speed pacer (text+$0d18: jsr patch_vbl_pace)
    remove_relocs_in(0x0D18, 0x0D1E)
    patch_bytes(0x0D18, struct.pack(">HI", 0x4EB9, patch_base + 4), reloc_offsets=(2,))

    if not disable_blitter:
        # Hook 3: STE Blitter 1-pixel smooth tilemap redraw (text+$1170)
        remove_relocs_in(0x1170, 0x1178)
        patch_bytes(0x1170, struct.pack(">HIH", 0x4EF9, patch_base + 8, 0x4E71), reloc_offsets=(2,))

        # Hook 4: STE Blitter 32x32 masked sprite renderer (text+$bcd2)
        remove_relocs_in(0xBCD2, 0xBCD8)
        patch_bytes(0xBCD2, struct.pack(">HI", 0x4EF9, patch_base + 12), reloc_offsets=(2,))

        # Hook 6: Smooth 1-pixel horizontal camera tracking Quiffy (text+$1090 = RAM $13606)
        remove_relocs_in(0x1090, 0x1096)
        patch_bytes(0x1090, struct.pack(">HI", 0x4EF9, patch_base + 20), reloc_offsets=(2,))

        # Hook 6b: Smooth 1-pixel water overlay (text+$1412 = RAM $13988, 10 bytes -> jmp + 2x nop)
        remove_relocs_in(0x1412, 0x141C)
        patch_bytes(0x1412, struct.pack(">HIHH", 0x4EF9, patch_base + 56, 0x4E71, 0x4E71), reloc_offsets=(2,))

    # Hook 5: Falcon-safe YM digi-SFX write (text+$875e)
    remove_relocs_in(0x875E, 0x8766)
    patch_bytes(0x875E, struct.pack(">HIH", 0x4EB9, patch_base + 16, 0x4E71), reloc_offsets=(2,))

    # Phase 3a: VBL Audio Tick + STE DMA Mixer (text+$012e: jsr $1b4fa -> jsr patch_vbl_audio)
    remove_relocs_in(0x012E, 0x0134)
    patch_bytes(0x012E, struct.pack(">HI", 0x4EB9, patch_base + 24), reloc_offsets=(2,))

    # Phase 3b: Title Screen -> Amiga Title Music (text+$0606: jsr $14d08 -> jsr patch_title_hook)
    remove_relocs_in(0x0606, 0x060C)
    patch_bytes(0x0606, struct.pack(">HI", 0x4EB9, patch_base + 28), reloc_offsets=(2,))

    # Phase 3c: Gameplay Loop -> Amiga In-Game SFX (text+$0632: jsr $12dec -> jsr patch_game_hook)
    remove_relocs_in(0x0632, 0x0638)
    patch_bytes(0x0632, struct.pack(">HI", 0x4EB9, patch_base + 32), reloc_offsets=(2,))

    # Phase 3d: In-Game SFX trigger (text+$9248: sub_01b7be -> jmp patch_sfx_hook)
    remove_relocs_in(0x9248, 0x924E)
    patch_bytes(0x9248, struct.pack(">HI", 0x4EF9, patch_base + 36), reloc_offsets=(2,))

    # Phase 3e: Clean Exit -> stop STE DMA (text+$0668: jsr $1b598 -> jsr patch_exit_hook)
    remove_relocs_in(0x0668, 0x066E)
    patch_bytes(0x0668, struct.pack(">HI", 0x4EB9, patch_base + 40), reloc_offsets=(2,))

    # Phase 4: Zero-lag IKBD Joystick Event Reporting ($14) + overrun-safe ISR
    #   - text+$0058: move.b #$15,$fc02.w -> move.b #$14,$fc02.w (Joy Event mode)
    #   - text+$005e: move.l #$127f0,$118.w -> move.l #patch_ikbd_isr,$118.w
    #   - text+$0498: skip per-frame $16 joystick interrogate poll (14 bytes -> bra.s +12 + 6x NOP)
    patch_bytes(0x005B, bytes([0x14]))
    remove_relocs_in(0x0060, 0x0064)
    patch_bytes(0x0060, struct.pack(">I", patch_base + 164), reloc_offsets=(0,))
    patch_bytes(0x0498, bytes([0x60, 0x0C]) + b"\x4e\x71" * 6)

    # Phase 4b: Walk-animation staircase anti-aliasing fix (text+$ae4e = RAM $1d3c4)
    remove_relocs_in(0xAE4E, 0xAE54)
    patch_bytes(0xAE4E, struct.pack(">HI", 0x4EB9, patch_base + 176), reloc_offsets=(2,))

    # Build final TOS .PRG
    hdr = struct.pack(">HIIIIHII", 0x601A, tlen, new_dlen, new_blen, 0, 0, 0, 0)[:28]
    out_prg = hdr + bytes(full_body) + encode_tos_relocs(relocs)
    out_path.write_bytes(out_prg)
    print(f"Built {out_path} ({len(out_prg)} B, patch={patch_size} B at +0x{patch_base:x}, {len(set(relocs))} relocs)")
    print(f"Wrote {out_dir / 'AM_MUS.BIN'} (129920 B) and {out_dir / 'AM_SFX.BIN'} (99460 B)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--no-blitter", action="store_true")
    args = ap.parse_args()
    build(args.out_dir, disable_blitter=args.no_blitter)
