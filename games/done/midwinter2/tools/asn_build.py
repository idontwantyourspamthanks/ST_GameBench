#!/usr/bin/env python3
"""Midwinter 2: build the Amiga sound bank for the STE DMA driver (patch group asn_*: sound effects + music).

Reads the user's own Amiga disk image (Disk 1 of 3, `program`, SPL release; NOT in git, kept in alt/amiga/, which is
git-ignored) and writes build/asn_bank.bin (git-ignored): the data and the code (patches/asn/blob.s) of the group.

    python3 tools/asn_build.py [--adf alt/amiga/disk1.adf] [--out build/asn_bank.bin] [--tunes 1 5 ...] [--no-led] [--rate6 N ...]
    python3 tools/asn_build.py stats        # what is in the tables (effects, tunes, rates, sizes)
    python3 tools/asn_build.py wav DIR      # one WAV per sound id (the model driver, 6258 Hz mono), for listening
    python3 tools/asn_build.py muswav DIR   # one WAV per tune in the bank as the blob's mixer renders it (12517 Hz mono, first 60 s)

Source data, all inside the load file `MWII` (work/notes/amiga_sound.md section 2, amiga_music.md section 3):
  - hunk 0 (CODE, 217912 B) contains the Amiga sound driver's DATA at fixed offsets: effect records (28 B), sequence table,
    sound rows (4 channel words per sound id); and the music: tune table, pattern lists, patterns, envelopes, instrument descriptors;
  - hunk 3 (DATA, chip) begins with the 8-bit signed sample pool of the effects (16 loop regions, 81544 B), then the music instruments (56640 B).
Bank layout (load address BANK = $BB000, offsets must equal the equates of patches/asn/blob.s):
  +$0000 header: 'ASN2', version.w, nrows.w, bank address.l, total length.l;  +$40..$FF zeros (B_SIL: the silence the one-shot instruments end in)
  +$0100 ROWS   41 x 8 B   (Amiga rows: 4 words per sound id, a sequence offset or $ffff per channel)
  +$0300 SEQ    818 B      (words: effect record offsets, 0 = stop, negative = relative jump back)
  +$0700 REC    1626 B     (effect records, 28 B: +0 vol +2 vslope +4 vaccel +6 vmin +8 vmax +a per/-1 +c pbase/pslope +e pslope/pscale
                            +10 pmin +12 pmax +14 duration (ticks) +16 sample ADDRESS (rewritten here: absolute RAM) +1a length (words))
  +$0E00 SV     256 B zeros (the blob's state)        +$0F00 MS 256 B zeros (the four music channel records)
  +$1000 RING   2048 B zeros (the DMA ring)
  +$1800 VTAB   3 gain sets x 16 levels x 256 B: out = clamp(round(s * level * gain))   (level L = 1..16: volume (4L)/64)
  +$4800 CODE   the blob = patches/asn/blob.s assembled with vasm (fixed entry jumps at +0: tick, wd, lvc, lv1, lv2, music tick, music start)
  +$6000 MUSIC  tune table, flags, score, instruments (tools/asn_music.py build_music), then the effects' sample regions.
  Every sample region is followed by PAD bytes (loops: the region repeated; one-shots: zeros): the mixer tests the end once per 8 outputs.
The whole file is loaded to BANK ($BB000): HD by a RUNME splice from FILES\\ASNBANK.BIN, floppy as part of FFA file 10.  It must end below
LIMIT: the 1 MB HD game uses RAM from $E83E6 up (work/notes/amiga_music_port.md, RAM map).
"""
from __future__ import annotations

import argparse
import hashlib
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import asn_music  # noqa: E402

ADF = ROOT / "alt" / "amiga" / "disk1.adf"
OUT = ROOT / "build" / "asn_bank.bin"

BANK = 0xBB000
LIMIT = 0xE8000                # the bank must end below this (free RAM of the 1 MB HD game: $BB000-$E83E5)
MAGIC = b"ASN2"
MWII_MD5 = "d7c1518e6702c3210a748fc40a1ed753"       # SPL release, Disk 1 of 3, program/MWII (505488 B)
OFF_SIL, OFF_ROWS, OFF_SEQ, OFF_REC, OFF_SV, OFF_MS, OFF_RING, OFF_VT, OFF_CODE, OFF_MUS = 0x40, 0x100, 0x300, 0x700, 0xE00, 0xF00, 0x1000, 0x1800, 0x4800, 0x6000
RL = 2048
# Amiga driver data inside hunk 0 (flat offsets = file offsets of the hunk 0 body)
A_REC, A_SEQ, A_ROWS = 0x2F75C, 0x2FDB6, 0x300E8
NROWS, REC_LEN, SEQ_LEN, REC_SIZE = 41, 0x65A, 0x332, 28
PAD = asn_music.PAD
CODE = BANK + OFF_CODE         # RAM address of the blob (patches/asn/blob.s `ORG`)
GAINS = (0.5, 0.25, 0.35)    # set 0: effects, <= 2 audible voices; set 1: effects with 3-4 voices and the peaky tunes; set 2: the other tunes
NLEV = 16
# Tunes the ST game can request (st_music.md 2.4), most wanted first; 3, 11, 13, 14 have no ST call site.
TUNES = [1, 5, 2, 4, 6, 7, 10, 15, 16, 17, 8, 9, 12]


def read_mwii(adf: Path) -> bytes:
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "MWII"
        subprocess.run(["xdftool", str(adf), "read", "MWII", str(dst)], check=True, capture_output=True)
        return dst.read_bytes()


def hunks(raw: bytes):
    """Minimal AmigaDOS load-file parser: returns [(type, size, data, relocs)]; only CODE/DATA/BSS + RELOC32/END."""
    p = 0
    be = lambda o: struct.unpack_from(">I", raw, o)[0]
    assert be(0) == 0x3F3 and be(4) == 0
    n = be(8)
    first, last = be(12), be(16)
    sizes = [be(20 + 4 * i) & 0x3FFFFFFF for i in range(n)]
    p = 20 + 4 * n
    out = []
    for i in range(n):
        t = be(p) & 0x3FFFFFFF
        ln = be(p + 4) * 4
        p += 8
        data = b""
        if t in (0x3E9, 0x3EA):
            data = raw[p:p + ln]
            p += ln
        nrel = 0
        while True:
            h = be(p) & 0x3FFFFFFF
            p += 4
            if h == 0x3F2:
                break
            if h == 0x3EC:
                while True:
                    c = be(p)
                    p += 4
                    if c == 0:
                        break
                    p += 4 + 4 * c
                    nrel += c
            else:
                raise SystemExit(f"hunk {i}: unexpected block ${h:x}")
        out.append((t, sizes[i] * 4, data, nrel))
    return out


class Tables:
    """The Amiga sound tables, parsed from MWII."""

    def __init__(self, mwii: bytes):
        md5 = hashlib.md5(mwii).hexdigest()
        if md5 != MWII_MD5:
            raise SystemExit(f"MWII md5 {md5} is not the SPL release {MWII_MD5} (offsets would be wrong)")
        self.mwii = mwii
        h = hunks(mwii)
        self.code, self.h3 = h[0][2], h[3][2]
        assert len(self.code) == 217912 and len(self.h3) == 138204
        c = self.code
        assert c[A_REC - 0x10:A_REC - 0x10 + 4] == bytes.fromhex("acdcacdc")      # the marker that precedes the data
        self.rec = c[A_REC:A_REC + REC_LEN]
        self.seq = c[A_SEQ:A_SEQ + SEQ_LEN]
        self.rows = [struct.unpack_from(">4H", c, A_ROWS + 8 * i) for i in range(NROWS)]
        self.recs = {}
        for off in range(2, REC_LEN - 27, REC_SIZE):
            f = struct.unpack_from(">11H", self.rec, off)
            so, ln = struct.unpack_from(">IH", self.rec, off + 0x16)
            self.recs[off] = dict(f=f, so=so, ln=ln)
        # the regions: distinct (offset, length bytes) pairs, contiguous from 0 in the pool
        regs = sorted({(r["so"], 2 * r["ln"]) for r in self.recs.values()})
        pos = 0
        for so, ln in regs:
            assert so == pos, (so, pos)
            pos += ln
        self.regions = regs
        self.pool_len = pos
        # all sequences must be words <= SEQ_LEN, all targets valid records
        for off in range(0, SEQ_LEN, 2):
            w = struct.unpack_from(">h", self.seq, off)[0]
            if w > 0:
                assert w in self.recs, hex(w)
        self._mem = None

    def seq_word(self, o):
        return struct.unpack_from(">h", self.seq, o)[0]

    @property
    def mem(self) -> asn_music.Mem:
        """The load file in operand address space (the music's pointers)."""
        if self._mem is None:
            self._mem = asn_music.Mem(asn_music.amiga_image(self.mwii))
        return self._mem


def region_pcm(t: Tables, so: int, ln: int):
    """Signed 8-bit region with its DC offset removed (the Amiga samples carry about +10; an envelope on it thumps)."""
    import numpy as np
    a = np.frombuffer(t.h3[so:so + ln], dtype=np.int8).astype(np.float64)
    if so != 0:
        a = a - round(a.mean())
    return np.clip(np.round(a), -128, 127).astype(np.int8)


def assemble_blob(listing: Path | None = None) -> bytes:
    """patches/asn/blob.s -> bytes from CODE."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "blob.bin"
        cmd = ["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-o", str(out)]
        if listing:
            cmd += ["-L", str(listing)]
        r = subprocess.run(cmd + [str(ROOT / "patches" / "asn" / "blob.s")], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(r.stderr)
        return out.read_bytes()


def tune_peak(m: asn_music.Mem, bank: bytes, info: dict, tune: int, rate: int) -> float:
    """Largest |sum| of the tune's voices at full table scale (one voice at volume 64 = 127), from a float render of its loop with the
    bank's (filtered) samples: the headroom the gain set must leave."""
    import numpy as np
    mu = asn_music.Music(m, fixed_env=True)
    mu.start(tune)
    pa = asn_music.Paula()
    pa.apply(mu.out)
    pcm = {}
    for lc, a in info["lc"].items():
        d = [x for x in info["lcraw"].values() if x[0] == a][0]
        pcm[lc] = (np.frombuffer(bank[a - BANK:a - BANK + d[2]], dtype=np.int8).astype(np.float64), d[1])
    hz = 12516.58 if rate else 6258.29
    n = int(round(hz / 50.053))
    pos, cur = [0.0] * 4, [None] * 4
    mx = 0.0
    for _ in range(info["loops"][tune]):
        mu.out = []
        before = list(pa.restart)
        mu.tick()
        pa.apply(mu.out)
        s = np.zeros(n)
        for c in range(4):
            if pa.restart[c] != before[c]:
                pos[c], cur[c] = 0.0, pa.cur[c][0]
            if not pa.on[c] or cur[c] not in pcm:
                continue
            d, loop = pcm[cur[c]]
            inc = asn_music.PAL / max(asn_music.PMIN_MUS, pa.per[c]) / hz
            idx = (pos[c] + inc * np.arange(n)).astype(np.int64)
            pos[c] += inc * n
            lv = asn_music.level_of(min(pa.vol[c], 64) << 8)
            if loop:
                v = d[idx % len(d)]
                pos[c] %= len(d)
            else:
                ok = idx < len(d)
                v = np.zeros(n)
                v[ok] = d[idx[ok]]
            s += v * (lv * 4 / 64)
        mx = max(mx, float(np.abs(s).max()))
    return mx


def build_bank(t: Tables, tunes=None, led: bool = True, rate6=(), verbose: bool = False):
    """-> (bank bytes, music info)."""
    tunes = list(TUNES if tunes is None else tunes)
    b = bytearray(OFF_CODE)
    # volume tables
    for g, gain in enumerate(GAINS):
        for lev in range(1, NLEV + 1):
            scale = min(lev * 4, 64) / 64.0
            lim = int(round(128 * gain))
            for u in range(256):
                s = u - 256 if u >= 128 else u
                v = int(round(s * scale * gain))
                v = max(-lim, min(lim - 1, v))
                b[OFF_VT + (g * NLEV + lev - 1) * 256 + u] = v & 0xFF
    blob = assemble_blob()
    if len(blob) > OFF_MUS - OFF_CODE:
        raise SystemExit(f"the blob ({len(blob)} B) does not fit ${CODE:x}-${BANK + OFF_MUS:x}")
    for i in range(7):                                  # the fixed entries the patch sites call: 7 x `jmp abs.l` into the blob
        op, tgt = struct.unpack_from(">HI", blob, 6 * i)
        if op != 0x4EF9 or not CODE + 42 <= tgt < CODE + len(blob):
            raise SystemExit(f"blob entry {i} at ${CODE + 6 * i:x} is not a jmp into the blob ({blob[6 * i:6 * i + 6].hex()})")
    b += blob + bytes(OFF_MUS - OFF_CODE - len(blob))
    # music section (a first pass with the default gain set finds each tune's peak, then the flags are set)
    rates = {n: 0 if n in rate6 else 1 for n in tunes}
    mus, info = asn_music.build_music(t.mem, tunes, BANK + OFF_MUS, BANK + OFF_SIL, led=led, rates=rates)
    mus = bytearray(mus)
    gains = {}
    for n in tunes:
        pk = tune_peak(t.mem, bytes(b) + bytes(mus), info, n, rates[n])
        gains[n] = 2 if pk * GAINS[2] * 1.10 + 2 <= 127 else 1          # 10 % + rounding headroom, else the quarter-scale set
        if pk * GAINS[gains[n]] * 1.10 + 2 > 127:
            raise SystemExit(f"tune {n}: peak {pk:.0f} overflows even the quarter-scale set")
        mus[0x121 + 2 * n] = gains[n]
        info.setdefault("peak", {})[n] = pk
    info["gains"], info["rates"] = gains, rates
    b += mus
    # effect samples
    smp = bytearray()
    base_of = {}
    for so, ln in t.regions:
        pcm = region_pcm(t, so, ln).tobytes()
        base_of[so] = BANK + len(b) + len(smp)
        smp += pcm + (pcm * (PAD // ln + 1))[:PAD]
        if len(smp) & 1:
            smp += b"\0"
    rec = bytearray(t.rec)
    for off, r in t.recs.items():
        struct.pack_into(">I", rec, off + 0x16, base_of[r["so"]])
    for i, row in enumerate(t.rows):
        struct.pack_into(">4H", b, OFF_ROWS + 8 * i, *row)
    b[OFF_SEQ:OFF_SEQ + SEQ_LEN] = t.seq
    b[OFF_REC:OFF_REC + REC_LEN] = rec
    info["sfx_base"] = base_of
    b += smp
    total = len(b)
    if BANK + total > LIMIT:
        raise SystemExit(f"the bank ends at ${BANK + total:x}, above ${LIMIT:x}: drop tunes (--tunes)")
    struct.pack_into(">4sHHII", b, 0, MAGIC, 2, NROWS, BANK, total)
    info.update(blob_len=len(blob), mus_len=len(mus), sfx_len=len(smp), total=total)
    return bytes(b), info


def cmd_stats(t: Tables):
    print(f"hunk0 {len(t.code)} B, hunk3 {len(t.h3)} B; {len(t.recs)} effect records, {len(t.regions)} sample regions, pool {t.pool_len} B")
    for so, ln in t.regions:
        used = sorted(k for k, r in t.recs.items() if r["so"] == so)
        print(f"  region ${so:05x} {ln:6d} B  records {[hex(k) for k in used]}")
    for i, row in enumerate(t.rows):
        print(f"  sound {i:2d}: rows {[('--' if w == 0xFFFF else '%03x' % w) for w in row]}")
    bank, info = build_bank(t)
    print(describe(bank, info))
    for n in info["tunes"]:
        tu = asn_music.Tune(t.mem, n)
        print(f"  tune {n:2d}: loop {info['loops'][n]:5d} ticks, {len(tu.pats):2d} patterns, {len(tu.insts)} instruments, peak {info['peak'][n]:4.0f} -> gain set {info['gains'][n]}"
              f" ({GAINS[info['gains'][n]]}), rate {'12517' if info['rates'][n] else '6258'} Hz")


def describe(bank: bytes, info: dict) -> str:
    return (f"{len(bank)} B: tables + state + ring + volume tables ${OFF_CODE:x}, blob {info['blob_len']} B at ${CODE:x}, music ${BANK + OFF_MUS:x} {info['mus_len']} B "
            f"(score {info['score_bytes']} B, {len(info['insts'])} instruments {info['sample_bytes']} B) for tunes {info['tunes']}, effects' samples {info['sfx_len']} B; "
            f"loads at ${BANK:x}, ends ${BANK + len(bank):x} (limit ${LIMIT:x}, {LIMIT - BANK - len(bank)} B to spare)")


def write_muswavs(t: Tables, bank: bytes, info: dict, outdir: Path, secs: float = 60.0):
    import wave
    outdir.mkdir(parents=True, exist_ok=True)
    for n in info["tunes"]:
        rate = info["rates"][n]
        ticks = min(info["loops"][n], int(secs * 50))
        a = asn_music.render(t.mem, bank, BANK, info, n, ticks, rate=rate, gainset=info["gains"][n], vt_base=BANK + OFF_VT)
        with wave.open(str(outdir / f"tune{n:02d}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(1)
            w.setframerate(12517 if rate else 6258)
            w.writeframes(bytes((x + 128) & 255 for x in a))
    print("wrote", outdir)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="?", default="build", choices=["build", "stats", "wav", "muswav"])
    ap.add_argument("arg", nargs="?")
    ap.add_argument("--adf", default=str(ADF))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--tunes", nargs="*", type=int, default=None, help=f"tunes in the bank (default {TUNES}); the others stay on the YM")
    ap.add_argument("--no-led", action="store_true", help="do not apply the Amiga's LED low-pass (3.3 kHz) to the instruments")
    ap.add_argument("--rate6", nargs="*", type=int, default=[], help="tunes mixed at 6258 Hz instead of 12517 Hz (half the CPU)")
    a = ap.parse_args()
    t = Tables(read_mwii(Path(a.adf)))
    if a.cmd == "stats":
        return cmd_stats(t)
    if a.cmd == "wav":
        import asn_model
        return asn_model.write_wavs(t, Path(a.arg or "alt/amiga/wav"))
    bank, info = build_bank(t, a.tunes, led=not a.no_led, rate6=a.rate6)
    if a.cmd == "muswav":
        return write_muswavs(t, bank, info, Path(a.arg or "alt/amiga/muswav"))
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_bytes(bank)
    print(f"wrote {a.out}: {describe(bank, info)}")


if __name__ == "__main__":
    main()
