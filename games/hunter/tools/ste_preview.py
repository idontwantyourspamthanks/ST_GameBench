#!/usr/bin/env python3
"""Render how Hunter's Amiga effects would sound through STE DMA sound, to choose an output rate and voice count.

Reads the user's own ADF (via amiga_extract.load_sound); writes only into the git-ignored
games/hunter/alt/amiga/preview/.  For every STE rate R (12517, 6258 Hz) it simulates the planned mixer:
  * each voice steps through its 8-bit sample with a 16.16 phase increment native_rate/R (nearest sample,
    no interpolation, exactly what a 68000 mixer loop would do);
  * N voices are summed and divided by N (8-bit output: that's the headroom/resolution cost of mixing);
  * the DMA output is zero-order-held: the WAV is written at 50066 Hz with each output sample repeated,
    so your player can't smooth it into something the STE wouldn't produce.
The Amiga reference (amiga/) is the raw sample at its native rate, also zero-order-held.

Usage:  ste_preview.py [--adf PATH] [--out DIR]
"""
from __future__ import annotations

import argparse
import wave
from pathlib import Path

import numpy as np

from amiga_extract import DEFAULT_ADF, GAME, load_sound

OUT_RATE = 50066
RATES = (12517, 6258)
LOOP_SECONDS = 3.0


def voice(sample: dict, native: float, rate: int, seconds: float | None = None, rate_curve=None) -> np.ndarray:
    """8-bit signed samples of one voice at STE rate `rate` (nearest-sample phase stepping, 16.16 fixed point)."""
    data = np.frombuffer(sample["data"], dtype=np.int8).astype(np.int32)
    n_out = int((seconds if seconds else len(data) / native) * rate)
    if rate_curve is None:
        inc = np.full(n_out, int(native / rate * 65536))
    else:
        inc = (rate_curve(np.arange(n_out) / rate) / rate * 65536).astype(np.int64)
    pos = np.cumsum(inc) - inc[0]
    idx = pos >> 16
    if sample["looped"] and seconds:
        lo, ll = sample["loop_off"], sample["loop_len"]
        over = idx >= lo + ll
        idx[over] = lo + (idx[over] - lo) % ll
    idx = idx[idx < len(data)]
    return data[idx]


def amiga_ref(sample: dict, native: float, seconds: float | None) -> np.ndarray:
    """The Amiga sample at its own rate, resampled zero-order-hold to OUT_RATE (Paula is a ZOH DAC too)."""
    return voice(sample, native, int(round(native)), seconds)


def zoh(x: np.ndarray, rate: int) -> np.ndarray:
    t = (np.arange(int(len(x) * OUT_RATE / rate)) * rate // OUT_RATE)
    return x[np.minimum(t, len(x) - 1)]


def write(path: Path, x8: np.ndarray, rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    y = zoh(np.clip(x8, -128, 127).astype(np.int16), rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(OUT_RATE)
        w.writeframes((y * 256).astype("<i2").tobytes())


def mix(voices: list[np.ndarray]) -> np.ndarray:
    n = max(len(v) for v in voices)
    acc = np.zeros(n, dtype=np.int32)
    for v in voices:
        acc[: len(v)] += v
    return acc // len(voices)           # 8-bit output: each voice keeps 1/N of the range


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adf", type=Path, default=DEFAULT_ADF)
    ap.add_argument("--out", type=Path, default=GAME / "alt" / "amiga" / "preview")
    a = ap.parse_args()
    _, _, samples, effects = load_sound(a.adf.read_bytes())

    def fx(eid, rate, seconds=None):
        e = effects[eid]
        s = samples[e["sample"]]
        secs = LOOP_SECONDS if (s["looped"] and not seconds) else seconds
        return voice(s, e["rate"], rate, secs)

    for e in effects:
        s = samples[e["sample"]]
        secs = LOOP_SECONDS if s["looped"] else None
        name = f"fx_{e['id']:02d}_s{e['sample']:02d}"
        write(a.out / "amiga" / f"{name}.wav", amiga_ref(s, e["rate"], secs), int(round(e["rate"])))
        for r in RATES:
            write(a.out / f"ste_{r}" / f"{name}.wav", fx(e["id"], r), r)

    # Engine pitch following speed: the tank/truck/jeep engine sample swept across its four game rates and back.
    eng = samples[effects[7]["sample"]]
    lo, hi = effects[7]["rate"], effects[10]["rate"]
    curve = lambda t: lo + (hi - lo) * np.clip(1 - abs(t / 3.0 - 1), 0, 1)   # up over 3 s, down over 3 s
    for r in RATES:
        write(a.out / f"ste_{r}" / "pitch_engine_sweep.wav", voice(eng, lo, r, 6.0, curve), r)

    # A busy moment: helicopter rotor (loop) + big explosion + tracer fire.  3 voices vs 2 (tracer dropped).
    for r in RATES:
        heli, boom = fx(13, r, 3.0), fx(3, r)
        tracer = np.concatenate([np.zeros(int(0.4 * r), np.int32), fx(6, r)])
        write(a.out / f"ste_{r}" / "scene_3voice_heli_explosion_tracer.wav", mix([heli, boom, tracer]), r)
        write(a.out / f"ste_{r}" / "scene_2voice_heli_explosion.wav", mix([heli, boom]), r)
        write(a.out / f"ste_{r}" / "scene_1voice_explosion_only.wav", boom, r)

    print(f"wrote {sum(1 for _ in a.out.rglob('*.wav'))} WAVs under {a.out}")


if __name__ == "__main__":
    main()
