#!/usr/bin/env python3
"""Extract & unpack ENTOMBED.PRG from originals/stf30a.msa into a clean relocatable TOS PRG."""
from __future__ import annotations

import struct
from pathlib import Path

GAME_DIR = Path(__file__).resolve().parent.parent
ORIG_MSA = GAME_DIR / "originals" / "stf30a.msa"
OUT_PRG = GAME_DIR / "work" / "extracted" / "ENTOMBED_UNPACKED.PRG"


def unpack_msa(data: bytes) -> bytes:
    magic, spt, sides, start_trk, end_trk = struct.unpack(">5H", data[:10])
    assert magic == 0x0E0F, f"Bad MSA magic {magic:#x}"
    trk_len = spt * 512
    pos = 10
    out = bytearray()
    for _ in range(start_trk, end_trk + 1):
        for _ in range(sides + 1):
            (clen,) = struct.unpack_from(">H", data, pos)
            pos += 2
            chunk = data[pos : pos + clen]
            pos += clen
            if clen == trk_len:
                out.extend(chunk)
            else:
                i = 0
                dec = bytearray()
                while i < len(chunk):
                    b = chunk[i]
                    if b == 0xE5:
                        val = chunk[i + 1]
                        (cnt,) = struct.unpack_from(">H", chunk, i + 2)
                        dec.extend([val] * cnt)
                        i += 4
                    else:
                        dec.append(b)
                        i += 1
                assert len(dec) == trk_len
                out.extend(dec)
    return bytes(out)


def extract_file_from_st(img: bytes, target_path: str) -> bytes:
    bps, spc, res, nfats, nroot, nsec, media, spf, spt, nsides = struct.unpack_from(
        "<HBHBHHBHHH", img, 11
    )
    fat_off = res * bps
    root_off = (res + nfats * spf) * bps
    root_secs = (nroot * 32 + bps - 1) // bps
    data_off = root_off + root_secs * bps
    fat = img[fat_off : fat_off + spf * bps]

    def next_clus(c: int) -> int:
        idx = (c * 3) // 2
        val = struct.unpack_from("<H", fat, idx)[0]
        return (val >> 4) if (c & 1) else (val & 0xFFF)

    def read_chain(c: int) -> bytes:
        out = bytearray()
        seen = set()
        while 2 <= c < 0xFF8 and c not in seen:
            seen.add(c)
            off = data_off + (c - 2) * spc * bps
            out.extend(img[off : off + spc * bps])
            c = next_clus(c)
        return bytes(out)

    parts = [p.upper() for p in target_path.strip("/").split("/")]
    entries = img[root_off : root_off + root_secs * bps]
    for depth, want in enumerate(parts):
        found = None
        for i in range(0, len(entries), 32):
            ent = entries[i : i + 32]
            if len(ent) < 32 or ent[0] == 0:
                break
            if ent[0] == 0xE5 or ent[11] == 0x0F or (ent[11] & 0x08):
                continue
            name = ent[0:8].decode("ascii", "replace").strip()
            ext = ent[8:11].decode("ascii", "replace").strip()
            fname = f"{name}.{ext}" if ext else name
            if fname.upper() == want:
                attr = ent[11]
                clus, size = struct.unpack_from("<HI", ent, 26)
                found = (attr, clus, size)
                break
        if found is None:
            raise FileNotFoundError(f"Missing {want} in {target_path}")
        attr, clus, size = found
        if depth == len(parts) - 1:
            return read_chain(clus)[:size]
        assert attr & 0x10
        entries = read_chain(clus)
    raise AssertionError("unreachable")


def depack_entombed_prg(packed_prg: bytes) -> bytes:
    """Exact Python translation of the 0x1b2-byte depacker stub in ENTOMBED.PRG."""
    magic, tlen, dlen, blen, slen = struct.unpack_from(">HIIII", packed_prg, 0)
    assert magic == 0x601A and tlen == 0x1B2, f"Unexpected header: {magic:#x} {tlen:#x}"
    # Packed payload is the DATA segment of the outer PRG
    src = packed_prg[28 + tlen : 28 + tlen + dlen]
    # Last 12 bytes of DATA: [-12:-8] = ? , [-8:-4] = unpacked_len, [-4:] = ?
    # From 0x001c: a0 = end_of_data; a0 -= 4; unpacked_len = *(long*)(a0 -= 4); a0 -= 4;
    a0 = len(src) - 4
    a0 -= 4
    (unpacked_len,) = struct.unpack_from(">I", src, a0)
    a0 -= 4

    dst = bytearray(unpacked_len)
    a2 = unpacked_len

    d0 = 0
    while d0 == 0:
        a0 -= 1
        d0 = src[a0]

    def get_bit() -> int:
        nonlocal a0, d0
        carry = d0 & 1
        d0 >>= 1
        if d0 == 0:
            a0 -= 1
            b = src[a0]
            carry = b & 1
            d0 = (b >> 1) | 0x80
        return carry

    def get_bits(n_dbra: int) -> int:
        val = 0
        for _ in range(n_dbra + 1):
            val = (val << 1) | get_bit()
        return val

    def get_offset(d4_init: int) -> tuple[int, int]:
        # sub 0x00c4 (d4=d4_init) or 0x00c2 (d4=0)
        d2 = get_bits(1)
        d1 = ((d2 + 1) << 2) - 1
        if (d1 ^ d4_init) == 0:
            return 0, d4_init  # Z=1
        return get_bits(d1), d4_init  # Z=0 (Wait: let's check Z flag!)

    while a2 > 0:
        if not get_bit():
            # 0x003c: literal byte
            a0 -= 1
            a2 -= 1
            dst[a2] = src[a0]
            continue
        if not get_bit():
            # 0x0088
            if get_bit():
                # 0x0100: copy 2 bytes (d3=1) from 8-bit offset
                d3 = 1
                a0 -= 1
                d2 = src[a0]
            else:
                d2 = get_bits(1)
                if d2 == 0:
                    # 0x00f8: d3 = get_offset(0), d2 = 1
                    d3 = get_bits(1)
                    d1 = ((d3 + 1) << 2) - 1
                    d3 = get_bits(d1)
                    d2 = 1
                else:
                    d1 = (d2 + 1) * 2 - 1
                    d3 = get_bits(d1)
                    # 0x00aa: bsr 0x00c2
                    d2_sel = get_bits(1)
                    d1_sel = ((d2_sel + 1) << 2) - 1
                    d2 = get_bits(d1_sel)
            # 0x00ac: copy d3+1 bytes from a2 + d2
            a1 = a2 + d2
            for _ in range(d3 + 1):
                a1 -= 1
                a2 -= 1
                dst[a2] = dst[a1]
            continue

        if not get_bit():
            # 0x0042: d4=15, d3=2, bsr 0x00c4
            d2_sel = get_bits(1)
            d1_sel = ((d2_sel + 1) << 2) - 1
            if (d1_sel ^ 15) == 0:
                # 0x00de eor.b d1, d4 zeroes d4 when d1 == 15 -> literal 0x00!
                a2 -= 1
                dst[a2] = 0
            else:
                d2 = get_bits(d1_sel)
                a1 = a2 + d2
                for _ in range(3):
                    a1 -= 1
                    a2 -= 1
                    dst[a2] = dst[a1]
            continue

        if not get_bit():
            # 0x005a: single-bit-set literal byte
            d1 = get_bits(2)
            a2 -= 1
            dst[a2] = (1 << d1) & 0xFF
            continue

        if get_bit():
            # 0x0084: d3=4, bra 0x00aa
            d2_sel = get_bits(1)
            d1_sel = ((d2_sel + 1) << 2) - 1
            d2 = get_bits(d1_sel)
            a1 = a2 + d2
            for _ in range(5):
                a1 -= 1
                a2 -= 1
                dst[a2] = dst[a1]
            continue

        # 0x006c: d4=15, d3=3, bsr 0x00c4
        d2_sel = get_bits(1)
        d1_sel = ((d2_sel + 1) << 2) - 1
        if (d1_sel ^ 15) == 0:
            # 0x0076: move.b (a2), -(a2)
            val = dst[a2]
            a2 -= 1
            dst[a2] = val
        else:
            d2 = get_bits(d1_sel)
            a1 = a2 + d2
            for _ in range(4):
                a1 -= 1
                a2 -= 1
                dst[a2] = dst[a1]

    return bytes(dst)


def main():
    st = unpack_msa(ORIG_MSA.read_bytes())
    packed = extract_file_from_st(st, "SIDE_2/ENTOMBED/ENTOMBED.PRG")
    unpacked = depack_entombed_prg(packed)
    magic, tlen, dlen, blen, slen = struct.unpack_from(">HIIII", unpacked, 0)
    assert magic == 0x601A, f"Unpacked magic bad: {magic:#x}"
    OUT_PRG.parent.mkdir(parents=True, exist_ok=True)
    OUT_PRG.write_bytes(unpacked)
    print(f"Unpacked {len(unpacked):,} bytes -> {OUT_PRG}")
    print(f"  TEXT=0x{tlen:x} ({tlen:,})  DATA=0x{dlen:x}  BSS=0x{blen:x} ({blen:,})  SYM=0x{slen:x}")
    reloc_off = 28 + tlen + dlen + slen
    print(f"  Reloc table at 0x{reloc_off:x} ({len(unpacked)-reloc_off:,} bytes)")


if __name__ == "__main__":
    main()
