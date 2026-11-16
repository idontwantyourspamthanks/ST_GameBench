#!/usr/bin/env python3
"""Reference model of the Amiga Midwinter 2 sound driver (ported from the Amiga disassembly, work/notes/amiga_sound.md §2) and of
the STE mixer in patches/asn_core.s.  Used for (1) the WAV previews (`asn_build.py wav`), (2) the per-tick state that the blob is
compared against in the emulator (`tools/asn_test.py`), (3) the rate statistics of the notes.

Amiga routines (flat addresses of work/dumps/mwii_flat.bin, base-0 layout; operands in the disassembly carry +$270d0):
  $2f3b2 tick, $2f28c start (rows), $2f2f2 kill (group), $2f46c voice update, $2f4fa next step, $2f5b0 stop, $2f616 Paula writes.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

PAL = 3546895
K4 = 9285653               # PAL * 65536 / 6258.29 / 4
PMIN, PMAX = 142, 2000     # period clamp of the STE mixer (inc16 = (K4 / P) << 2 must fit 16 bits for the quotient)


def s16(x):
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


class Voice:
    __slots__ = ("vol vsl per psl cnt rec seq grp smp ln idx frac").split()

    def __init__(self):
        self.vol = self.vsl = self.per = self.psl = self.cnt = self.rec = self.seq = 0
        self.grp = -1
        self.smp = 0
        self.ln = 200
        self.idx = self.frac = 0


class Driver:
    def __init__(self, tables):
        self.t = tables
        self.v = [Voice() for _ in range(4)]
        self.grpb = [0] * 8
        self.level = 7
        self.last = -1

    # ---- the Amiga code ------------------------------------------------------------------------
    def R(self, off, field):
        """field = byte offset inside the record at `off` (signed word)."""
        return struct.unpack_from(">h", self.t.rec, off + field)[0]

    def start(self, sid):
        if not 0 <= sid < len(self.t.rows):
            return
        row = self.t.rows[sid]
        for c in range(4):
            if row[c] != 0xFFFF:
                self.kill(c)
        g = 1
        while self.grpb[g] != 0:
            g += 1
        for c in range(4):
            if row[c] != 0xFFFF:
                self.grpb[g] |= 1 << (c + 1)
                self.v[c].cnt = 1
                self.v[c].seq = row[c]
                self.v[c].grp = g

    def kill(self, c):
        g = self.v[c].grp
        if g < 0:
            return
        m = self.grpb[g]
        self.grpb[g] = 0
        for d6 in range(1, 5):
            if m & (1 << d6):
                v = self.v[d6 - 1]
                v.cnt = 0
                v.vol = 0
                v.grp = -1

    def tick(self, trig=None):
        """One 50 Hz tick. trig = sound id or None (the request word)."""
        if trig is not None and trig >= 0:
            self.start(trig)
        if all(v.cnt == 0 for v in self.v) and self.last >= 0:
            self.start(self.last)
        for c in range(4):
            self.voice(c)

    def voice(self, c):
        v = self.v[c]
        a = v.rec
        v.cnt = s16(v.cnt - 1)
        if v.cnt == 0:
            return self.step(c)
        if v.cnt < 0:
            v.cnt += 1
            return
        d0, d1 = v.vol, v.vsl
        d0 = s16(d0 + d1)
        d1 = s16(d1 + self.R(a, 4))
        mx = self.R(a, 8)
        if d0 >= mx:
            d0 = mx
        else:
            mn = self.R(a, 6)
            if d0 < mn:
                d0 = mn
        v.vol, v.vsl = d0, d1
        if self.R(a, 0xA) >= 0:
            d0 = s16(v.per + v.psl)
            d1 = s16(v.psl + self.R(a, 0xE))
        else:
            d1 = s16(self.R(a, 0xE) * self.level)
            d0 = s16(self.R(a, 0xC) + d1)
        mx = self.R(a, 0x12)
        if d0 >= mx:
            d0 = mx
        else:
            mn = self.R(a, 0x10)
            if d0 < mn:
                d0 = mn
        v.per, v.psl = d0, d1

    def step(self, c):
        v = self.v[c]
        seq = self.t.seq
        p = v.seq
        v.seq = p + 2
        d0 = struct.unpack_from(">h", seq, p)[0]
        v.rec = d0
        if d0 == 0:
            return self.stop(c)
        if d0 < 0:
            p += d0
            v.seq = p + 2
            d0 = struct.unpack_from(">h", seq, p)[0]
            v.rec = d0
        a = d0
        so, ln = struct.unpack_from(">IH", self.t.rec, a + 0x16)
        v.smp, v.ln = so, ln
        v.vol, v.vsl = self.R(a, 0), self.R(a, 2)
        v.idx = v.frac = 0
        d = self.R(a, 0xA)
        if d < 0:
            d = s16(self.R(a, 0xC) + s16(self.R(a, 0xE) * self.level))
        v.per = d
        v.psl = self.R(a, 0xC)
        v.cnt = self.R(a, 0x14) or 7

    def stop(self, c):
        v = self.v[c]
        v.vol = 0
        g = v.grp
        if g >= 0:
            self.grpb[g] &= ~(1 << (c + 1))
        v.grp = -1

    # ---- the STE mixer (6258 Hz mono; volume levels; loops via the cyclic pad) -------------------------
    @staticmethod
    def level_of(vol):
        """Volume level 0..16 of the mixer (asm: asn_prep): the 8.8 volume's high byte, clamped to 64, (b + 2) >> 2."""
        if vol < 0:
            return 0
        return min(16, (min(64, vol >> 8) + 2) >> 2)

    def mix(self, n, regions, pcm, gains=(0.5, 0.25)):
        """Render n samples with the current voice parameters (float model: tools/asn_test.py has the bit-exact integer one). pcm[so] = int8 array."""
        import numpy as np
        out = np.zeros(n, dtype=np.int32)
        act = []
        for v in self.v:
            lv = self.level_of(v.vol)
            if lv > 0 and v.smp in pcm:
                act.append((v, lv))
        g = gains[0] if len(act) <= 2 else gains[1]
        lim = int(round(128 * g))
        for v, lv in act:
            per = max(PMIN, min(PMAX, v.per))
            inc = ((K4 // per) << 2) / 65536.0
            data = pcm[v.smp]
            ln = len(data)
            pos = v.idx + v.frac / 65536.0
            idxs = (pos + inc * np.arange(n)).astype(np.int64) % ln
            scale = min(lv * 4, 64) / 64.0
            s = np.round(data[idxs].astype(np.float64) * scale * g)
            s = np.clip(s, -lim, lim - 1)
            out += s.astype(np.int32)
            pos += inc * n
            pos %= ln
            v.idx, v.frac = int(pos), int((pos % 1) * 65536)
        return np.clip(out, -128, 127).astype(np.int8)


def render_sound(t, sid, secs=3.0, level=7, hold=False):
    import numpy as np
    from asn_build import region_pcm
    d = Driver(t)
    d.level = level
    pcm = {so: region_pcm(t, so, ln) for so, ln in t.regions}
    chunks = []
    spt = 6258.29 / 50.0
    carry = 0.0
    nt = int(secs * 50)
    d.last = sid if hold else -1
    for k in range(nt):
        d.tick(sid if k == 0 else None)
        carry += spt
        n = int(carry)
        carry -= n
        chunks.append(d.mix(n, {}, pcm))
    return np.concatenate(chunks)


def write_wavs(t, outdir: Path):
    import wave
    outdir.mkdir(parents=True, exist_ok=True)
    for sid in range(len(t.rows)):
        used = [w for w in t.rows[sid] if w != 0xFFFF]
        if not used:
            continue
        a = render_sound(t, sid, secs=3.0)
        with wave.open(str(outdir / f"sound{sid:02d}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(1)
            w.setframerate(6258)
            w.writeframes(bytes((int(x) + 128) & 255 for x in a))
    print("wrote", outdir)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import asn_build
    t = asn_build.Tables(asn_build.read_mwii(asn_build.ADF))
    write_wavs(t, Path(sys.argv[1] if len(sys.argv) > 1 else "alt/amiga/wav"))
