#!/usr/bin/env python3
"""Nebulus campaign disks: build / inspect / extract (game independent; the seed of the community site's disk packager).

A campaign disk is an ordinary 720 KB double-sided FAT12 floppy (Atari ST / PC / Amiga-tool readable) that holds ONE file, `NEBLEVEL.OVL`
(exactly 8192 bytes: the campaign + level file, format in work/notes/editor.md section 3).  The game's editor loads/saves that file in place
(never creates it, never grows it), so a disk is "ready" as soon as it carries a file of that name and size.  Nothing else is on the disk:
no AUTO folder, a NON-executable boot sector (checksum != $1234, so TOS never runs it).

Boot sector serial (bytes 8..10) = first 3 bytes of md5(NEBLEVEL.OVL): TOS (BDOS media-change check) only notices that the user swapped one
campaign disk for another by a different serial.  Layout (work/notes/editor.md section 12):  80 tracks x 2 sides x 9 sectors x 512 B = 737,280 B; BPB 512 B/sector, 2 sectors/cluster, 1 reserved,
2 FATs x 3 sectors, 112 root entries, 1440 sectors, media $F9; volume label NEBCAMPAIGN; NEBLEVEL.OVL at clusters 2..9 (contiguous, sectors 14..29).

    nebcampaign.py new OUT.st|OUT.msa [--ovl FILE] [--label NAME]   blank disk (all-zero file) or one that carries FILE (8192 B, validated)
    nebcampaign.py info IMG.st|IMG.msa                              BPB, directory, NEBLEVEL.OVL status (+ levels/campaigns when it is valid)
    nebcampaign.py extract IMG.st|IMG.msa OUT.ovl                   write the NEBLEVEL.OVL of a disk image
    nebcampaign.py check IMG                                        exit 0 when the image is a usable campaign disk
The 880 KB (11-sector) / Amiga ADF variant is NOT provided: an ADF is an Amiga OFS/FFS volume, not FAT, and the Atari editor cannot read it
(the site converts ADF campaigns by extracting the file).  .msa = Magic Shadow Archiver (uncompressed tracks), accepted by Hatari and most emulators."""
import argparse, hashlib, struct, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "work/editor"))
import ovl as ovl_mod                                    # noqa: E402  (PC-side file tools: validate / parse)

OVSZ = 0x2000
SPT, HEADS, TRACKS = 9, 2, 80
NSEC = SPT * HEADS * TRACKS
NFAT, SPF, NDIR = 2, 3, 112
FAT0 = 512
DIR0 = FAT0 + NFAT * SPF * 512
DATA0 = DIR0 + NDIR * 32
FNAME = b"NEBLEVELOVL"


def boot_sector(serial: bytes = b"NEB") -> bytes:
    bs = bytearray(512)
    bs[0:3] = b"\xeb\x34\x90"
    bs[3:8] = b"NEBLV"
    bs[8:11] = serial                                    # TOS volume serial (3 bytes): TOS tells a swapped disk from the old one by this number
    struct.pack_into("<HBHBHHBHHH", bs, 11, 512, 2, 1, NFAT, NDIR, NSEC, 0xF9, SPF, SPT, HEADS)
    s = sum(struct.unpack(">256H", bytes(bs))) & 0xFFFF
    assert s != 0x1234, "boot sector must not be executable"
    return bytes(bs)


def build(ovl: bytes = bytes(OVSZ), label: bytes = b"NEBCAMPAIGN") -> bytes:
    assert len(ovl) == OVSZ, f"NEBLEVEL.OVL must be exactly {OVSZ} bytes (got {len(ovl)})"
    b = bytearray(NSEC * 512)
    b[0:512] = boot_sector(hashlib.md5(ovl).digest()[:3])      # serial = hash of the file: different campaigns are different disks to TOS
    ncl = OVSZ // 1024
    fat = bytearray(SPF * 512)
    fat[0:3] = b"\xf9\xff\xff"

    def sf(n, v):
        o = n * 3 // 2
        x = fat[o] | fat[o + 1] << 8
        x = (x & 0x000F) | (v << 4) if n & 1 else (x & 0xF000) | v
        fat[o], fat[o + 1] = x & 0xFF, x >> 8
    for k in range(ncl):
        sf(2 + k, 3 + k if k < ncl - 1 else 0xFFF)
    for k in range(NFAT):
        b[FAT0 + k * SPF * 512:FAT0 + (k + 1) * SPF * 512] = fat
    d = bytearray(32); d[0:11] = label.ljust(11)[:11]; d[11] = 0x08
    e = bytearray(32); e[0:11] = FNAME; e[11] = 0x20
    struct.pack_into("<HH", e, 22, 0x6000, 0x5D72)       # fixed time/date: the output is deterministic
    struct.pack_into("<HL", e, 26, 2, len(ovl))
    b[DIR0:DIR0 + 32] = d
    b[DIR0 + 32:DIR0 + 64] = e
    b[DATA0:DATA0 + OVSZ] = ovl
    return bytes(b)


def to_msa(st: bytes) -> bytes:
    """Magic Shadow Archiver, every track stored uncompressed (length word = track size)."""
    out = bytearray(struct.pack(">HHHHH", 0x0E0F, SPT, HEADS - 1, 0, TRACKS - 1))
    tl = SPT * 512
    for t in range(TRACKS):
        for s in range(HEADS):
            o = (t * HEADS + s) * tl
            out += struct.pack(">H", tl) + st[o:o + tl]
    return bytes(out)


def from_msa(m: bytes) -> bytes:
    magic, spt, sides, t0, t1 = struct.unpack(">HHHHH", m[:10])
    assert magic == 0x0E0F, "not an MSA image"
    p = 10; out = bytearray(); tl = spt * 512
    for _ in range((t1 - t0 + 1) * (sides + 1)):
        n = struct.unpack(">H", m[p:p + 2])[0]; p += 2
        raw = m[p:p + n]; p += n
        if n == tl:
            out += raw
        else:                                              # MSA RLE: 0xE5 byte count.w  = run
            q = 0; trk = bytearray()
            while q < len(raw):
                c = raw[q]; q += 1
                if c == 0xE5:
                    v = raw[q]; cnt = struct.unpack(">H", raw[q + 1:q + 3])[0]; q += 3
                    trk += bytes([v]) * cnt
                else:
                    trk.append(c)
            assert len(trk) == tl, "bad MSA track"
            out += trk
    return bytes(out)


def load(path) -> bytes:
    d = Path(path).read_bytes()
    return from_msa(d) if d[:2] == b"\x0e\x0f" else d


class Disk:
    def __init__(self, img: bytes):
        self.img = img
        bps, spc, res, nfat, ndir, tot, media, spf, spt, heads = struct.unpack_from("<HBHBHHBHHH", img, 11)
        self.bpb = dict(bps=bps, spc=spc, reserved=res, fats=nfat, root=ndir, sectors=tot, media=media, spf=spf, spt=spt, heads=heads)
        self.fat0 = res * bps
        self.dir0 = self.fat0 + nfat * spf * bps
        self.data0 = self.dir0 + ndir * 32
        self.cl = spc * bps

    def fat(self, n):
        o = self.fat0 + n * 3 // 2
        x = self.img[o] | self.img[o + 1] << 8
        return (x >> 4) if n & 1 else (x & 0xFFF)

    def entries(self):
        for i in range(self.bpb["root"]):
            e = self.img[self.dir0 + 32 * i:self.dir0 + 32 * i + 32]
            if e[0] == 0:
                break
            if e[0] == 0xE5:
                continue
            yield e

    def find(self, name11=FNAME):
        for e in self.entries():
            if e[:11] == name11 and not e[11] & 0x18:
                return e
        return None

    def read(self, e):
        c, size = struct.unpack_from("<H", e, 26)[0], struct.unpack_from("<L", e, 28)[0]
        out = bytearray()
        while 2 <= c < 0xFF8 and len(out) < size:
            o = self.data0 + (c - 2) * self.cl
            out += self.img[o:o + self.cl]
            c = self.fat(c)
        return bytes(out[:size])

    def label(self):
        for e in self.entries():
            if e[11] & 0x08:
                return e[:11].decode("ascii", "replace").strip()
        return ""


def status(img: bytes):
    """-> (ok, text, file bytes | None).  ok = the game would load/save it: file present with exactly OVSZ bytes (content valid or all zero for load)."""
    try:
        d = Disk(img)
    except struct.error:
        return False, "not a FAT floppy image", None
    b = d.bpb
    if b["bps"] != 512 or b["fats"] < 1 or b["root"] == 0 or len(img) < b["sectors"] * 512:
        return False, "not a usable FAT12 image", None
    e = d.find()
    if e is None:
        return False, "no NEBLEVEL.OVL (not a campaign disk)", None
    size = struct.unpack_from("<L", e, 28)[0]
    data = d.read(e)
    if size != OVSZ:
        return False, f"NEBLEVEL.OVL is {size} bytes, must be {OVSZ} (not a campaign disk)", data
    if not any(data):
        return True, "NEBLEVEL.OVL present, empty (all zero): 0 levels / 0 campaigns", data
    pr = ovl_mod.validate(data)
    if pr:
        return False, "NEBLEVEL.OVL is corrupt: " + pr[0], data
    lv, cs = ovl_mod.parse(data)
    return True, f"NEBLEVEL.OVL valid: {len(lv)} levels / {len(cs)} campaigns", data


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new"); n.add_argument("out"); n.add_argument("--ovl"); n.add_argument("--label", default="NEBCAMPAIGN")
    for c in ("info", "check"):
        sub.add_parser(c).add_argument("img")
    x = sub.add_parser("extract"); x.add_argument("img"); x.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "new":
        data = Path(a.ovl).read_bytes() if a.ovl else bytes(OVSZ)
        if a.ovl and len(data) != OVSZ:
            sys.exit(f"{a.ovl}: {len(data)} bytes, must be {OVSZ}")
        st = build(data, a.label.upper().encode("ascii"))
        Path(a.out).write_bytes(to_msa(st) if a.out.lower().endswith(".msa") else st)
        print(f"wrote {a.out}: {len(st)} B image, NEBLEVEL.OVL {'from ' + a.ovl if a.ovl else 'all zero'}")
        return 0
    img = load(a.img)
    ok, text, data = status(img)
    if a.cmd == "info":
        d = Disk(img)
        print(f"{a.img}: {len(img)} B, BPB {d.bpb}, label '{d.label()}'")
        for e in d.entries():
            print(f"  {e[:8].decode('ascii','replace')}.{e[8:11].decode('ascii','replace')} attr {e[11]:02x} cluster {struct.unpack_from('<H', e, 26)[0]} size {struct.unpack_from('<L', e, 28)[0]}")
        print(("OK: " if ok else "NOT OK: ") + text)
        return 0
    if a.cmd == "check":
        print(("OK: " if ok else "NOT OK: ") + text)
        return 0 if ok else 1
    if data is None:
        sys.exit("no NEBLEVEL.OVL on the disk")
    Path(a.out).write_bytes(data)
    print(f"extracted {len(data)} B -> {a.out} ({text})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
