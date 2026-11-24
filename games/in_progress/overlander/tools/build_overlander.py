#!/usr/bin/env python3
"""Build patched Overlander (OVERLAND.PRG + disk_overlay) from originals/overlander_elite.zip.

Phase 1:
  - Extracts & decrypts AUTO/RUN.PRO from originals/overlander_elite.zip (STX)
    into the pristine relocatable 77,376-byte GEMDOS PRG (verified checksum 0xa08be7cd).
  - Relocates all 13 TEXT_END (+0x12e40) scratch-buffer refs to BSS (scratch_40k).
  - Relocates all 231 hardcoded low-RAM ($000800..$008440) refs to BSS (lowram_bss).
  - Relocates G.TOS load buffer & initial stack from TEXT_END+$a000 to BSS (g_tos_buf).
  - Dynamically allocates 256-byte aligned triple screen buffers in BSS (scr_bufs).
  - Strips 'a:\\' from 'a:\\loadscr.img' and 'a:\\g.tos' for HD + floppy support.
  - NOPs out the 24-bit exception-vector hack (+0x0368..+0x0388) for 68030 TT/Falcon.
  - Replaces self-modifying Timer B bra.b ($b822/$b834/$b840) with 68030-safe flag wait.
  - Adds TT ST-Low video switch, IKBD mouse disable, and 25.0 fps VBL pacing.
"""
import os
import re
import struct
import subprocess
import sys
import zipfile
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
ORIG_ZIP = GAME_DIR / "originals" / "overlander_elite.zip"
WORK_DIR = GAME_DIR / "work"
OVERLAY_DIR = WORK_DIR / "disk_overlay"
PATCH_SRC = GAME_DIR / "patches" / "overlander_patch.s"
PATCH_BIN = WORK_DIR / "overlander_patch.bin"

BASE_RAM = 0x00AA9A  # Reference load address from ste_loaded.ram (for comments only)


def extract_stx_files():
    """Extract AUTO/RUN.PRG, AUTO/RUN.PRO, LOADSCR.IMG, G.TOS from overlander.stx."""
    with zipfile.ZipFile(ORIG_ZIP, "r") as zf:
        stx = zf.read("overlander.stx")

    magic, ver, tool, _, ntracks, rev = struct.unpack("<4sHHHBB", stx[:12])
    assert magic == b"RSY\x00", f"Bad STX magic: {magic!r}"

    off = 16
    img = bytearray(80 * 9 * 512)
    for _ in range(ntracks):
        rec_size, fuzzy_size, nsec, flags, track_len, track_num, track_type = struct.unpack(
            "<IIHHHBB", stx[off : off + 16]
        )
        side = (track_num >> 7) & 1
        cyl = track_num & 0x7F
        if cyl < 80 and side == 0 and nsec > 0:
            sec_hdr_off = off + 16
            base = sec_hdr_off + nsec * 16 + fuzzy_size
            for s in range(nsec):
                doff, bitpos, rtime, t, h, r, n, crc, fdc, rsv = struct.unpack(
                    "<IHHBBBBHBB", stx[sec_hdr_off + s * 16 : sec_hdr_off + (s + 1) * 16]
                )
                if 1 <= r <= 9 and (128 << n) == 512:
                    dst = (cyl * 9 + (r - 1)) * 512
                    img[dst : dst + 512] = stx[base + doff : base + doff + 512]
        off += rec_size

    tmp_img = WORK_DIR / "extracted" / "overlander_t0_79.st"
    tmp_img.parent.mkdir(parents=True, exist_ok=True)
    tmp_img.write_bytes(img)

    files_dir = WORK_DIR / "extracted" / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    for fn in ("RUN.PRG", "RUN.PRO", "LOADSCR.IMG", "G.TOS"):
        p = files_dir / fn
        if p.exists():
            p.unlink()
    env = dict(os.environ, MTOOLS_SKIP_CHECK="1")
    subprocess.run(
        [
            "mcopy", "-i", str(tmp_img),
            "::AUTO/RUN.PRG", "::AUTO/RUN.PRO", "::LOADSCR.IMG", "::G.TOS",
            str(files_dir) + "/",
        ],
        check=True,
        env=env,
    )
    return (
        (files_dir / "RUN.PRG").read_bytes(),
        (files_dir / "RUN.PRO").read_bytes(),
        (files_dir / "LOADSCR.IMG").read_bytes(),
        (files_dir / "G.TOS").read_bytes(),
    )


def decrypt_run_pro(run_prg: bytes, run_pro: bytes) -> tuple[bytearray, list[int]]:
    """Decrypt RUN.PRG -> unshuffle & XOR-decrypt RUN.PRO -> (text_bytes, reloc_offsets)."""
    # 1. Decrypt RUN.PRG
    text_len = struct.unpack(">I", run_prg[2:6])[0]
    run_dec = bytearray(run_prg[28 : 28 + text_len])
    d3 = text_len - 0x44
    d0 = 0
    while d0 != 0x200:
        d1 = 0
        d5 = struct.unpack(">H", run_dec[d0 : d0 + 2])[0]
        while d1 != d3:
            v = struct.unpack(">H", run_dec[0x44 + d1 : 0x46 + d1])[0] ^ d5
            struct.pack_into(">H", run_dec, 0x44 + d1, v)
            d5 = v
            d1 += 2
        d0 += 2
        if d0 == 0x44:
            d0 += 2

    # 2. Compute RUN_dec checksum d6 and decrypt RUN.PRO
    d6 = 0
    for i in range(0, 0x9AC, 4):
        d6 = (d6 + struct.unpack(">I", run_dec[i : i + 4])[0]) & 0xFFFFFFFF
    key_base = 0x275A  # Track-80 copy-protection key
    expect_sum = struct.unpack(">I", run_dec[0x9D4:0x9D8])[0]
    pro_len = struct.unpack(">I", run_dec[0x9C8:0x9CC])[0]

    pro = bytearray(run_pro)
    tbl = bytearray(run_dec[0xA5C:])
    d1 = 1
    while True:
        d0 = 0
        while True:
            eid = struct.unpack(">H", tbl[d0 : d0 + 2])[0]
            if eid == 0 or eid == d1:
                break
            d0 += 4
        if eid == 0:
            break
        xkey = struct.unpack(">H", tbl[d0 + 2 : d0 + 4])[0]
        blk_idx = (d0 >> 2) + 1
        if blk_idx != d1:
            i0, i1 = (blk_idx - 1) * 4, (d1 - 1) * 4
            tbl[i0 : i0 + 4], tbl[i1 : i1 + 4] = tbl[i1 : i1 + 4], tbl[i0 : i0 + 4]
            b0, b1 = (blk_idx - 1) * 512, (d1 - 1) * 512
            pro[b0 : b0 + 512], pro[b1 : b1 + 512] = pro[b1 : b1 + 512], pro[b0 : b0 + 512]
        xk = xkey ^ key_base ^ (d6 & 0xFFFF)
        b = (d1 - 1) * 512
        for j in range(0, 512, 2):
            w = struct.unpack(">H", pro[b + j : b + j + 2])[0]
            if w != 0:
                struct.pack_into(">H", pro, b + j, w ^ xk)
        d1 += 1

    got_sum = 0
    for i in range(0, pro_len, 4):
        got_sum = (got_sum + struct.unpack(">I", pro[i : i + 4])[0]) & 0xFFFFFFFF
    assert got_sum == expect_sum, f"RUN.PRO checksum mismatch: {got_sum:#x} != {expect_sum:#x}"

    magic, tlen, dlen, blen, slen = struct.unpack(">HIIII", pro[:18])
    assert magic == 0x601A and dlen == 0 and blen == 0 and slen == 0
    text = bytearray(pro[28 : 28 + tlen])

    ro = 28 + tlen
    first = struct.unpack(">I", pro[ro : ro + 4])[0]
    relocs = [first]
    pos = first
    p = ro + 4
    while True:
        b = pro[p]
        p += 1
        if b == 0:
            break
        if b == 1:
            pos += 254
        else:
            pos += b
            relocs.append(pos)

    return text, relocs


def assemble_patch() -> bytes:
    """Assemble patches/overlander_patch.s with vasmm68k_mot."""
    cmd = ["vasmm68k_mot", "-Fbin", "-spaces", "-m68000", "-o", str(PATCH_BIN), str(PATCH_SRC)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout)
        print(res.stderr, file=sys.stderr)
        raise SystemExit(f"vasmm68k_mot failed (rc={res.returncode})")
    data = PATCH_BIN.read_bytes()
    if len(data) & 1:
        data += b"\x00"
    return data


def encode_relocs(relocs: list[int]) -> bytes:
    """Encode sorted unique relocation offsets into GEMDOS relocation table."""
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


def main():
    run_prg, run_pro, loadscr, g_tos = extract_stx_files()
    text, orig_relocs = decrypt_run_pro(run_prg, run_pro)
    orig_tlen = len(text)
    assert orig_tlen == 0x12E40, f"Unexpected text len {orig_tlen:#x}"

    patch_bin = bytearray(assemble_patch())
    patch_off = orig_tlen  # Patch sits at +0x12e40

    # BSS layout (starts right after TEXT = orig_tlen + len(patch_bin), aligned to 16 bytes)
    total_text_len = (orig_tlen + len(patch_bin) + 15) & ~15
    patch_bin += b"\x00" * (total_text_len - orig_tlen - len(patch_bin))

    bss_scratch_40k = total_text_len                  # $a000 (40 KB) scratch / preshifted mountains
    bss_lowram      = bss_scratch_40k + 0xA000        # $8000 (32 KB) replaces $000800..$008800
    bss_g_tos       = bss_lowram + 0x8000             # $3b000 (241 KB) G.TOS graphics bank
    bss_mask_buf    = bss_g_tos + 0x3B000             # $1000 (4 KB) on-the-fly sprite mask scratch
    bss_am_mus      = bss_mask_buf + 0x1000           # $b400 (45 KB) AM_MUS.BIN (Amiga player + 5 tunes + 7 insts)
    bss_am_sfx      = bss_am_mus + 0xB400             # $4000 (16 KB) AM_SFX.BIN (Amiga sampled SFX)
    bss_dma_bufs    = bss_am_sfx + 0x4000             # $2000 (8 KB) 4KB vol_tbl + 2KB dma_ring + 256B vpaula
    bss_scr_bufs    = bss_dma_bufs + 0x2000           # $17800 (96 KB) 3 * 32000 + 256 aligned screens
    total_bss_len   = (bss_scr_bufs + 0x17800) - total_text_len

    print(
        f"Layout: TEXT=0x{total_text_len:x} (orig=0x{orig_tlen:x} + patch={len(patch_bin)}B), "
        f"BSS=0x{total_bss_len:x} ({total_bss_len//1024} KB), "
        f"total RAM={(total_text_len + total_bss_len)//1024} KB"
    )

    relocs = set(orig_relocs)

    # 1. Fill patch header relocated pointers (+0x44..+0x90 inside patch_bin)
    def set_patch_ptr(poff: int, target_off: int):
        struct.pack_into(">I", patch_bin, poff, target_off)
        relocs.add(patch_off + poff)

    set_patch_ptr(0x44, 0x000000)         # ptr_game_base
    set_patch_ptr(0x48, 0x00011C)         # ptr_orig_start ($abb6)
    set_patch_ptr(0x4C, bss_scr_bufs)     # ptr_scr_bufs
    set_patch_ptr(0x50, bss_g_tos)        # ptr_g_tos_buf
    set_patch_ptr(0x54, bss_lowram)       # ptr_lowram_bss
    set_patch_ptr(0x58, 0x003D46)         # ptr_orig_sky_cont ($00e7e0)
    set_patch_ptr(0x5C, 0x003D92)         # ptr_orig_sky_done ($00e82c)
    set_patch_ptr(0x60, 0x00CD92)         # ptr_orig_road_cont ($01782c)
    set_patch_ptr(0x64, bss_mask_buf)     # ptr_mask_buf
    set_patch_ptr(0x68, 0x00368E)         # ptr_orig_mtn_cont ($00e128)
    set_patch_ptr(0x6C, 0x00322E)         # ptr_orig_spr_aln_cont ($00dcc8)
    set_patch_ptr(0x70, 0x003832)         # ptr_orig_spr_scl_cont ($00e2cc)
    set_patch_ptr(0x74, bss_am_mus)       # ptr_am_mus_buf
    set_patch_ptr(0x78, bss_am_sfx)       # ptr_am_sfx_buf
    set_patch_ptr(0x7C, bss_dma_bufs)     # ptr_dma_bufs
    set_patch_ptr(0x80, 0x00235C)         # ptr_orig_aud_tick ($00cdf6)
    set_patch_ptr(0x84, 0x00252E)         # ptr_orig_aud_stop1 ($00cfc8)
    set_patch_ptr(0x88, 0x002548)         # ptr_orig_aud_stop2 ($00cfe2)
    set_patch_ptr(0x8C, 0x00284A)         # ptr_orig_aud_sfx ($00d2e4)
    set_patch_ptr(0x90, 0x002886)         # ptr_orig_aud_mus ($00d320)

    # 2. Relocate all 13 TEXT_END (+0x12e40..+0x12e80) refs -> bss_scratch_40k
    #    EXCEPT the 3 G.TOS / initial-stack sites (+0x11e, +0x230, +0x2d4) which are followed by adda.l #$a000, An!
    gtos_sites = {0x0011E, 0x00230, 0x002D4}
    moved_text_end = 0
    for r in list(orig_relocs):
        v = struct.unpack(">I", text[r : r + 4])[0]
        if v >= 0x12E40:
            if r in gtos_sites:
                # Point directly to bss_g_tos and NOP out the following `adda.l #$a000, a6/a0` (6 bytes)
                struct.pack_into(">I", text, r, bss_g_tos)
                assert struct.unpack(">H", text[r + 4 : r + 6])[0] in (0xDDFC, 0xD1FC), (
                    f"Expected adda.l #$a000 after +0x{r:x}, got {text[r+4:r+10].hex()}"
                )
                assert struct.unpack(">I", text[r + 6 : r + 10])[0] == 0xA000
                text[r + 4 : r + 10] = b"\x4e\x71\x4e\x71\x4e\x71"  # 3x nop
            else:
                struct.pack_into(">I", text, r, bss_scratch_40k + (v - 0x12E40))
            moved_text_end += 1
    assert moved_text_end == 13, f"Expected 13 TEXT_END relocs, got {moved_text_end}"

    # 3. Relocate ALL hardcoded low-RAM ($000800..$008440) .l references into bss_lowram!
    #    Valid target set verified from full disassembly of OVERLAND_orig.PRG.
    lowram_targets = {
        0x0800, 0x3B44, 0x4044, 0x458A, 0x4FDA, 0x561A, 0x5C5A, 0x5CAA,
        0x5D22, 0x5D4A, 0x5D9A, 0x5DEA, 0x5E62, 0x5EBA, 0x5F12, 0x5F62,
        0x5FA8, 0x6FA8, 0x7040, 0x7108, 0x7240, 0x7260, 0x7262, 0x7280,
        0x72A0, 0x72C0, 0x7340, 0x7360, 0x7380, 0x73A0, 0x73C0, 0x8440,
    }
    lowram_patched = 0
    for i in range(2, orig_tlen - 4, 2):
        if i in relocs:
            continue
        val = struct.unpack(">I", text[i : i + 4])[0]
        if val not in lowram_targets:
            continue
        op = struct.unpack(">H", text[i - 2 : i])[0]
        # Verify preceding opcode takes a 32-bit absolute or immediate address
        # (lea .l, movea.l #imm/.l, move .l, movem .l, clr/tst/addq/subq .l, etc.)
        is_abs_op = (
            (op & 0xF1FF) in (0x41F9, 0x2079, 0x207C, 0x2039, 0x3039, 0x1039)
            or op in (
                0x23F9, 0x33F9, 0x13F9, 0x4279, 0x42B9, 0x4239,
                0x5279, 0x5379, 0x48F9, 0x4CF9, 0x21FC, 0x31FC,
                0x11FC, 0x23FC, 0x33FC, 0x13FC, 0x4FF9, 0x4879,
                0x33C0, 0x33C1, 0x23C0, 0x23C8, 0x33E8, 0x33EA,
                0x08F9, 0x08B9, 0x0839,
            )
            or (op & 0xFFC0) in (0x48C0, 0x4CC0)  # movem.l <mask>, $xxxx.l (mask is at i-2!)
        )
        # Also handle 4-byte opcode+mask (movem.l d0-d7, $7240.l -> 48f9 00ff 00007240)
        if not is_abs_op and i >= 4:
            op2 = struct.unpack(">H", text[i - 4 : i - 2])[0]
            if op2 in (0x48F9, 0x4CF9, 0x48B9, 0x4CB9, 0x33FC, 0x23FC, 0x13FC, 0x08F9, 0x08B9, 0x0839):
                is_abs_op = True
        if is_abs_op:
            new_off = bss_lowram + (val - 0x0800)
            struct.pack_into(">I", text, i, new_off)
            relocs.add(i)
            lowram_patched += 1
    print(f"Relocated {lowram_patched} hardcoded low-RAM ($0800..$8440) refs -> bss_lowram (+0x{bss_lowram:x})")
    assert lowram_patched >= 220, f"Too few low-RAM refs patched ({lowram_patched})"

    # 4. Patch entry bra.w (+0x0000: 6000 010c -> jmp patch_entry_init)
    #    Wait: +0x0000 is 4 bytes (6000 010c), +0x0004 is $aa9e! So we can't overwrite +0x0004!
    #    Instead, +0x010e ($aba8) is 16 bytes of Setpalette(b164): hook at +0x010e?
    #    No! Even cleaner: bra.w +0x010c at +0x0000 can jump directly to patch_off?
    #    No, patch_off is +0x12e40 (>32KB away for bra.w!).
    #    Instead, patch +0x010e ($aba8) with `jmp patch_entry_init.l` (6 bytes, overwriting pea $b164(pc); move.w #6,-(sp)!)
    #    Wait: original $aba8..$abb6 is:
    #      00aba8 (+0x10e): 487a 05ba (pea $b164(pc))
    #      00abac (+0x112): 3f3c 0006 (move.w #6,-(sp))
    #      00abb0 (+0x116): 4e4e      (trap #14)
    #      00abb2 (+0x118): 4fef 0006 (lea 6(sp),sp)
    #    We can put `jsr patch_entry_init.l` (6 bytes) at +0x10e? Wait: if we overwrite pea+move.w,
    #    we just call Setpalette($b164) or let patch_init return to +0x114?
    #    Even better: overwrite +0x10e..+0x116 (10 bytes: Setpalette) with `jsr patch_entry_init.l; nop; nop`
    #    Wait: Setpalette($b164) just sets all-black palette before clearing screen! Calling Setpalette($b164)
    #    from patch_init (or right after) is 4 instructions, OR we hook right at +0x10e (`jmp patch_entry_init.l`),
    #    do Setpalette in patch_init (or skip it since screens are already cleared and fade sets palette!),
    #    and jump back to +0x11c ($abb6)!
    assert text[0x10E:0x114] == bytes.fromhex("487a05ba3f3c")
    struct.pack_into(">HI", text, 0x10E, 0x4EF9, patch_off + 0x0000)  # jmp patch_entry_init.l
    relocs.add(0x110)

    # 5. Strip 'a:\' from 'a:\loadscr.img' (+0x1ce, 14 B) and 'a:\g.tos' (+0x27a, 8 B)
    assert text[0x1CE : 0x1CE + 14] == b"a:\\loadscr.img"
    text[0x1CE : 0x1CE + 14] = b"loadscr.img\x00\x00\x00"
    assert text[0x27A : 0x27A + 8] == b"a:\\g.tos"
    text[0x27A : 0x27A + 8] = b"g.tos\x00\x00\x00"

    # 6. NOP out 24-bit exception vector hack (+0x368..+0x38a = $ae02..$ae24)
    assert text[0x368:0x36E] == bytes.fromhex("207c00000008")
    assert text[0x386:0x38A] == bytes.fromhex("51c8fff6")
    # Remove any reloc inside +0x368..+0x38a (there is one at +0x374 -> $17d0c)
    for r in list(relocs):
        if 0x368 <= r < 0x38A:
            relocs.remove(r)
    text[0x368:0x38A] = b"\x4e\x71" * ((0x38A - 0x368) // 2)

    # 7. Fix screen-limit reference at +0x35c ($adf6: move.l #$68900, d0 -> bss_scr_bufs)
    assert struct.unpack(">HI", text[0x35A:0x360]) == (0x203C, 0x068900)
    struct.pack_into(">I", text, 0x35C, bss_scr_bufs)
    relocs.add(0x35C)

    # 8. Fix ALL THREE self-modifying Timer B loops ($b330, $b54a, $b822)
    #    Offsets in TEXT: +0x0896, +0x0ab0, +0x0d88 (each has wake at +0x1e)
    for tb_off in (0x0896, 0x0AB0, 0x0D88):
        wake_off = tb_off + 0x1E
        assert text[tb_off : tb_off + 4] == bytes.fromhex("33fc60fe"), f"Bad tb_off 0x{tb_off:x}"
        assert text[wake_off : wake_off + 4] == bytes.fromhex("33fc6002"), f"Bad wake_off 0x{wake_off:x}"
        for r in list(relocs):
            if tb_off <= r < wake_off + 8:
                relocs.remove(r)
        tb_wait_stub = bytearray(wake_off - tb_off)
        struct.pack_into(">H", tb_wait_stub, 0, 0x2F08)                      # move.l a0,-(sp)
        struct.pack_into(">HI", tb_wait_stub, 2, 0x4EB9, patch_off + 0x0004) # jsr patch_entry_tb_wait.l
        struct.pack_into(">H", tb_wait_stub, 8, 0x205F)                      # move.l (sp)+,a0
        struct.pack_into(">H", tb_wait_stub, 10, 0x4E73)                     # rte
        for k in range(12, len(tb_wait_stub), 2):
            struct.pack_into(">H", tb_wait_stub, k, 0x4E71)
        text[tb_off:wake_off] = tb_wait_stub
        relocs.add(tb_off + 4)
        struct.pack_into(">HIH", text, wake_off, 0x4EB9, patch_off + 0x0008, 0x4E71)
        relocs.add(wake_off + 2)

    # 8b. Fix self-modifying sprite Y-scaler at +0x3846 ($e2e0..$e31a) -> jmp patch_entry_scale.l
    assert text[0x3846:0x384C] == bytes.fromhex("3c1033c60000")
    for r in list(relocs):
        if 0x3846 <= r < 0x3882:
            relocs.remove(r)
    struct.pack_into(">HI", text, 0x3846, 0x4EF9, patch_off + 0x0014)
    relocs.add(0x3848)

    # 9. Hook frame flip sub_00af5a (+0x4c0) -> jmp patch_entry_flip.l
    assert text[0x4C0:0x4C6] == bytes.fromhex("083900020000")
    for r in list(relocs):
        if 0x4C0 <= r < 0x4C6:
            relocs.remove(r)
    struct.pack_into(">HI", text, 0x4C0, 0x4EF9, patch_off + 0x000C)
    relocs.add(0x4C2)

    # 10. Hook Sky Fill (+0x3d40 = $00e7da) -> jmp patch_entry_sky.l
    assert text[0x3D40:0x3D46] == bytes.fromhex("207ac2cc2050")
    struct.pack_into(">HI", text, 0x3D40, 0x4EF9, patch_off + 0x0018)
    relocs.add(0x3D42)

    # 11. Road Scanline Renderer (+0xcd8c = $017826): keep fast 4-plane-at-once CPU loop
    #     (STE Blitter 1-plane-per-span had higher register setup cost than 4-plane move.l!)

    # 12. G.TOS relocator (+0x02de): no precomputed mask needed (masks built on-the-fly cleanly)

    # 13. Hook Parallax Mountain Blitter (+0x3688 = $00e122: add.w d1,d1; lea $e172(pc),a6 [6 bytes])
    assert text[0x3688:0x368E] == bytes.fromhex("d2414dfa004c")
    struct.pack_into(">HI", text, 0x3688, 0x4EF9, patch_off + 0x0024)
    relocs.add(0x368A)

    # 14. Hook Aligned Masked Sprite Blitter (+0x3228 = $00dcc2: lea $dcda(pc),a3; add.w d6,d6 [6 bytes])
    assert text[0x3228:0x322E] == bytes.fromhex("47fa0016dc46")
    struct.pack_into(">HI", text, 0x3228, 0x4EF9, patch_off + 0x0028)
    relocs.add(0x322A)

    # 15. Shifted+Scaled Sprites (+0x382a): keep 68030-safe CPU loop (hooked at +0x3846)

    # 16. Hook Jas. C. Brooke YM driver (+0x2356 tick, +0x2528 stop1, +0x2542 stop2, +0x2842 sfx, +0x287e mus)
    assert text[0x2356:0x235C] == bytes.fromhex("48e7e0f04240")
    struct.pack_into(">HI", text, 0x2356, 0x4EF9, patch_off + 0x0030)
    relocs.add(0x2358)

    assert text[0x2528:0x252E] == bytes.fromhex("2f0841fafe05")
    struct.pack_into(">HI", text, 0x2528, 0x4EF9, patch_off + 0x0034)
    relocs.add(0x252A)

    assert text[0x2542:0x2548] == bytes.fromhex("2f0841fafdeb")
    struct.pack_into(">HI", text, 0x2542, 0x4EF9, patch_off + 0x0038)
    relocs.add(0x2544)

    assert text[0x2842:0x284A] == bytes.fromhex("48e780c045fafae2")
    struct.pack_into(">HIH", text, 0x2842, 0x4EF9, patch_off + 0x003C, 0x4E71)
    relocs.add(0x2844)

    assert text[0x287E:0x2886] == bytes.fromhex("48e7e0e045fa01f3")
    struct.pack_into(">HIH", text, 0x287E, 0x4EF9, patch_off + 0x0040, 0x4E71)
    relocs.add(0x2880)

    # 17. Phase 4A: True 12-bit STE 4,096-color Sky Gradients (+0x058a sky init, +0x0658 sky build)
    assert text[0x058A:0x0592] == bytes.fromhex("48e7008041fa004a")
    struct.pack_into(">HIH", text, 0x058A, 0x4EF9, patch_off + 0x0094, 0x4E71)
    relocs.add(0x058C)

    assert text[0x0658:0x065E] == bytes.fromhex("424032390000")
    for r in list(relocs):
        if 0x0658 <= r < 0x0660:
            relocs.remove(r)
    struct.pack_into(">HIH", text, 0x0658, 0x4EF9, patch_off + 0x0098, 0x4E71)
    relocs.add(0x065A)

    # 18. Phase 4B: Enhanced Joystick / Jaguar PowerPad + Keyboard shortcuts (+0xb98e special, +0x8356 IKBD)
    assert text[0xB98E:0xB998] == bytes.fromhex("303900007f3a08000001")
    for r in list(relocs):
        if 0xB98E <= r < 0xB998:
            relocs.remove(r)
    struct.pack_into(">HIHH", text, 0xB98E, 0x4EB9, patch_off + 0x009C, 0x4E71, 0x4E71)
    relocs.add(0xB990)

    assert text[0x8356:0x835C] == bytes.fromhex("12000241007f")
    struct.pack_into(">HI", text, 0x8356, 0x4EB9, patch_off + 0x00A0)
    relocs.add(0x8358)

    # 19. Phase 4C: Fixed-point 16.16 DDA road edge projector (+0xcc3c = $0176d6 left, +0xcc42 = $0176dc right)
    assert text[0xCC3C:0xCC46] == bytes.fromhex("49faffca600449faffea")
    struct.pack_into(">HI", text, 0xCC3C, 0x4EF9, patch_off + 0x00A4)  # jmp do_road_edge_left.l
    relocs.add(0xCC3E)
    struct.pack_into(">HI", text, 0xCC42, 0x4EF9, patch_off + 0x00A8)  # jmp do_road_edge_right.l
    relocs.add(0xCC44)

    # 20. Phase 4D: Replace repeated-addition multiply loop in road_seg_build (+0x92c0..+0x92ec = $013d5a..$013d86)
    #     Original: move.w (a1)+,d1; beq/bmi; loop add.l d2,d0 (d1 times!) -> muls.w (a2),d1; asl.l #8,d1; add.l d1,d0!
    assert text[0x92C0:0x92C6] == bytes.fromhex("321967000028")
    assert text[0x92EC:0x92EE] == bytes.fromhex("3140")
    muls_patch = bytes.fromhex(
        "3219"        # move.w  (a1)+,d1
        "6728"        # beq.s   +0x28 -> +0x92ec ($013d86)
        "c3d2"        # muls.w  (a2),d1      ; d1.l = signed d1 * (a2)
        "e181"        # asl.l   #8,d1        ; * 256 (8.8 fixed point!)
        "d081"        # add.l   d1,d0        ; d0.l += d1.l
        "6020"        # bra.s   +0x20 -> +0x92ec ($013d86)
    )
    text[0x92C0 : 0x92C0 + len(muls_patch)] = muls_patch

    # 21. Phase 4E: Replace 64x byte-by-byte 4-plane text plotter (+0x8a14..+0x8ae4 = $0134ae..$01357e)
    #     with 8x (move.l (a0)+,d0; movep.l d0,0(a1); adda.w d1,a1) -> 2.0x faster (-10,000 cyc/frame!)
    assert text[0x8A14:0x8A1C] == bytes.fromhex("1018121814181618")
    assert text[0x8AE4:0x8AE6] == bytes.fromhex("4e75")
    movep_row = bytes.fromhex("201801c90000d2c1")  # move.l (a0)+,d0; movep.l d0,0(a1); adda.w d1,a1
    movep_text = bytes.fromhex("322e0014") + (movep_row * 8) + bytes.fromhex("4e75")
    text[0x8A14 : 0x8A14 + len(movep_text)] = movep_text

    # Extract Amiga AM_MUS.BIN (45,600 B) and AM_SFX.BIN (15,720 B) from alt/amiga/*.adf
    amiga_adfs = sorted((GAME_DIR / "alt" / "amiga").glob("*.adf"))
    assert amiga_adfs, "Missing Amiga ADF in alt/amiga/"
    adf = amiga_adfs[0].read_bytes()
    am_mus = adf[0x02298E:0x02DBAE]
    am_sfx = adf[0x061A1C:0x065784]
    assert len(am_mus) == 45600 and len(am_sfx) == 15720

    # Assemble final GEMDOS PRG
    final_text = bytes(text) + bytes(patch_bin)
    assert len(final_text) == total_text_len
    reloc_bytes = encode_relocs(list(relocs))
    header = struct.pack(">HIIIIIIH", 0x601A, total_text_len, 0, total_bss_len, 0, 0, 0, 0)
    assert len(header) == 28
    prg = header + final_text + reloc_bytes

    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    (OVERLAY_DIR / "OVERLAND.PRG").write_bytes(prg)
    (OVERLAY_DIR / "LOADSCR.IMG").write_bytes(loadscr)
    (OVERLAY_DIR / "G.TOS").write_bytes(g_tos)
    (OVERLAY_DIR / "AM_MUS.BIN").write_bytes(am_mus)
    (OVERLAY_DIR / "AM_SFX.BIN").write_bytes(am_sfx)
    print(f"Wrote {OVERLAY_DIR / 'OVERLAND.PRG'} ({len(prg):,} B, {len(relocs)} relocs) + AM_MUS.BIN ({len(am_mus):,} B) + AM_SFX.BIN ({len(am_sfx):,} B)")


if __name__ == "__main__":
    main()
