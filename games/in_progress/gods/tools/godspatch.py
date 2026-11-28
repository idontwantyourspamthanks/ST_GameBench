#!/usr/bin/env python3
"""Gods (PP's Gamex HD build) patch builder & verifier.

Unpacks START.TOS, injects a tiny GEMDOS loader stub in its dead zero run ($804c)
that loads GODSPAT.BIN to $084000, and hooks START.TOS +$0748 (right after Gods
is unpacked into $1000-$21000 and before `jmp $140.w`) to call `jsr $084008`.
"""
from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
ORIG = GAME / "originals/GODS"
PATCHES = GAME / "patches"
BUILD = GAME / "build/game"
VASM = "vasmm68k_mot"

PB = 0x084000
STUB_OFF = 0x804C
LOAD_HOOK_OFF = 0x0246    # clr.w -(a7); lea $b4e(pc),a1 (6 bytes: 4267 43fa 0904)
STAGE2_HOOK_OFF = 0x0748  # lea $2c58.w,a1; move.w #$4ef9,(a1)+ (6 bytes: 43f8 2c58 32fc)


def lz_unpack(src: bytes) -> bytes:
    out = bytearray()
    i = 0
    while True:
        c = src[i]; i += 1
        if c == 0:
            break
        if c < 0x80:
            out += src[i:i + c]; i += c
            continue
        cnt = c & 0x3F
        if c & 0x40:
            cnt += 3
            off = (src[i] << 8) | src[i + 1]
            i += 2
        else:
            cnt += 2
            off = src[i]
            i += 1
        for _ in range(cnt + 1):
            out.append(out[-off])
    return bytes(out)


def reloc_offsets(prg: bytes) -> set[int]:
    tlen, dlen, slen = struct.unpack(">LLL", prg[2:14])[0], struct.unpack(">L", prg[6:10])[0], struct.unpack(">L", prg[14:18])[0]
    p = 28 + tlen + dlen + slen
    first = struct.unpack(">L", prg[p:p + 4])[0]
    if first == 0:
        return set()
    p += 4
    offs = {first}
    cur = first
    while prg[p] != 0:
        if prg[p] == 1:
            cur += 254
        else:
            cur += prg[p]
            offs.add(cur)
        p += 1
    return offs


def assemble(src_text: str, incdir: Path | None = None) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "in.s"
        o = Path(td) / "out.bin"
        s.write_text(src_text)
        cmd = [VASM, "-Fbin", "-m68000"]
        if incdir:
            cmd += [f"-I{incdir}"]
        cmd += ["-o", str(o), str(s)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"vasm failed:\n{r.stdout}\n{r.stderr}")
        return o.read_bytes()


def build_start_tos(orig_start: bytes) -> bytes:
    unp = bytearray(lz_unpack(orig_start[28 + 0x106:]))
    tlen = struct.unpack(">L", unp[2:6])[0]
    rels = reloc_offsets(bytes(unp))
    text_base = 28

    # Verify original bytes at hook sites and no relocation overlap
    assert bytes(unp[text_base + LOAD_HOOK_OFF : text_base + LOAD_HOOK_OFF + 6]) == bytes.fromhex("426743fa0904"), \
        "Unexpected bytes at START.TOS +$0246"
    assert bytes(unp[text_base + STAGE2_HOOK_OFF : text_base + STAGE2_HOOK_OFF + 6]) == bytes.fromhex("43f82c5832fc"), \
        "Unexpected bytes at START.TOS +$0748"
    for off in range(LOAD_HOOK_OFF, LOAD_HOOK_OFF + 6):
        assert off not in rels, f"Reloc collision at ${off:x}"
    for off in range(STAGE2_HOOK_OFF, STAGE2_HOOK_OFF + 6):
        assert off not in rels, f"Reloc collision at ${off:x}"

    # Assemble loader stub at text offset STUB_OFF
    stub_src = f"""
        org     ${STUB_OFF:x}
stub:
        movem.l d0-d7/a0-a6,-(a7)
        clr.w   -(a7)                   ; mode 0 = read-only
        pea     fname(pc)
        move.w  #$3d,-(a7)              ; Fopen
        trap    #1
        addq.l  #8,a7
        move.w  d0,d7
        bmi.s   .fail
        pea     ${PB:x}.l               ; dest = $084000
        pea     $4000.l                 ; max 16 KB
        move.w  d7,-(a7)
        move.w  #$3f,-(a7)              ; Fread
        trap    #1
        lea     12(a7),a7
        move.w  d7,-(a7)
        move.w  #$3e,-(a7)              ; Fclose
        trap    #1
        addq.l  #4,a7
        cmpi.l  #$47445350,${PB:x}.l    ; 'GDSP' magic?
        bne.s   .fail
        ; Patch START.TOS +$0748 (8 bytes: lea $2c58.w,a1; move.w #$4ef9,(a1)+)
        lea     ${STAGE2_HOOK_OFF:x}(pc),a0
        move.w  #$4eb9,(a0)+            ; jsr $084008.l
        move.l  #${PB + 8:x},(a0)+
        move.w  #$4e71,(a0)             ; nop (clears leftover #$4ef9 immediate!)
.fail:
        movem.l (a7)+,d0-d7/a0-a6
        movea.l (a7)+,a0
        clr.w   -(a7)
        lea     $0b4e(pc),a1
        jmp     (a0)
fname:
        dc.b    "GODSPAT.BIN",0
        even
"""
    stub_bin = assemble(stub_src)
    assert len(stub_bin) <= (0x83EA - STUB_OFF), f"Stub too big: {len(stub_bin)}"
    assert all(b == 0 for b in unp[text_base + STUB_OFF : text_base + STUB_OFF + len(stub_bin)]), \
        "Non-zero bytes in START.TOS stub area!"
    for off in range(STUB_OFF, STUB_OFF + len(stub_bin)):
        assert off not in rels, f"Reloc collision in stub at ${off:x}"

    unp[text_base + STUB_OFF : text_base + STUB_OFF + len(stub_bin)] = stub_bin
    # Replace +$0246 (6 bytes) with: bsr.w stub (4 bytes) + nop (2 bytes)
    disp = STUB_OFF - (LOAD_HOOK_OFF + 2)
    hook_bytes = struct.pack(">HhH", 0x6100, disp, 0x4E71)
    unp[text_base + LOAD_HOOK_OFF : text_base + LOAD_HOOK_OFF + 6] = hook_bytes

    # Add discreet "enhanced by dad_prg v1.0" credit on the Gamex startup screen
    # Replace "GAMEX: key F9" -> "STE Tier 2 - enhanced by dad_prg v1.0" in the banner?
    # Better: keep "GAMEX: key F9" intact and append credit via the dead space or replace unused padding.
    old_banner = b"Press S for unlimited stamina\r\n"
    idx = unp.find(old_banner)
    if idx >= 0:
        # Check if there is trailing padding or print via stub — actually we can safely print it right in the stub?
        # Even simpler: check the string right after old_banner in START.TOS!
        pass
    return bytes(unp)


def build(stage2_src: Path | None = None) -> None:
    stage2_src = stage2_src or (PATCHES / "stage2.s")
    pat_bin = assemble(stage2_src.read_text(), incdir=PATCHES)
    assert pat_bin[:4] == b"GDSP", "GODSPAT.BIN missing GDSP magic"
    assert len(pat_bin) <= 0x4000, f"GODSPAT.BIN too big: {len(pat_bin)}"

    start_bin = build_start_tos((ORIG / "START.TOS").read_bytes())

    if BUILD.exists():
        shutil.rmtree(BUILD)
    shutil.copytree(ORIG, BUILD)
    (BUILD / "START.TOS").write_bytes(start_bin)
    (BUILD / "GODSPAT.BIN").write_bytes(pat_bin)
    print(f"Built {BUILD}: START.TOS ({len(start_bin)} B), GODSPAT.BIN ({len(pat_bin)} B)")


if __name__ == "__main__":
    build()
