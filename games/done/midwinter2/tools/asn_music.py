#!/usr/bin/env python3
"""Midwinter 2: the Amiga MUSIC for the STE DMA driver (patch group asn_*, music part): data model, exact interpreter, bank section.

Everything is read from the user's own Amiga disk (the load file `MWII`, md5-checked by tools/asn_build.py); nothing from it is in git.
Format and evidence: work/notes/amiga_music.md (sections 3-5), port notes: work/notes/amiga_music_port.md.

  amiga_image(mwii)      the load file relocated like the study's flat dump: hunk 0 at operand address $270d0, hunk 3 (chip data) at $89478
  Music(mem)             the Amiga driver ($5760c start, $57720 tick) as an interpreter: per tick the list of Paula register writes.
                         `fixed_env=True` = the PORT's behaviour for a channel that never ran an ENV command (tunes 3/11/13 channel 1 read
                         their volume from Amiga low memory): a constant volume FIXVOL instead.
  Paula                  register file + DMA latch semantics the STE mixer implements (LC/LEN latched at DMA start and at each end of cycle)
  build_music(...)       the bank section: tune table, lists, patterns, envelopes, instrument descriptors (pointers = RAM addresses), samples
  Mixer                  integer model of the blob's mixer (16.16 stepping, groups of 8, volume tables): bit exact, used by tools/asn_mus_test.py
"""
from __future__ import annotations

import struct

B = 0x270D0                 # operand address of hunk 0 byte 0 (the addresses of the disassembly and of amiga_music.md)
H3 = 0x89478                # operand address of hunk 3 (chip DATA: sfx pool 81544 B, then the music instruments)
TUNE_TABLE = 0x57E78        # 16 B per tune: 4 pattern-list pointers
NTUNES = 17
IDLE_STREAM, IDLE_LIST, SILENCE_ENV, SIL_LOOP = 0x58304, 0x582FC, 0x5C3F4, 0x5C292
PAL = 3546895
FIXVOL = 32                 # the port's volume of a channel without an envelope
FIX = 0x7FFF0000            # model-only address of that envelope's terminator (w16(FIX) = $ff, w16(FIX - 2) = FIXVOL)
ARGS = {0x00: 0, 0x04: 4, 0x08: 0, 0x0C: 4, 0x10: 8, 0x14: 12, 0x18: 0, 0x1C: 0, 0x20: 2, 0x24: 0, 0x28: 0, 0x2C: 0, 0x30: 0, 0x34: 0, 0x38: 4}
PAD = 48                    # bytes after every sample region: the mixer checks the end only every 8 outputs (8 x 5.02 bytes at most)


def amiga_image(mwii: bytes) -> bytes:
    """MWII with every hunk relocated to its operand address; index = address - B (identical to the study's mwii_flat.bin)."""
    be = lambda o: struct.unpack_from(">I", mwii, o)[0]
    assert be(0) == 0x3F3 and be(4) == 0
    n = be(8)
    sizes = [(be(20 + 4 * i) & 0x3FFFFFFF) * 4 for i in range(n)]
    bases, a = [], B
    for s in sizes:
        bases.append(a)
        a += s
    img = bytearray(a - B)
    p = 20 + 4 * n
    for i in range(n):
        t = be(p) & 0x3FFFFFFF
        ln = be(p + 4) * 4
        p += 8
        data = bytearray()
        if t in (0x3E9, 0x3EA):
            data = bytearray(mwii[p:p + ln])
            p += ln
        while True:
            hk = be(p) & 0x3FFFFFFF
            p += 4
            if hk == 0x3F2:
                break
            if hk != 0x3EC:
                raise SystemExit(f"hunk {i}: unexpected block ${hk:x}")
            while True:
                c = be(p)
                p += 4
                if c == 0:
                    break
                tgt = be(p)
                p += 4
                for _ in range(c):
                    o = be(p)
                    p += 4
                    struct.pack_into(">I", data, o, struct.unpack_from(">I", data, o)[0] + bases[tgt])
        img[bases[i] - B:bases[i] - B + len(data)] = data
    assert bases[0] == B and bases[3] == H3, [hex(x) for x in bases]
    return bytes(img)


class Mem:
    def __init__(self, img: bytes, lowmem: bytes | None = None):
        self.img, self.low = img, lowmem

    def u16(self, a):
        if a == FIX:
            return 0xFF
        if a == FIX - 2:
            return FIXVOL
        if a < 0x400:               # Amiga low memory: `move.w $0.l,..` (a slip: meant #0) and envelope reads of a channel without ENV
            return (self.low[a] << 8 | self.low[a + 1]) if self.low else 0
        return struct.unpack_from(">H", self.img, a - B)[0]

    def u32(self, a):
        return struct.unpack_from(">I", self.img, a - B)[0]


class Rec:
    pass


class Music:
    """The MWII music routine; `out` collects (register, value) writes: LCn LENn PERn VOLn DMACON.  (work/music_study/amiga/sim.py with a
    memory object; tools/asn_mus_test.py checks the two produce the same stream when the study's files are present.)"""

    def __init__(self, mem: Mem, fixed_env: bool = False):
        self.m, self.fixed = mem, fixed_env
        self.out, self.recs, self.ev, self.tickno = [], [], [], 0

    def start(self, tune):
        o, m = self.out, self.m
        o.append(("DMACON", 0x000F))                      # $5750a hardware reset
        for c in range(4):
            o.append((f"LC{c}", 0))
        for c in range(4):
            o.append((f"LEN{c}", 0x10))
        for c in range(4):
            o.append((f"VOL{c}", 0))
        for c in range(4):
            o.append((f"PER{c}", 1))
        self.recs = []
        for c in range(4):
            r = Rec()
            r.ch = c
            r.cnt = r.state = r.per = r.slide = r.step = r.target = r.delay = r.vib = 0
            r.env = r.env0 = FIX if self.fixed else 0
            r.ev, r.lst, r.lst0 = IDLE_STREAM, IDLE_LIST, m.u32(TUNE_TABLE + 16 * tune + 4 * c)
            r.lc = r.len = r.lc2 = r.len2 = r.vcnt = r.vrel = r.vup = r.vdn = r.vdel = r.vdelrel = 0
            r.voladd = r.voladdf = r.inst = r.wraps = 0
            self.recs.append(r)

    def tick(self):
        for r in self.recs:
            self.chan(r)
        self.tickno += 1

    def chan(self, r):
        c = r.ch
        o = self.out
        if r.cnt == 0:
            return self.new_event(r, c)
        if r.cnt == 1:
            if r.state != 0:
                o.append(("DMACON", 1 << c))
            r.cnt -= 1
            return self.proc(r, c)
        if r.state == 3:
            o.append((f"LC{c}", r.lc2))
            o.append((f"LEN{c}", r.len2))
            r.state = 1
        r.cnt = (r.cnt - 1) & 0xFFFF
        self.proc(r, c)

    def proc(self, r, c):
        chg = 0
        d2 = r.per
        if r.slide != 0:
            if r.delay != 0:
                r.delay -= 1
            else:
                chg += 1
                if r.slide == 1:
                    d2 = (d2 + r.step) & 0xFFFF
                    if not r.target >= d2:
                        d2 = r.target
                        r.slide = 0
                else:
                    d2 = (d2 - r.step) & 0xFFFF
                    if not r.target < d2:
                        d2 = r.target
                        r.slide = 0
        if r.vib != 0:
            if r.vdel != 0:
                r.vdel -= 1
            elif r.vcnt != 0:
                r.vcnt -= 1
            else:
                r.vcnt = r.vrel
                chg += 1
                if r.vib < 3:
                    d2 = (d2 - r.vdn) & 0xFFFF
                    r.vib += 1
                else:
                    d2 = (d2 + r.vup) & 0xFFFF
                    r.vib += 1
                    if r.vib == 5:
                        r.vib = 1
        if chg:
            r.per = d2
            self.out.append((f"PER{c}", d2))
        self.vol(r, c)

    def vol(self, r, c):
        w = self.m.u16
        a1 = r.env
        if w(a1) == 0xFF:
            self.out.append((f"VOL{c}", w(a1 - 2)))
        elif r.voladdf == 1:
            self.out.append((f"VOL{c}", (w(a1) + r.voladd) & 0xFFFF))
            a1 += 2
        else:
            self.out.append((f"VOL{c}", w(a1)))
            a1 += 2
        r.env = a1

    def new_event(self, r, c):
        o, m = self.out, self.m
        w, l = m.u16, m.u32
        r.voladdf = w(0)
        a1 = r.ev
        while True:
            d0 = w(a1)
            a1 += 2
            if d0 > 0x64:
                r.per = d0
                o.append((f"PER{c}", d0))
                r.cnt = (w(a1) - 1) & 0xFFFF
                a1 += 2
                r.ev = a1
                r.env = r.env0
                r.vdel = r.vdelrel
                if r.vib != 0:
                    r.vib = 1
                if r.state != 0:
                    r.state = 3
                    o.append((f"LC{c}", r.lc))
                    o.append((f"LEN{c}", r.len))
                o.append(("DMACON", 0x8200 | 1 << c))
                return self.vol(r, c)
            if d0 == 0x00:
                return
            elif d0 == 0x04:
                a3 = l(a1)
                a1 += 4
                r.inst = a3
                r.state = w(a3)
                r.lc, r.len = l(a3 + 2), w(a3 + 6)
                if r.state == 0:
                    o.append((f"LC{c}", r.lc))
                    o.append((f"LEN{c}", r.len))
                else:
                    r.lc2, r.len2 = l(a3 + 8), w(a3 + 12)
            elif d0 == 0x08:
                p = r.lst
                if l(p) == 0:
                    r.wraps += 1
                    self.ev.append(("WRAP", c, self.tickno))
                    r.lst = p = r.lst0
                r.lst += 4
                a1 = l(p)
            elif d0 == 0x0C:
                a4 = l(a1)
                a1 += 4
                r.voladd, r.env0 = w(a4 + 2), a4 + 4
            elif d0 == 0x10:
                r.slide, r.step, r.target, r.delay = w(a1), w(a1 + 2), w(a1 + 4), w(a1 + 6)
                a1 += 8
            elif d0 == 0x14:
                r.vib = 1
                r.vcnt, r.vrel, r.vup, r.vdn, r.vdel, r.vdelrel = (w(a1 + 2 * i) for i in range(6))
                a1 += 12
            elif d0 == 0x18:
                r.slide = 0
            elif d0 == 0x1C:
                r.vib = 0
            elif d0 == 0x20:
                r.cnt = (w(a1) - 1) & 0xFFFF
                a1 += 2
                r.ev = a1
                r.env = SILENCE_ENV
                o.append((f"VOL{c}", 0))
                return self.vol(r, c)
            elif d0 in (0x24, 0x28):
                o.append(("DMACON", 1 << c))
                o.append(("PER0", 1))
                o.append((f"VOL{c}", 0))
                return
            elif d0 in (0x2C, 0x30):
                pass                                     # LED filter on / off (modelled by filtering the instruments at build time)
            elif d0 == 0x34:
                r.voladdf = 1
            elif d0 == 0x38:
                a1 = l(a1)
            else:
                raise ValueError(hex(d0))


class Paula:
    """Register file of the four channels as the port keeps it: per, vol, lc, len (the registers), on (DMACON bit) and the latched buffer
    cur = (lc, len) taken at a DMA start; `restart[c]` counts DMA starts."""

    def __init__(self):
        self.per = [1] * 4
        self.vol = [0] * 4
        self.lc = [0] * 4
        self.len = [0x10] * 4
        self.on = [False] * 4
        self.cur = [(0, 0x10)] * 4
        self.restart = [0] * 4

    def apply(self, writes):
        for k, v in writes:
            if k == "DMACON":
                for c in range(4):
                    if v & (1 << c):
                        if v & 0x8000:
                            if not self.on[c]:
                                self.on[c] = True
                                self.cur[c] = (self.lc[c], self.len[c])
                                self.restart[c] += 1
                        else:
                            self.on[c] = False
            else:
                c = int(k[-1])
                getattr(self, k[:-1].lower())[c] = v


# ---- the data of the tunes ------------------------------------------------------------------------------------------------------------------
def read_list(m: Mem, p):
    out = []
    while m.u32(p):
        out.append(m.u32(p))
        p += 4
        assert len(out) < 400
    return out


def parse_pattern(m: Mem, p):
    """[(address, kind, args)] up to and including the NEXT that ends it; kind 'N' = note (period, duration) else the command word."""
    ev = []
    a = p
    while True:
        w = m.u16(a)
        if w > 0x64:
            ev.append((a, "N", (w, m.u16(a + 2))))
            a += 4
            continue
        if w not in ARGS:
            raise SystemExit(f"pattern ${p:x}: unknown command ${w:x} at ${a:x}")
        n = ARGS[w]
        ev.append((a, w, tuple(m.u16(a + 2 + i) for i in range(0, n, 2))))
        a += 2 + n
        if w in (0x00, 0x08, 0x24, 0x28, 0x38):
            return ev, a


class Tune:
    def __init__(self, m: Mem, n: int):
        self.n = n
        self.lists = [read_list(m, m.u32(TUNE_TABLE + 16 * n + 4 * c)) for c in range(4)]
        self.pats = {}
        self.envs, self.insts = set(), set()
        for L in self.lists:
            for p in L:
                if p in self.pats:
                    continue
                ev, end = parse_pattern(m, p)
                if ev[-1][1] != 0x08:
                    raise SystemExit(f"tune {n}: pattern ${p:x} ends with command ${ev[-1][1]:x}, not NEXT (the port handles it, the builder does not)")
                self.pats[p] = (ev, end)
                for a, k, args in ev:
                    if k == 0x0C:
                        self.envs.add(m.u32(a + 2))
                    elif k == 0x04:
                        self.insts.add(m.u32(a + 2))


def env_bytes(m: Mem, e):
    """volsub.w, voladd.w, steps..., $00ff (the hold reads the word before the terminator, which may be the voladd word)."""
    q = e + 4
    while m.u16(q) != 0xFF:
        q += 2
        assert q - e < 200
    return m.img[e - B:q + 2 - B]


def inst_fields(m: Mem, a):
    return m.u16(a), m.u32(a + 2), m.u16(a + 6), m.u32(a + 8), m.u16(a + 12)


def usage(m: Mem, tunes, cap=7000):
    """Per tune: loop length in ticks (every channel wrapped twice or `cap`), and per instrument LC the ticks played at each period
    (DMA on, volume > 0): the weights for the build-time filter and the statistics."""
    res = {}
    for n in tunes:
        mu = Music(m, fixed_env=True)
        mu.start(n)
        pa = Paula()
        pa.apply(mu.out)
        use = {}
        t = 0
        while t < cap and not all(r.wraps >= 2 for r in mu.recs):
            mu.out = []
            mu.tick()
            pa.apply(mu.out)
            for c in range(4):
                if pa.on[c] and pa.vol[c] > 0:
                    d = use.setdefault(pa.cur[c][0], {})
                    d[pa.per[c]] = d.get(pa.per[c], 0) + 1
            t += 1
        res[n] = (t, use)
    return res


def led_filter(pcm, rate_hz: float, loop: bool, fc: float = 3300.0):
    """The Amiga's LED low-pass (on in every tune) as two one-pole sections at `fc`, applied to an instrument at the rate it is mostly played at.
    Loops are filtered circularly (steady state), one-shots from silence."""
    import numpy as np
    x = np.asarray(pcm, dtype=np.float64)
    a = 1.0 - np.exp(-2.0 * np.pi * fc / rate_hz)
    for _ in range(2):
        y = np.empty_like(x)
        s = 0.0
        if loop:
            for v in x:                                  # settle on one pass of the loop
                s += a * (v - s)
        for i, v in enumerate(x):
            s += a * (v - s)
            y[i] = s
        x = y
    return np.clip(np.round(x), -128, 127).astype(np.int8)


def build_music(m: Mem, tunes: list[int], base: int, sil: int, led: bool = True, rates: dict | None = None, gains: dict | None = None):
    """The music section, to be loaded at RAM address `base` (even).  `sil` = RAM address of >= 16 + PAD zero bytes (the one-shots' second part).
    Returns (bytes, info).  Layout (all pointers are RAM addresses):
      +$000 tune table: 18 x 16 B (tune 0..17; 4 list pointers, first = 0: the tune is not in the bank -> YM)
      +$120 18 x 2 B flags: rate (0 = 6258 Hz, 1 = 12517 Hz), gain set (index of the volume table set)
      +$144 idle list (long 0), idle stream (words $2c $18 $1c $08), silence envelope (8 zero words, $ff), fixed envelope (0, FIXVOL, $ff)
      then lists, patterns, envelopes, instrument descriptors (flag.w LC1.l LEN1.w LC2.l LEN2.w, lengths in words), samples (+PAD each)."""
    import numpy as np
    rates = rates or {}
    gains = gains or {}
    T = {n: Tune(m, n) for n in tunes}
    out = bytearray(0x144)
    info = dict(base=base, tunes=list(tunes))

    def put(b):
        if len(out) & 1:
            out.append(0)
        a = base + len(out)
        out.extend(b)
        return a

    info["idle_list"] = put(bytes(4))
    info["idle"] = put(struct.pack(">4H", 0x2C, 0x18, 0x1C, 0x08))
    info["silenv"] = put(bytes(16) + b"\x00\xff")
    fx = put(struct.pack(">3H", 0, FIXVOL, 0xFF))
    info["fixenv"] = fx + 4
    # patterns: the union of their address ranges, copied verbatim (patterns share tails), pointers rewritten below
    iv = sorted({(p, e) for t in T.values() for p, (ev, e) in t.pats.items()})
    merged = []
    for p, e in iv:
        if merged and p < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([p, e])
    pmap = {}                      # Amiga address range -> RAM address
    patfix = set()                 # (offset in out, kind, amiga pointer); patterns that share a tail name the same pointer twice
    for p, e in merged:
        a = put(m.img[p - B:e - B])
        pmap[(p, e)] = a
    def paddr(x):
        for (p, e), a in pmap.items():
            if p <= x < e:
                return a + x - p
        raise KeyError(hex(x))
    for t in T.values():
        for p, (ev, e) in t.pats.items():
            for a, k, args in ev:
                if k in (0x04, 0x0C):
                    patfix.add((paddr(a + 2) - base, k, m.u32(a + 2)))
    # envelopes
    emap = {}
    for e in sorted({e for t in T.values() for e in t.envs}):
        emap[e] = put(env_bytes(m, e))
    # instrument descriptors + samples
    insts = sorted({i for t in T.values() for i in t.insts})
    use = usage(m, tunes)
    info["loops"] = {n: use[n][0] for n in tunes}
    wsum = {}
    for n in tunes:
        for lc, d in use[n][1].items():
            w = wsum.setdefault(lc, {})
            for per, k in d.items():
                w[per] = w.get(per, 0) + k
    dmap, smap, sdata = {}, {}, {}
    for i in insts:
        flag, lc1, len1, lc2, len2 = inst_fields(m, i)
        if flag != 1 or not (lc2 == SIL_LOOP or (lc2 == lc1 and len2 == len1)):
            raise SystemExit(f"instrument ${i:x}: unexpected shape {flag} {lc1:x} {len1} {lc2:x} {len2}")
        loop = lc2 == lc1
        a0 = lc1 & ~1                                   # Paula ignores bit 0 of AUDxLC
        pcm = np.frombuffer(m.img[a0 - B:a0 - B + 2 * len1], dtype=np.int8)
        if led:
            w = wsum.get(lc1)
            if w:                                       # duration-weighted median playing rate
                ks = sorted(w.items())
                half, acc = sum(w.values()) / 2, 0
                for per, k in ks:
                    acc += k
                    if acc >= half:
                        break
                rate = PAL / per
            else:
                rate = 15625.0
            pcm = led_filter(pcm, rate, loop)
            info.setdefault("filter_rate", {})[i] = rate
        sdata[i] = (pcm.tobytes(), loop)
    for i in insts:
        dmap[i] = put(bytes(14))
    for i in insts:
        pcm, loop = sdata[i]
        smap[i] = put(pcm + ((pcm * (PAD // len(pcm) + 1))[:PAD] if loop else bytes(PAD)))
    for i in insts:
        flag, lc1, len1, lc2, len2 = inst_fields(m, i)
        loop = lc2 == lc1
        struct.pack_into(">HIHIH", out, dmap[i] - base, flag, smap[i], len1, smap[i] if loop else sil, len2)
    for off, k, ptr in patfix:
        assert struct.unpack_from(">I", out, off)[0] == ptr
        struct.pack_into(">I", out, off, dmap[ptr] if k == 0x04 else emap[ptr])
    # lists + tune table
    lmap = {}
    for n in tunes:
        for c in range(4):
            key = tuple(T[n].lists[c])
            if key not in lmap:
                lmap[key] = put(b"".join(struct.pack(">I", paddr(p)) for p in key) + bytes(4))
            struct.pack_into(">I", out, 16 * n + 4 * c, lmap[key])
        out[0x120 + 2 * n] = rates.get(n, 1)
        out[0x121 + 2 * n] = gains.get(n, 0)
    if len(out) & 1:
        out.append(0)
    info.update(lc={m.u32(i + 2): smap[i] for i in insts}, lcraw={i: (smap[i], sdata[i][1], len(sdata[i][0])) for i in insts}, desc=dmap, env=emap,
                paddr=paddr, sil=sil, sample_bytes=sum(len(sdata[i][0]) + PAD for i in insts), score_bytes=len(out) - sum(len(sdata[i][0]) + PAD for i in insts),
                insts=insts)
    return bytes(out), info


# ---- the blob's music side as an integer model (patches/asn/blob.s): slots, volumes, mixer, silent advance --------------------------------------
K_SFX, SH_SFX, PMIN_SFX = 9285653, 2, 142        # 6258 Hz, the sound effects: inc16 = (K / period) << SH
K_MUS, PMIN_MUS = 4642826, 113                    # music: (K / period) << 2 at 12517 Hz, << 3 at 6258 Hz
PMAX = 2000
RL = 2048
ATT = [256, 256, 256, 181, 128, 91, 64, 45, 32, 23, 16, 11, 8, 6, 4, 0]      # $b9a (YM attenuation, 2 = normal, ~3 dB per step) -> volume x / 256


def level_of(vol88: int) -> int:
    """Mixer level 0..16 of an 8.8 volume (asm: asn_prep)."""
    if vol88 & 0x8000:
        return 0
    return (min(64, vol88 >> 8) + 2) >> 2


def inc_of(per: int, k: int, sh: int, pmin: int):
    """(fraction, integer) of the 16.16 phase increment (asm: asn_inc)."""
    per = max(pmin, min(PMAX, per))
    v = ((k // per) & 0xFFFF) << sh
    return v & 0xFFFF, v >> 16


class Slot:
    """A mixer voice: the blob's $20-byte record.  smp / lnw = the buffer being played (Paula's latch, length in words), nsmp / nlnw = AUDxLC / AUDxLEN."""

    def __init__(self, sil=0):
        self.vol = self.avol = self.dma = self.dead = self.idx = self.frac = self.incf = self.inci = self.lv = 0
        self.per = 1
        self.smp = self.nsmp = sil
        self.lnw = self.nlnw = 0x10
        self.vt = 0


def mix(mem: bytes, bank: int, ring: bytearray, wr: int, n8: int, voices, music: bool, sil: int) -> int:
    """asn_mix: `voices` (list order: the first stores, the others add) into the ring from `wr`, n8 groups of 8 outputs; returns the new cursor.
    At the start of every group, while idx >= length the buffer ends: sound effects loop it; music takes the pending LC / LEN (Paula) and a
    voice that lands in the silence region is dead (it reads zeros and stops advancing)."""
    for k, v in enumerate(voices):
        pos = wr
        smp, ln, idx, frac, incf, inci = v.smp, (2 * v.lnw) & 0xFFFF, v.idx, v.frac, v.incf, v.inci
        vt = v.vt - bank
        for _ in range(n8):
            while idx >= ln:
                idx = (idx - ln) & 0xFFFF
                zero = ln == 0
                if music:
                    smp, v.smp, v.lnw = v.nsmp, v.nsmp, v.nlnw
                    ln = (2 * v.lnw) & 0xFFFF
                    zero = ln == 0 or smp == sil
                    if zero:
                        v.dead = 0xFFFF
                if zero:
                    smp, ln, idx, frac, incf, inci = sil, 0xFFFF, 0, 0, 0, 0
            base = smp - bank
            for _ in range(8):
                o = mem[vt + mem[base + idx]]
                ring[pos] = o if k == 0 else (ring[pos] + o) & 0xFF
                pos = (pos + 1) & (RL - 1)
                frac += incf
                idx = (idx + inci + (frac >> 16)) & 0xFFFF
                frac &= 0xFFFF
        v.idx, v.frac = idx, frac
    if not voices:
        for i in range(n8 * 8):
            ring[(wr + i) & (RL - 1)] = 0
    return (wr + n8 * 8) & (RL - 1)


class BlobModel:
    """What the blob does with a tune: the driver's Paula writes land in four slots (mus_chan ..), mus_vols, asn_prep, asn_mix, mus_skip."""

    def __init__(self, m: Mem, bank: bytes, bank_addr: int, info: dict, vt_base: int, fixed_env: bool = True):
        self.m, self.bank, self.base, self.info, self.vt = m, bank, bank_addr, info, vt_base
        self.sil = info["sil"]
        self.fixed = fixed_env
        self.lc = dict(info["lc"])
        self.lc[SIL_LOOP] = self.sil

    def start(self, tune: int, rate: int, gainset: int, mu=None):
        """`mu` = another implementation of the driver with the same interface (start / tick / out), e.g. the study's sim.py."""
        self.mu = mu or Music(self.m, fixed_env=self.fixed)
        self.mu.start(tune)
        self.mu.out = []
        self.slots = [Slot(self.sil) for _ in range(4)]
        self.sh = 2 if rate else 3
        self.gset = gainset
        self.restarts = [0] * 4

    def tick(self):
        mu = self.mu
        mu.out = []
        mu.tick()
        for k, v in mu.out:
            if k == "DMACON":
                for c in range(4):
                    if v & (1 << c):
                        s = self.slots[c]
                        if not v & 0x8000:
                            s.dma = 0
                        elif not s.dma or s.dead:      # a start: the channel was off, or sat in the silence loop
                            s.dma, s.dead = 1, 0
                            s.smp, s.lnw, s.idx, s.frac = s.nsmp, s.nlnw, 0, 0
                            self.restarts[c] += 1
                continue
            s = self.slots[int(k[-1])]
            if k.startswith("PER"):
                s.per = v
            elif k.startswith("VOL"):
                s.avol = v
            elif k.startswith("LEN"):
                s.nlnw = v
            else:
                s.nsmp = self.lc.get(v, self.sil)

    def vols(self, att: int = 2):
        for s in self.slots:
            s.vol = min(s.avol, 64) * ATT[att & 15] if s.dma and not s.dead else 0

    def prep(self):
        act = []
        for s in self.slots:
            s.lv = level_of(s.vol)
            if s.lv:
                s.incf, s.inci = inc_of(s.per, K_MUS, self.sh, PMIN_MUS)
                s.vt = self.vt + (self.gset * 16 + s.lv - 1) * 256
                act.append(s)
        return act

    def skip(self, n: int):
        """mus_skip: voices that play at volume 0 advance n outputs."""
        if n == 0:
            return
        for s in self.slots:
            if not s.dma or s.dead or s.lv:
                continue
            s.incf, s.inci = inc_of(s.per, K_MUS, self.sh, PMIN_MUS)
            d = s.incf * n + s.frac
            s.frac = d & 0xFFFF
            i = (d >> 16) + s.inci * n + s.idx
            ln = 2 * s.lnw
            while i >= ln:
                i -= ln
                if ln:
                    s.smp, s.lnw = s.nsmp, s.nlnw
                    ln = 2 * s.lnw
                    if s.smp != self.sil:
                        continue
                s.dead, i, s.frac = 0xFFFF, 0, 0
                break
            s.idx = i & 0xFFFF

    def render(self, ring: bytearray, wr: int, n8: int) -> int:
        """asn_prep + asn_mix + mus_skip for one VBL that mixes n8 groups."""
        act = self.prep()
        wr = mix(self.bank, self.base, ring, wr, n8, act, True, self.sil)
        self.skip(n8 * 8)
        return wr


def render(m: Mem, bank: bytes, bank_addr: int, info: dict, tune: int, ticks: int, rate: int = 1, gainset: int = 0, vt_base: int = 0,
           att: int = 2, spt: float | None = None):
    """Model render of a tune as the blob plays it: per tick the driver, then that tick's share of samples (whole groups of 8).
    Returns the DMA bytes (signed 8 bit) at 12517 Hz (rate 1) or 6258 Hz (rate 0)."""
    bm = BlobModel(m, bank, bank_addr, info, vt_base)
    bm.start(tune, rate, gainset)
    out = bytearray()
    spt = spt or (12516.58 if rate else 6258.29) / 50.053
    acc = 0.0
    for _ in range(ticks):
        bm.tick()
        bm.vols(att)
        acc += spt
        n8 = int(acc) // 8
        acc -= n8 * 8
        ring = bytearray(RL)
        bm.render(ring, 0, n8)
        out += ring[:n8 * 8]
    return out
