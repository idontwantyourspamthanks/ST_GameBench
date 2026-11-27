#!/usr/bin/env python3
"""
Seconds Out (1988, Tynesoft) — Enhanced STE Builder & Patcher (v1.0)

Verifies original disk image MD5, extracts assets to dist/hd/, assembles
patches/loader.s and patches/engine.s with vasmm68k_mot, verifies every
original byte at every hook site, and builds:
  - dist/hd/SECONDS.PRG (native GEMDOS HD install, + RUNME.TOS copy for harness)
  - dist/SecondsOut_Enhanced_v1.0.st (auto-booting 720 KB FAT12 floppy image)
"""
import argparse
import hashlib
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path

VERSION = "1.3"
GAME_DIR = Path(__file__).resolve().parent.parent
ORIG_ST = GAME_DIR / "originals" / "Seconds Out (1988)(Tynesoft).st"
ORIG_ST_MD5 = "ea7f80595ef3f30a269cec5642d5db6a"

GAME_BASE = 0x00080000
PATCH_BASE = 0x00088000


def extract_fat12(st_path: Path) -> dict[str, bytes]:
    data = st_path.read_bytes()
    bps = struct.unpack_from("<H", data, 11)[0]
    spc = data[13]
    res = struct.unpack_from("<H", data, 14)[0]
    nfats = data[16]
    nroot = struct.unpack_from("<H", data, 17)[0]
    spf = struct.unpack_from("<H", data, 22)[0]
    fat_off = res * bps
    root_off = (res + nfats * spf) * bps
    data_off = root_off + nroot * 32

    def next_cluster(cl):
        byte_off = fat_off + (cl * 3) // 2
        val = struct.unpack_from("<H", data, byte_off)[0]
        return (val >> 4) if (cl & 1) else (val & 0xFFF)

    def read_chain(cl, size=None):
        out = bytearray()
        while 2 <= cl < 0xFF8:
            off = data_off + (cl - 2) * spc * bps
            out.extend(data[off : off + spc * bps])
            cl = next_cluster(cl)
        return bytes(out[:size] if size is not None else out)

    files = {}

    def walk_dir(buf, prefix=""):
        for i in range(0, len(buf), 32):
            e = buf[i : i + 32]
            if len(e) < 32 or e[0] == 0:
                break
            if e[0] == 0xE5 or e[11] == 0x0F or (e[11] & 0x08):
                continue
            name = e[:8].decode("ascii", "replace").strip()
            ext = e[8:11].decode("ascii", "replace").strip()
            if name in (".", ".."):
                continue
            fname = f"{name}.{ext}" if ext else name
            if not name:
                fname = f"EMPTY.{ext}"
            rel = f"{prefix}{fname}"
            cl = struct.unpack_from("<H", e, 26)[0]
            size = struct.unpack_from("<I", e, 28)[0]
            if e[11] & 0x10:
                walk_dir(read_chain(cl), f"{rel}/")
            else:
                files[rel] = read_chain(cl, size)

    walk_dir(data[root_off:data_off])
    return files


def parse_tos_prg(raw: bytes):
    assert raw[:2] == b"\x60\x1a", "Not a TOS PRG"
    tlen, dlen, blen, slen = struct.unpack_from(">IIII", raw, 2)
    text = raw[28 : 28 + tlen + dlen]
    reloc_off = 28 + tlen + dlen + slen
    relocs = []
    if reloc_off + 4 <= len(raw):
        pos = struct.unpack_from(">I", raw, reloc_off)[0]
        if pos != 0:
            relocs.append(pos)
            i = reloc_off + 4
            while i < len(raw) and raw[i] != 0:
                b = raw[i]
                i += 1
                if b == 1:
                    pos += 254
                else:
                    pos += b
                    relocs.append(pos)
    return text, relocs


def assemble_bin(src: Path, out: Path):
    cmd = ["vasmm68k_mot", "-Fbin", "-m68000", "-o", str(out), str(src)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr, file=sys.stderr)
        raise SystemExit(f"vasm failed on {src}")
    return out.read_bytes()


def jmp_abs(addr: int) -> bytes:
    return b"\x4e\xf9" + struct.pack(">I", addr)


def jsr_abs(addr: int) -> bytes:
    return b"\x4e\xb9" + struct.pack(">I", addr)


def _unpack_csp(raw: bytes) -> bytearray:
    out = bytearray()
    i = 0
    while i < len(raw) and len(out) < 0x7D00:
        b = raw[i]
        i += 1
        if b == 0:
            if i >= len(raw):
                break
            cnt = raw[i]
            i += 1
            out.extend(b"\x00" * (256 if cnt == 0 else cnt))
        else:
            out.append(b)
    return out[:0x7D00]


def _pack_csp(buf: bytearray) -> bytes:
    out = bytearray()
    i = 0
    n = len(buf)
    while i < n:
        if buf[i] == 0:
            run = 0
            while i < n and buf[i] == 0 and run < 256:
                run += 1
                i += 1
            out.append(0)
            out.append(0 if run == 256 else run)
        else:
            out.append(buf[i])
            i += 1
    return bytes(out)


def repair_csp_bad_sectors(name: str, raw: bytes) -> bytes:
    """Repair two single-sector RLE desyncs baked into the original .ST dump (B1C.CSP & B2B.CSP)."""
    if name == "B1C.CSP":
        # Bonecrusher Jones knockdown row: y=53..68 shifted +2 bytes (yellow shorts), y=73..99 shifted +8 bytes (feet 16px right)
        buf = _unpack_csp(raw)
        fix = bytearray(buf)
        fix[53 * 160 : 69 * 160] = buf[53 * 160 + 2 : 69 * 160 + 2]
        fix[73 * 160 : 100 * 160] = buf[73 * 160 + 8 : 100 * 160 + 8]
        for dst_y, src_y in ((52, 51), (69, 68), (70, 68), (71, 73), (72, 73)):
            fix[dst_y * 160 : (dst_y + 1) * 160] = fix[src_y * 160 : (src_y + 1) * 160]
        return _pack_csp(fix)
    if name == "B2B.CSP":
        # Hammerhead Hagman bottom row (portrait + punches) had 5 RLE desync bands (+2/+6/+8/+10/+14)
        buf = _unpack_csp(raw)
        fix = bytearray(buf)
        for y0, y1, d in ((119, 124, 2), (126, 130, 6), (131, 141, 8), (142, 146, 10), (148, 200, 14)):
            s0, s1 = y0 * 160, y1 * 160
            seg = buf[s0 + d : s1 + d]
            if len(seg) < s1 - s0:
                seg = seg + b"\x00" * ((s1 - s0) - len(seg))
            fix[s0:s1] = seg
        # Clean the 1-2px transition seams from adjacent clean scanlines
        fix[118 * 160 : 118 * 160 + 120] = fix[117 * 160 : 117 * 160 + 120]
        for dst_y, src_y in ((124, 123), (125, 126), (130, 129), (141, 140), (146, 145), (147, 148)):
            fix[dst_y * 160 : (dst_y + 1) * 160] = fix[src_y * 160 : (src_y + 1) * 160]
        return _pack_csp(fix)
    return raw


def build_tos_prg(text_bytes: bytes) -> bytes:
    hdr = struct.pack(">HIIIIIIH", 0x601A, len(text_bytes), 0, 0, 0, 0, 0, 0)
    return hdr + text_bytes + b"\x00\x00\x00\x00"


def build_fat12_floppy(hd_dir: Path, out_st: Path):
    """Build an auto-booting 720 KB FAT12 Atari ST floppy image with AUTO/SECONDS.PRG."""
    # Standard 80 tracks, 2 sides, 9 spt = 1440 sectors = 737,280 bytes
    bps = 512
    spc = 2
    res = 1
    nfats = 2
    nroot = 112
    tot = 1440
    spf = 5
    img = bytearray(tot * bps)

    # Boot sector (non-executable standard Atari ST BPB, checksum != $1234 -> TOS boots AUTO/)
    img[0:2] = b"\x60\x38"
    img[2:8] = b"SECOUT"
    struct.pack_into("<H", img, 11, bps)
    img[13] = spc
    struct.pack_into("<H", img, 14, res)
    img[16] = nfats
    struct.pack_into("<H", img, 17, nroot)
    struct.pack_into("<H", img, 19, tot)
    img[21] = 0xF9
    struct.pack_into("<H", img, 22, spf)
    struct.pack_into("<H", img, 24, 9)
    struct.pack_into("<H", img, 26, 2)

    fat_off = res * bps
    root_off = (res + nfats * spf) * bps
    data_off = root_off + nroot * 32

    fat = [0] * 720
    fat[0] = 0xFF9
    fat[1] = 0xFFF
    next_cl = 2

    def alloc_file(content: bytes) -> int:
        nonlocal next_cl
        if not content:
            return 0
        csize = spc * bps
        ncl = (len(content) + csize - 1) // csize
        first = next_cl
        for k in range(ncl):
            cl = next_cl
            next_cl += 1
            fat[cl] = next_cl if k + 1 < ncl else 0xFFF
            chunk = content[k * csize : (k + 1) * csize]
            off = data_off + (cl - 2) * csize
            img[off : off + len(chunk)] = chunk
        return first

    def make_dirent(name8: str, ext3: str, attr: int, cl: int, size: int) -> bytes:
        e = bytearray(32)
        e[0:8] = name8.upper().ljust(8)[:8].encode("ascii")
        e[8:11] = ext3.upper().ljust(3)[:3].encode("ascii")
        e[11] = attr
        struct.pack_into("<H", e, 26, cl)
        struct.pack_into("<I", e, 28, size)
        return bytes(e)

    # Create AUTO directory cluster with SECONDS.PRG
    prg_bytes = (hd_dir / "SECONDS.PRG").read_bytes()
    prg_cl = alloc_file(prg_bytes)
    auto_cl = next_cl
    next_cl += 1
    fat[auto_cl] = 0xFFF
    auto_buf = bytearray(spc * bps)
    auto_buf[0:32] = make_dirent(".", "", 0x10, auto_cl, 0)
    auto_buf[32:64] = make_dirent("..", "", 0x10, 0, 0)
    auto_buf[64:96] = make_dirent("SECONDS", "PRG", 0x00, prg_cl, len(prg_bytes))
    img[data_off + (auto_cl - 2) * spc * bps : data_off + (auto_cl - 1) * spc * bps] = auto_buf

    root_idx = 0
    img[root_off + root_idx * 32 : root_off + (root_idx + 1) * 32] = make_dirent("AUTO", "", 0x10, auto_cl, 0)
    root_idx += 1

    # Add all asset files (except RUNME.TOS & SECONDS.PRG) to root
    for p in sorted(hd_dir.iterdir()):
        if not p.is_file() or p.name in ("RUNME.TOS", "SECONDS.PRG"):
            continue
        stem, dot, ext = p.name.partition(".")
        raw = p.read_bytes()
        cl = alloc_file(raw)
        img[root_off + root_idx * 32 : root_off + (root_idx + 1) * 32] = make_dirent(stem, ext, 0x00, cl, len(raw))
        root_idx += 1

    # Pack FAT12 into both FAT copies
    fat_bytes = bytearray(spf * bps)
    for cl in range(0, len(fat), 2):
        v0 = fat[cl] & 0xFFF
        v1 = fat[cl + 1] & 0xFFF if cl + 1 < len(fat) else 0
        bo = (cl * 3) // 2
        if bo + 2 < len(fat_bytes):
            fat_bytes[bo] = v0 & 0xFF
            fat_bytes[bo + 1] = ((v0 >> 8) & 0x0F) | ((v1 & 0x0F) << 4)
            fat_bytes[bo + 2] = (v1 >> 4) & 0xFF
    img[fat_off : fat_off + len(fat_bytes)] = fat_bytes
    img[fat_off + spf * bps : fat_off + 2 * spf * bps] = fat_bytes

    out_st.write_bytes(img)
    print(f"Built floppy {out_st} ({len(img):,} B, used {next_cl-2}/713 clusters)")


def build(uncouple: bool = True, use_blitter: bool = True, tween: bool = True):
    if not ORIG_ST.exists():
        raise SystemExit(f"Missing original disk image: {ORIG_ST}")
    st_md5 = hashlib.md5(ORIG_ST.read_bytes()).hexdigest()
    if st_md5 != ORIG_ST_MD5:
        raise SystemExit(f"MD5 mismatch on {ORIG_ST}: got {st_md5}, expected {ORIG_ST_MD5}")

    files = extract_fat12(ORIG_ST)
    orig_prg = files["AUTO/EMPTY.PRG"]
    orig_text, relocs = parse_tos_prg(orig_prg)
    assert len(orig_text) == 0x5332

    work_dir = GAME_DIR / "work" / "build"
    work_dir.mkdir(parents=True, exist_ok=True)
    loader_bin = assemble_bin(GAME_DIR / "patches" / "loader.s", work_dir / "loader.bin")
    engine_bin = bytearray(assemble_bin(GAME_DIR / "patches" / "engine.s", work_dir / "engine.bin"))

    # Config words at PATCH_BASE + $9c
    cfg_off = 0x9C
    assert engine_bin[cfg_off : cfg_off + 6] == bytes.fromhex("000100010001"), (
        f"Unexpected cfg bytes at +0x{cfg_off:x}: {engine_bin[cfg_off:cfg_off+6].hex()}"
    )
    struct.pack_into(">HHH", engine_bin, cfg_off, int(use_blitter), int(uncouple), int(tween))

    hooks_spec = [
        # HD compatibility
        (0x007E, b"a:.tos\x00", b"b.tos\x00\x00"),
        (0x02CE, bytes.fromhex("42673f3c000e4e41588f"), b"\x4e\x71" * 5),
        (0x44D2, bytes.fromhex("3f3c00003f3c000e4e41588f"), b"\x4e\x71" * 6),
        # Shorten 11-second splash busy-wait ($550000 -> $080000)
        (0x4C72, bytes.fromhex("203c00550000"), bytes.fromhex("203c00080000")),
        # Phase 1: Mask cache + STE Blitter + Uncoupled 50 Hz loop
        (0x02B8, bytes.fromhex("4eb9000045bc"), jsr_abs(PATCH_BASE + 0x00)),
        (0x455A, bytes.fromhex("4eb900005004"), jsr_abs(PATCH_BASE + 0x04)),
        (0x10B6, bytes.fromhex("41f900057cd0"), jmp_abs(PATCH_BASE + 0x08)),
        (0x10EC, bytes.fromhex("41f900057cd0"), jmp_abs(PATCH_BASE + 0x0C)),
        (0x0BC4, bytes.fromhex("33c600000cb8"), jmp_abs(PATCH_BASE + 0x10)),
        (0x1BFA, bytes.fromhex("33c600000cb8"), jmp_abs(PATCH_BASE + 0x14)),
        (0x0506, bytes.fromhex("303900000004"), jmp_abs(PATCH_BASE + 0x18)),
        (0x241A, bytes.fromhex("e54841f90000243a"), jmp_abs(PATCH_BASE + 0x1C) + b"\x4e\x71"),
        # Phase 2 & 3: Stamina, Fatigue, AI Rebalance, 2P Mode, Career Styles, Title Menu
        (0x03D6, bytes.fromhex("33fc003f00002d4a33fc003f00002d4c"), jmp_abs(PATCH_BASE + 0x20) + b"\x4e\x71" * 5),
        (0x047A, bytes.fromhex("4eb9000021e8"), jsr_abs(PATCH_BASE + 0x24)),
        (0x2D24, bytes.fromhex("e54841f90000534e"), jmp_abs(PATCH_BASE + 0x28) + b"\x4e\x71"),
        (0x134C, bytes.fromhex("41f900002bf8"), jmp_abs(PATCH_BASE + 0x2C)),
        (0x1392, bytes.fromhex("d17900001166"), jmp_abs(PATCH_BASE + 0x30)),
        (0x13A8, bytes.fromhex("917900001166"), jmp_abs(PATCH_BASE + 0x34)),
        (0x1568, bytes.fromhex("41f900002bf8"), jmp_abs(PATCH_BASE + 0x38)),
        (0x159C, bytes.fromhex("41f900002bf8"), jmp_abs(PATCH_BASE + 0x3C)),
        (0x15D2, bytes.fromhex("41f900002bf8"), jmp_abs(PATCH_BASE + 0x40)),
        (0x1736, bytes.fromhex("537900002d4a4eb900002d4e"), jmp_abs(PATCH_BASE + 0x44) + b"\x4e\x71" * 3),
        (0x1780, bytes.fromhex("537900002d4a4eb900002d4e"), jmp_abs(PATCH_BASE + 0x48) + b"\x4e\x71" * 3),
        (0x1B72, bytes.fromhex("33fcffff00002f56"), jmp_abs(PATCH_BASE + 0x4C) + b"\x4e\x71"),
        (0x1A9E, bytes.fromhex("5779000016d4"), jmp_abs(PATCH_BASE + 0x50)),
        (0x1ABC, bytes.fromhex("5679000016d4"), jmp_abs(PATCH_BASE + 0x54)),
        (0x2B44, bytes.fromhex("3c3070149d7900002d4c"), jmp_abs(PATCH_BASE + 0x58) + b"\x4e\x71" * 2),
        (0x38A6, bytes.fromhex("3c3070309d7900002d4a"), jmp_abs(PATCH_BASE + 0x5C) + b"\x4e\x71" * 2),
        (0x2BB8, bytes.fromhex("2f3c000034fe"), jmp_abs(PATCH_BASE + 0x60)),
        (0x3912, bytes.fromhex("4a790000374c"), jmp_abs(PATCH_BASE + 0x64)),
        (0x360C, bytes.fromhex("4a7900003600"), jmp_abs(PATCH_BASE + 0x68)),
        (0x4AB8, bytes.fromhex("4a7900002f5a"), jmp_abs(PATCH_BASE + 0x6C)),
        (0x1D54, bytes.fromhex("223c00068300"), jmp_abs(PATCH_BASE + 0x70)),
        (0x1DA6, bytes.fromhex("08390007000007e4"), jmp_abs(PATCH_BASE + 0x74) + b"\x4e\x71"),
        (0x1E7A, bytes.fromhex("08390007000007e4"), jmp_abs(PATCH_BASE + 0x78) + b"\x4e\x71"),
        (0x40AC, bytes.fromhex("4a3900004110"), jmp_abs(PATCH_BASE + 0x7C)),
        # Fix 68030 I-cache crash on TT/Falcon: replace self-modifying jsr $ffffffff at $14ea
        # with clean indirect `movea.l (a0,d1.w),a0; jsr (a0)`!
        (0x14EA, bytes.fromhex("23f01000000014f44eb9ffffffff"),
                 bytes.fromhex("207010004e904e714e714e714e71")),
        # Between-fights Newspaper screen at $0708 (replaces jsr $1cf4.l)
        (0x0708, bytes.fromhex("4eb900001cf4"), jsr_abs(PATCH_BASE + 0x80)),
        # Slow down health regeneration (P1 passive regen 6->80 ticks, CPU between-round +16->+6 HP)
        (0x19F6, bytes.fromhex("0006"), bytes.fromhex("0050")),
        (0x0482, bytes.fromhex("0010"), bytes.fromhex("0006")),
        # 2P Mode Tug-of-War KO Gauge with dual KO gloves ($2262 draw, $2b8e P1 hit pull)
        (0x2262, bytes.fromhex("303c000941f900071758"), jmp_abs(PATCH_BASE + 0x84) + b"\x4e\x71" * 2),
        (0x2B8E, bytes.fromhex("0c7900090000225e"), jmp_abs(PATCH_BASE + 0x88) + b"\x4e\x71"),
        # Skip Trainer mini-game between rounds in 2P Versus mode ($060c)
        (0x060C, bytes.fromhex("4eb900004c98"), jsr_abs(PATCH_BASE + 0x8C)),
        # Allow P1 Super (Fire+Up) from either High or Low stance (NOP bne at $1b58)
        (0x1B58, bytes.fromhex("6600ffc0"), b"\x4e\x71\x4e\x71"),
        # Race-free Joy 1 capture ($4108: move.b d0,$7e4.l)
        (0x4108, bytes.fromhex("13c0000007e4"), jmp_abs(PATCH_BASE + 0x90)),
        # Low stamina increases knockdown floor count & KO risk ($2f6e P2, $3a74 P1)
        (0x2F6E, bytes.fromhex("b07900003a62"), jmp_abs(PATCH_BASE + 0x94)),
        (0x3A74, bytes.fromhex("b07900003be8"), jmp_abs(PATCH_BASE + 0x98)),
        # Malone "WELL DONE" screen: allow Joy1 Fire / auto-exit ($46c0) & preserve G_WIN ($472e)
        (0x46C0, bytes.fromhex("4a790000425c"), jsr_abs(PATCH_BASE + 0xA8)),
        (0x472E, bytes.fromhex("427900003a5e"), b"\x4e\x71" * 3),
    ]

    # Strip \r before \0 in all filename strings
    for off in list(range(0x85, 0xD1)) + list(range(0x15A, 0x175)):
        if orig_text[off] == 0x0D and orig_text[off + 1] == 0x00:
            hooks_spec.append((off, b"\x0d", b"\x00"))

    hook_blob = bytearray()
    for off, exp, rep in hooks_spec:
        actual = orig_text[off : off + len(exp)]
        if actual != exp:
            raise SystemExit(
                f"Verify FAILED at $0x{off:04x}: expected {exp.hex()}, got {actual.hex()}"
            )
        assert len(exp) == len(rep), f"Length mismatch at $0x{off:04x}"
        hook_blob.extend(struct.pack(">IH", GAME_BASE + off, len(rep)))
        hook_blob.extend(rep)
        if len(rep) & 1:
            hook_blob.append(0)

    if len(engine_bin) & 1:
        engine_bin.append(0)
    payload = bytearray()
    payload.extend(loader_bin)
    payload.extend(struct.pack(">IIII", len(orig_text), len(relocs), len(engine_bin), len(hooks_spec)))
    payload.extend(orig_text)
    for r in relocs:
        payload.extend(struct.pack(">I", r))
    payload.extend(engine_bin)
    payload.extend(hook_blob)

    out_prg = build_tos_prg(bytes(payload))

    hd_dir = GAME_DIR / "dist" / "hd"
    hd_dir.mkdir(parents=True, exist_ok=True)
    for rel, raw in files.items():
        if rel.startswith("AUTO/") or rel == "ZSEND.TOS":
            continue
        dst_name = "B.TOS" if rel == "EMPTY.TOS" else rel
        (hd_dir / dst_name).write_bytes(repair_csp_bad_sectors(dst_name, raw))
    (hd_dir / "SECONDS.PRG").write_bytes(out_prg)
    (hd_dir / "RUNME.TOS").write_bytes(out_prg)

    print(
        f"Built {hd_dir / 'SECONDS.PRG'} ({len(out_prg):,} B) "
        f"[v{VERSION}, engine={len(engine_bin)} B, hooks={len(hooks_spec)}]"
    )

    # Also build auto-booting 720 KB floppy image
    out_st = GAME_DIR / "dist" / f"SecondsOut_Enhanced_v{VERSION}.st"
    build_fat12_floppy(hd_dir, out_st)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-uncouple", action="store_true")
    ap.add_argument("--no-blitter", action="store_true")
    ap.add_argument("--no-tween", action="store_true")
    args = ap.parse_args()
    build(uncouple=not args.no_uncouple, use_blitter=not args.no_blitter, tween=not args.no_tween)


if __name__ == "__main__":
    main()
