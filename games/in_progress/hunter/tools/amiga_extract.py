#!/usr/bin/env python3
"""Extract Hunter's sampled sound effects from the user's own Amiga ADF (Fairlight crack).

Nothing from the ADF is stored in git: the default output dir games/in_progress/hunter/alt/amiga/samples/ is git-ignored.

Disk layout (decoded from the bootblock and the game's trackloader, see work/notes/sound.md):
  * ADF = 160 tracks of 11 x 512 bytes (5632), but the game uses only 10 sectors (5120 bytes) per track.
  * Game track number t (0..159): t < 80 -> cylinder t side 0, t >= 80 -> cylinder t-80 side 1.
    ADF byte offset of a track = (cyl*2 + side) * 5632.
  * File "main" is the game; it contains a 22-entry table of 32-byte records
    (word track, word size_in_longs, word ntracks, word flags, 24-byte name).
  * "externs/soundfile" = the sound driver + effect table + all samples (uncompressed).
      +0x000  driver code (init at +0, VBL update at +0x4a)
      +0x2d2  per-channel state (effect request bytes ...)
      +0x2ee  16 x long  sample start offsets, relative to +0x580
      +0x35e  per-sample 6-byte records: length_words, loop_offset_bytes, loop_length_words
      +0x400  envelope table (16-byte records)
      +0x430  21 x 16-byte effect records: sample, envelope, period (word), duration (byte), ...
      +0x580  sample data (8-bit signed PCM, Paula)

Usage:  amiga_extract.py [--adf PATH] [--out DIR] [--list]
"""
from __future__ import annotations

import argparse
import struct
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
DEFAULT_ADF = GAME / "alt" / "amiga" / "Hunter (Activision).adf"
DEFAULT_OUT = GAME / "alt" / "amiga" / "samples"

PAL_CLOCK = 3546895          # Paula colour clock, PAL (NTSC: 3579545)
TRACK_ADF = 11 * 512         # bytes per track in the ADF
TRACK_DATA = 10 * 512        # bytes of game data per track (11th sector is a dummy)

OFF_SAMPLE_OFFS = 0x2EE
OFF_SAMPLE_TAB = 0x35E
OFF_ENV = 0x400
OFF_EFFECTS = 0x430
OFF_DATA = 0x580
N_EFFECTS = 21
N_SAMPLES = 12


def track_bytes(adf: bytes, t: int) -> bytes:
    cyl, side = (t, 0) if t < 80 else (t - 80, 1)
    o = (cyl * 2 + side) * TRACK_ADF
    return adf[o:o + TRACK_DATA]


def read_file(adf: bytes, start: int, nbytes: int) -> bytes:
    out = bytearray()
    t = start
    while len(out) < nbytes:
        out += track_bytes(adf, t)
        t += 1
    return bytes(out[:nbytes])


def file_table(adf: bytes):
    """Return {name: (track, size_bytes, ntracks, flags)} from the game's table inside file 'main'.

    'main' (track 2, 14 tracks) is the game image the bootblock loads at $40000. The table has 32-byte
    records whose name field starts at +8; it is found by its 'main' / 'externs/' strings.
    """
    main = read_file(adf, 2, 14 * TRACK_DATA)
    table = {}
    j = main.find(b"externs/soundfile")
    if j < 0:
        raise SystemExit("file table not found in 'main': is this the Fairlight Hunter ADF?")
    base = j - 8
    # walk back to the first record: record 0 is 'main'
    while main[base - 32 + 8:base - 32 + 12] in (b"main", b"exte"):
        base -= 32
    n = 0
    while main[base + n * 32 + 8:base + n * 32 + 12] in (b"main", b"exte"):
        rec = main[base + n * 32:base + n * 32 + 32]
        track, size_l, ntr, flags = struct.unpack(">4H", rec[:8])
        name = rec[8:].rstrip(b" \x00").decode("ascii")
        table[name] = (track, size_l * 4, ntr, flags)
        n += 1
    return table


def write_wav(path: Path, data: bytes, rate: int) -> None:
    pcm = bytes((b + 128) & 0xFF for b in data)  # signed -> unsigned 8-bit
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(rate)
        w.writeframes(pcm)


def load_sound(adf: bytes):
    tab = file_table(adf)
    start, size, ntr, flags = tab["externs/soundfile"]
    # The table says 14 tracks but the size needs 15 (the last 892 bytes of sample 11 are on the next track).
    sf = read_file(adf, start, size)
    offs = list(struct.unpack(">16I", sf[OFF_SAMPLE_OFFS:OFF_SAMPLE_OFFS + 64]))
    samples = []
    for i in range(N_SAMPLES):
        ln_w, loop_off, loop_w = struct.unpack(">3H", sf[OFF_SAMPLE_TAB + 6 * i:OFF_SAMPLE_TAB + 6 * i + 6])
        a = OFF_DATA + offs[i]
        samples.append(dict(idx=i, start=a, length=ln_w * 2, loop_off=loop_off, loop_len=loop_w * 2,
                            looped=loop_w > 1, data=sf[a:a + ln_w * 2]))
    effects = []
    for e in range(N_EFFECTS):
        r = sf[OFF_EFFECTS + 16 * e:OFF_EFFECTS + 16 * e + 16]
        sample, env, period, dur = r[0], r[1], struct.unpack(">H", r[2:4])[0], r[4]
        effects.append(dict(id=e, sample=sample, env=env, period=period, dur=dur,
                            rate=PAL_CLOCK / period, forever=dur == 0xFF))
    return tab, sf, samples, effects


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adf", type=Path, default=DEFAULT_ADF)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--list", action="store_true", help="print tables only, write nothing")
    a = ap.parse_args()

    adf = a.adf.read_bytes()
    tab, sf, samples, effects = load_sound(adf)

    print("file table:")
    for n, (t, sz, ntr, fl) in tab.items():
        print(f"  {n:24s} track {t:3d} size {sz:6d} ntracks {ntr:2d} flags {fl:04x}")
    print(f"soundfile: {len(sf)} bytes")

    users: dict[int, list[dict]] = {}
    for e in effects:
        users.setdefault(e["sample"], []).append(e)

    print("\nsamples (8-bit signed PCM):")
    for s in samples:
        us = users.get(s["idx"], [])
        print(f"  s{s['idx']:02d} file+0x{s['start']:05x} {s['length']:6d} B  "
              f"{'LOOP' if s['looped'] else 'once'}  used by effects {[e['id'] for e in us]}")
    print("\neffects:")
    print("  id sample env period  rate(PAL)  dur")
    for e in effects:
        print(f"  {e['id']:2d}  s{e['sample']:02d}   {e['env']:2d}  ${e['period']:04x} {e['rate']:8.0f} Hz  "
              f"{'loop' if e['forever'] else e['dur']}")
    tot = sum(s["length"] for s in samples)
    print(f"\ntotal sample bytes: {tot}")
    if a.list:
        return

    (a.out / "effects").mkdir(parents=True, exist_ok=True)
    for s in samples:
        us = users.get(s["idx"])
        if not us:
            continue
        rate = round(us[0]["rate"])
        write_wav(a.out / f"sample_{s['idx']:02d}_{rate}Hz.wav", s["data"], rate)
    for e in effects:
        s = samples[e["sample"]]
        write_wav(a.out / "effects" / f"fx_{e['id']:02d}_s{e['sample']:02d}_{round(e['rate'])}Hz.wav",
                  s["data"], round(e["rate"]))
    print(f"wrote WAVs to {a.out}")


if __name__ == "__main__":
    main()
