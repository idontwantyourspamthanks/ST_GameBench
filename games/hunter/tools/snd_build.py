#!/usr/bin/env python3
"""Build the Hunter STE sample bank (loaded at $90000 by huntpatch.py --samples) from the user's own Amiga ADF.

    python3 games/hunter/tools/snd_build.py [--adf PATH] [--out games/hunter/build/hunter_snd.bin] [--map]

Nothing from the ADF is stored in git: the output goes to games/hunter/build/ (git-ignored).  The samples are
read with tools/amiga_extract.py (load_sound).  The bank is consumed by patches/snd_core.s (the layout constants
below MUST match its equates; the code checks the 'HSND' magic and the version word before it touches anything).

Bank layout (absolute addresses assume the bank at BANK = $90000; every offset is from the bank start):
  +$000  'HSND', word version (1), word total length / 2 ... (informational)
  +$100  21 effect records of 16 bytes (index = effect id 0..20, the same ids on the ST and the Amiga):
           +0 long sample address (absolute)   +4 word end index   +6 word loop length (0 = one-shot)
           +8 word Amiga base period           +10 word flags (bit0 loop, bit1 swell envelope, bit2 sustained)
           +12 long phase increment 16.16 at the base period (output rate OUT_RATE)
  +$300  22 bytes: priority class of the ST driver ($AF38 in the game; low = important)
  +$400  256 bytes MULV: volume = round(game_volume * envelope / 15), index game_volume*16+envelope
  +$500  256 bytes ENV2: swell envelope (0..15) of the Amiga envelope 2 by effect age in VBL ticks
  +$600  21 longs: absolute address of the half-scale copy of the effect's sample (loops only, else 0): the same bytes
           as volume table 15 gives, so a voice at full game volume (the player's own engine) mixes without a table lookup
  +$1000 16 volume tables of 256 bytes: table k, index = the raw signed sample byte as unsigned:
           out = clamp(round(s * k / 30), -64, 63)      (half scale per voice: two voices never overflow)
  +$2000 the 12 samples (8-bit signed, native Amiga rate), each followed by PAD bytes (loops: the first bytes of the
           loop again, one-shots: zeros), so the mixer never needs a bounds check inside a VBL; then the half-scale copies
           of the loop samples (same lengths, same pads, same indices).

Phase increment: inc = (K4 // period) << 2 with K4 = floor(PAL_CLOCK * 65536 / OUT_RATE / 4) (the 68000 does the same
with one `divu.w`); OUT_RATE is the STE DMA rate 8010613/1280 = 6258.29 Hz.
"""
from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))
from amiga_extract import DEFAULT_ADF, PAL_CLOCK, load_sound  # noqa: E402

BANK = 0x90000
VERSION = 2
OFF_FX, OFF_PRIO, OFF_MULV, OFF_ENV2, OFF_HB, OFF_VTAB, OFF_SAMP = 0x100, 0x300, 0x400, 0x500, 0x600, 0x1000, 0x2000
PAD = 512                                   # >= the source bytes one VBL can consume (<= 252 outputs * inc < 2)
OUT_RATE = 8010613 / 1280                   # STE DMA rate 0
K4 = int(PAL_CLOCK * 65536 / OUT_RATE / 4)  # 9285653; patches/snd_core.s uses the same constant
PRIO = [1, 2, 2, 3, 3, 3, 6, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5, 5, 5, 5, 5]   # game $AF38 (22 entries)
PER_MIN, PER_MAX = 284, 2047                # engine pitch clamp: 12.5 kHz = inc < 2.0 .. 1.7 kHz
F_LOOP, F_ENV2, F_SUST = 1, 2, 4


def inc16(period: int) -> int:
    return (K4 // period) << 2


def vtab_entry(k: int, u: int) -> int:
    """Volume table k at unsigned byte u: clamp(round(s*k/30), -64, 63) as a byte."""
    sv = u - 256 if u > 127 else u
    o = int((sv * k) / 30 + (0.5 if sv * k >= 0 else -0.5))
    return max(-64, min(63, o)) & 0xFF


def vtab15(u: int) -> int:
    return vtab_entry(15, u)


def amiga_envelope(sf: bytes, env: int, ticks: int = 256) -> list[int]:
    """Level (0..64) after each driver tick of the Amiga envelope `env` (soundfile +$400, entries of ticks,delta,repeat;
    code at soundfile +$ae..$102)."""
    rec = sf[0x400 + 16 * env:0x400 + 16 * env + 16]
    level, idx, tick, rep = 0, 0, 1, rec[2]
    out = []
    for _ in range(ticks):
        if tick != 0xFF:                     # tick counter >= 0 (signed byte negative = stopped)
            tick -= 1
            if tick == 0:
                v = (level + rec[idx + 1]) & 0xFF
                level = v if v < 0x41 else (0x40 if v < 0x80 else 0)
                rep = (rep - 1) & 0xFF
                if rep:
                    tick = rec[idx]
                else:
                    idx += 3
                    t = rec[idx]
                    if t >= 0xC0:
                        idx = t & 0x3F
                        t = rec[idx]
                    tick = t
                    if idx != 0x0F:
                        rep = rec[idx + 2]
        out.append(level)
    return out


def build(adf_path: Path) -> tuple[bytes, dict]:
    tab, sf, samples, effects = load_sound(adf_path.read_bytes())
    bank = bytearray(OFF_SAMP)
    bank[0:4] = b"HSND"
    struct.pack_into(">H", bank, 4, VERSION)

    # samples
    addr = {}
    for s in samples:
        data = s["data"]
        pad = bytearray(PAD)
        if s["looped"]:
            lo, ll = s["loop_off"], s["loop_len"]
            loop = data[lo:lo + ll]
            pad = bytearray(loop[i % ll] for i in range(PAD))
        if len(bank) % 2:
            bank.append(0)
        addr[s["idx"]] = BANK + len(bank)
        bank += data + bytes(pad)
        if len(data) + PAD > 0x7FFF:
            raise SystemExit(f"sample {s['idx']} too long for 16-bit indices")
    # half-scale copies of the loop samples (= table 15), index-aligned with the originals
    half = {}
    for s in samples:
        if s["looped"]:
            if len(bank) % 2:
                bank.append(0)
            half[s["idx"]] = BANK + len(bank)
            src = bank[addr[s["idx"]] - BANK:addr[s["idx"]] - BANK + len(s["data"]) + PAD]
            bank += bytes(vtab15(b) for b in src)
    total = len(bank)
    struct.pack_into(">HH", bank, 6, total >> 16, total & 0xFFFF)

    # effect records
    for e in effects:
        s = samples[e["sample"]]
        flags = (F_LOOP if s["looped"] else 0) | (F_ENV2 if e["env"] == 2 else 0) | (F_SUST if e["forever"] else 0)
        end = s["loop_off"] + s["loop_len"] if s["looped"] else s["length"]
        loop = s["loop_len"] if s["looped"] else 0
        if s["looped"] and s["loop_off"] != 0:
            raise SystemExit("loop_off != 0 is not supported by the mixer wrap (idx -= loop_len)")
        struct.pack_into(">IHHHHI", bank, OFF_FX + 16 * e["id"], addr[e["sample"]], end, loop, e["period"], flags,
                         inc16(e["period"]))
    bank[OFF_PRIO:OFF_PRIO + len(PRIO)] = bytes(PRIO)
    for e in effects:
        struct.pack_into(">I", bank, OFF_HB + 4 * e["id"], half.get(e["sample"], 0))

    # MULV and ENV2
    for gv in range(16):
        for env in range(16):
            bank[OFF_MULV + gv * 16 + env] = (gv * env * 2 + 15) // 30
    lv = amiga_envelope(sf, 2, 256)
    for t, v in enumerate(lv):
        bank[OFF_ENV2 + t] = (v * 15 * 2 + 64) // 128

    # volume tables: out = clamp(round(s*k/30), -64, 63); half scale per voice
    for k in range(16):
        for u in range(256):
            bank[OFF_VTAB + k * 256 + u] = vtab_entry(k, u)
    info = dict(total=len(bank), samples={i: a for i, a in addr.items()}, effects=len(effects), k4=K4,
                env2=lv, tab=tab)
    return bytes(bank), info


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adf", type=Path, default=DEFAULT_ADF)
    ap.add_argument("--out", type=Path, default=GAME / "build" / "hunter_snd.bin")
    ap.add_argument("--map", action="store_true", help="print the layout")
    a = ap.parse_args()
    bank, info = build(a.adf)
    if len(bank) > 126976:
        raise SystemExit(f"bank {len(bank)} B exceeds $90000..$AEFFF (126976 B)")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(bank)
    print(f"wrote {a.out}: {len(bank)} bytes (${BANK:x}..${BANK + len(bank) - 1:x}), K4={K4}")
    if a.map:
        for i, ad in info["samples"].items():
            print(f"  sample {i:2d} at ${ad:x}")


if __name__ == "__main__":
    main()
