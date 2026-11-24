#!/usr/bin/env python3
"""STX (Pasti) reader -> plain .ST disk image + anomaly report; Moonshine Racers floppy work (work/notes/floppy.md).

    python3 tools/stx2st.py info  IMAGE.stx...            # header, per-track sector/fuzzy/timing summary, anomalies
    python3 tools/stx2st.py st    IMAGE.stx OUT.st [--geom 80,2,9|80,2,10|80,2,11] [--json OUT.json]
    python3 tools/stx2st.py cmp   A.bin B.bin [OFFSET]     # coarse content search of one blob in another

Format: reverse-engineered from the emulator's own reader (hatari 2.6.1 src/floppies/stx.c, `STX_Insert_internal`;
structures in src/includes/floppies/stx.h). All multi-byte fields are little-endian:
  header (16 B)  "RSY\\0" | version u16 (3) | imaging tool u16 | reserved u16 | tracks u8 | revision u8 | reserved u32
  track  (16 B)  BlockSize u32 | FuzzySize u32 | SectorsCount u16 | Flags u16 | MFMSize u16 | TrackNumber u8 (bit7 = side) | RecType u8
                 then SectorsCount * 16 B sector blocks, then FuzzySize bytes of fuzzy masks, then the sector/track data area.
  sector (16 B)  DataOffset u32 | BitPosition u16 | ReadTime u16 | ID_Track u8 | ID_Head u8 | ID_Sector u8 | ID_Size u8 |
                 ID_CRC u16 | FDC_Status u8 | Reserved u8
                 data = trackdata + DataOffset, length 128 << (ID_Size & 3); FDC_Status bit0 = variable timing, bit3 = CRC error,
                 bit4 = RNF (no data), bit5 = deleted data, bit7 = fuzzy bits (mask in the fuzzy area, one mask byte per data byte).
  Flags bit0 = the track has sector blocks; bit6 = track image present; bit7 = track image carries a sync position.
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

FDC_CRC, FDC_RNF, FDC_DELETED, FDC_FUZZY, FDC_VARTIME = 1 << 3, 1 << 4, 1 << 5, 1 << 7, 1 << 0


def parse(path: Path) -> dict:
    d = path.read_bytes()
    if d[:4] != b"RSY\0":
        raise SystemExit(f"{path}: not an STX (magic {d[:4]!r})")
    ver, tool, res1 = struct.unpack_from("<HHH", d, 4)
    ntracks, rev = d[0x0A], d[0x0B]
    res2 = struct.unpack_from("<I", d, 0x0C)[0]
    tracks = []
    p = 16
    for i in range(ntracks):
        (bsize, fsize, nsect, flags, mfmsize) = struct.unpack_from("<IIHHH", d, p)
        tnum, rectype = d[p + 14], d[p + 15]
        t = dict(block=p, BlockSize=bsize, FuzzySize=fsize, Sectors=[], Flags=flags, MFMSize=mfmsize,
                 Track=tnum & 0x7F, Side=(tnum >> 7) & 1, RecordType=rectype, TrackImage=bool(flags & 0x40))
        s0 = p + 16
        data0 = s0 + nsect * 16 + fsize
        fuzzy = data0 - fsize
        if flags & 1:                                  # sector blocks present
            maxend = 0
            for n in range(nsect):
                (doff, bitpos, rtime) = struct.unpack_from("<IHH", d, s0 + n * 16)
                itr, ihd, isec, isz = d[s0 + n * 16 + 8:s0 + n * 16 + 12]
                icrc = struct.unpack_from(">H", d, s0 + n * 16 + 12)[0]
                stat, rsv = d[s0 + n * 16 + 14], d[s0 + n * 16 + 15]
                size = 128 << (isz & 3)
                sec = dict(ID_Track=itr, ID_Head=ihd, ID_Sector=isec, ID_Size=isz, ID_CRC=icrc, Size=size,
                           Status=stat, ReadTime=rtime, BitPosition=bitpos, DataOffset=doff)
                if not stat & FDC_RNF:
                    lo, hi = data0 + doff, data0 + doff + size
                    sec["data"] = d[lo:hi]
                    maxend = max(maxend, doff + size)
                    if stat & FDC_FUZZY:
                        sec["fuzzy"] = d[fuzzy:fuzzy + size]
                        fuzzy += size
                t["Sectors"].append(sec)
            # timings (revision 2 + variable-time sectors) start after the sector data / track image
            tim = data0 + maxend
            img = 0
            if flags & 0x40:
                img = struct.unpack_from("<H", d, data0 + (4 if flags & 0x80 else 0) + 2)[0]
                tim = max(tim, data0 + (4 if flags & 0x80 else 0) + img)
            if any(s["Status"] & FDC_VARTIME for s in t["Sectors"]) and rev == 2 and tim + 4 <= len(d):
                t["TimingFlags"], t["TimingSize"] = struct.unpack_from("<HH", d, tim)
        traces = [s for s in range(0)]  # (no op; keeps the shape obvious)
        tracks.append(t)
        p += bsize
    return dict(path=str(path), version=ver, tool=tool, revision=rev, reserved=(res1, res2), tracks=tracks,
                size=len(d), tail=len(d) - p)


def anomalies(disk: dict) -> list[str]:
    """Only what a plain 512-byte-sector .ST would lose: CRC errors, deleted data, fuzzy bytes, variable timing, RNF,
    odd sizes, wrong ID fields, duplicated/missing IDs, empty tracks, and sectors whose ID is not 1..N."""
    out = []
    counts = {"crc": 0, "fuzzy": 0, "del": 0, "var": 0, "rnf": 0, "odd": 0, "idfield": 0, "empty": 0, "dup": 0}
    for t in disk["tracks"]:
        ss = t["Sectors"]
        tn = f"t{t['Track']:02d}.{t['Side']}"
        if not ss:
            counts["empty"] += 1
            out.append(f"{tn}: no sectors (track image only)")
            continue
        ids = [s["ID_Sector"] for s in ss]
        if sorted(ids) != list(range(1, len(ss) + 1)):
            counts["dup"] += 1
            out.append(f"{tn}: sector IDs {sorted(ids)}")
        for s in ss:
            bad = []
            if s["Status"] & FDC_CRC: bad.append("crc"); counts["crc"] += 1
            if s["Status"] & FDC_DELETED: bad.append("deleted"); counts["del"] += 1
            if s["Status"] & FDC_FUZZY: bad.append("fuzzy"); counts["fuzzy"] += 1
            if s["Status"] & FDC_VARTIME: bad.append("vartime"); counts["var"] += 1
            if s["Status"] & FDC_RNF: bad.append("rnf"); counts["rnf"] += 1
            if s["Size"] != 512: bad.append(f"size{s['Size']}"); counts["odd"] += 1
            if s["ID_Track"] != t["Track"] or s["ID_Head"] != t["Side"]:
                bad.append(f"id{t['Track']:02x}.{t['Side']}/{s['ID_Track']:02x}.{s['ID_Head']}"); counts["idfield"] += 1
            if bad:
                out.append(f"{tn} sec {s['ID_Sector']:2d}: " + " ".join(bad))
        if t["FuzzySize"]:
            out.append(f"{tn}: fuzzy area {t['FuzzySize']} B")
        if "TimingSize" in t:
            out.append(f"{tn}: timing table {t.get('TimingSize')} B (flags {t.get('TimingFlags')!r})")
    out.insert(0, "summary: " + ", ".join(f"{k}={v}" for k, v in counts.items()) +
               f", track images={sum(t['TrackImage'] for t in disk['tracks'])}/{len(disk['tracks'])}, "
               f"MFMSize range {min(t['MFMSize'] for t in disk['tracks'])}-{max(t['MFMSize'] for t in disk['tracks'])}")
    return out


def cmd_info(paths):
    for p in paths:
        d = parse(Path(p))
        print(f"{Path(p).name}: {d['size']} B, version {d['version']}, tool {d['tool']}, revision {d['revision']}, "
              f"{len(d['tracks'])} track blocks, trailing {d['tail']} B")
        sides = {}
        for t in d["tracks"]:
            sides.setdefault(t["Side"], []).append(t)
        for side, ts in sorted(sides.items()):
            print(f"  side {side}: {len(ts)} tracks, sectors per track {sorted({len(t['Sectors']) for t in ts})}, "
                  f"IDs/track {sorted({len(t['Sectors']) for t in ts})}, tracks {min(t['Track'] for t in ts)}-{max(t['Track'] for t in ts)}")
        a = anomalies(d)
        print(f"  anomalies: {len(a)}")
        for l in a:
            print("   ", l)


def cmd_st(path, out, geom, js):
    geo = [int(x) for x in geom.split(",")]
    tracks_n, sides_n, spt = geo
    d = parse(Path(path))
    img = bytearray(tracks_n * sides_n * spt * 512)
    hit = 0
    for t in d["tracks"]:
        if t["Track"] >= tracks_n or t["Side"] >= sides_n:
            continue
        for s in t["Sectors"]:
            n = s["ID_Sector"]
            if not (1 <= n <= spt) or "data" not in s or s["Size"] != 512:
                continue
            base = ((t["Track"] * sides_n + t["Side"]) * spt + (n - 1)) * 512
            img[base:base + 512] = s["data"]
            hit += 1
    Path(out).write_bytes(bytes(img))
    # geometry check: which sectors are missing / duplicated
    seen = {}
    for t in d["tracks"]:
        for s in t["Sectors"]:
            seen.setdefault((t["Track"], t["Side"], s["ID_Sector"]), []).append(s)
    missing = [(t, sd, n) for t in range(tracks_n) for sd in range(sides_n) for n in range(1, spt + 1)
               if (t, sd, n) not in seen]
    dup = {k: len(v) for k, v in seen.items() if len(v) > 1}
    extra = [k for k in seen if k[0] >= tracks_n or k[1] >= sides_n or not (1 <= k[2] <= spt)]
    print(f"{Path(path).name} -> {out}: {len(img)} B, {hit} sectors written, {len(missing)} missing, {len(dup)} duplicated, "
          f"{len(extra)} outside the geometry")
    for m in missing[:20]:
        print("   missing", m)
    if dup:
        print("   duplicated", dict(list(dup.items())[:10]))
    if extra:
        print("   outside", extra[:10])
    if js:
        Path(js).write_text(json.dumps(anomalies(d), indent=1) + "\n")
        print(f"   anomalies -> {js}")


def cmd_cmp(a, b, off="0"):
    A, B = Path(a).read_bytes(), Path(b).read_bytes()
    o = int(off, 0)
    n = 0
    for i in range(0, len(A) - 32, 16):
        blk = A[i:i + 32]
        if blk.count(0) >= 28:
            continue
        j = B.find(blk)
        if j >= 0:
            print(f"A ${i:06x} == B ${j:06x}  {blk[:16].hex()}")
            n += 1
            if n >= 20:
                break
    print(f"{n} 32-byte block(s) of {a} found in {b}")


def main(argv):
    if len(argv) < 2:
        raise SystemExit(__doc__)
    if argv[0] == "info":
        cmd_info(argv[1:])
    elif argv[0] == "st":
        geom, js = "80,2,9", None
        rest = argv[1:]
        if "--geom" in rest:
            i = rest.index("--geom"); geom = rest[i + 1]; del rest[i:i + 2]
        if "--json" in rest:
            i = rest.index("--json"); js = rest[i + 1]; del rest[i:i + 2]
        cmd_st(rest[0], rest[1], geom, js)
    elif argv[0] == "cmp":
        cmd_cmp(*argv[1:])
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
