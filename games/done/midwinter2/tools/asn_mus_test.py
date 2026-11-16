#!/usr/bin/env python3
"""Tests of the music part of patches/asn/blob.s (the Amiga music on the STE's DMA sound) in the Unicorn 68000 emulator.

    python3 tools/asn_mus_test.py unit [--ticks 1700] [--tunes N ...]     all of the checks below
    python3 tools/asn_mus_test.py clip                                    the 8-bit mix of every tune over its whole loop never overflows
    ASN_NEG=1 python3 tools/asn_mus_test.py unit                          negative control: the reference plays channel 2 one period unit off

  spec   : tools/asn_music.py `Music` (the interpreter the tools use) against the study's work/music_study/amiga/sim.py (the SPEC, verified tick for
           tick against the Amiga emulator): identical Paula write streams for the 17 tunes (skipped when the study's files are absent).
  player : the REAL entry points of the blob (asn_mstart with the tune in $b96, then asn_mtick once per VBL, DMA position fed like the hardware)
           against the model: after every VBL the four voices' AUDxPER / AUDxVOL / AUDxLC / AUDxLEN / DMA bit, the latched buffer, phase, dead flag,
           the mixer volume, AND the whole 2048-byte DMA ring, write cursor and DMA state.  The reference driver is sim.py itself when present.
           Runs every tune of the bank at its own rate, 50 Hz; tune 1 also at 60 Hz (five ticks per six VBL) and with DMA underruns.
  mixer  : asn_prep + asn_mix (+ mus_skip) on random voice states, sound-effect mode and music mode, bit exact against the integer model
           (buffer ends inside the call: loops, one-shots, Paula's reload, voices at volume 0).
  iface  : the vector-table behaviour: YM machines and tunes missing from the bank go to the YM driver ($c6c / $d0e, which really run here: FFA
           file 8 is loaded), a DMA tune parks the YM driver on tune 0, $b9a attenuation, the once flag ($ba2), restart, the start lock.
"""
from __future__ import annotations

import argparse
import os
import random
import re
import struct
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import asn_build  # noqa: E402
import asn_music as AM  # noqa: E402

from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UcError  # noqa: E402
from unicorn import m68k_const as mc  # noqa: E402

BANK = asn_build.BANK
SV, MS, RING, VT = BANK + asn_build.OFF_SV, BANK + asn_build.OFF_MS, BANK + asn_build.OFF_RING, BANK + asn_build.OFF_VT
RL = asn_build.RL
V0, VS = 0x40, 0x20
STUDY = ROOT / "work" / "music_study" / "amiga"
NEG = bool(os.environ.get("ASN_NEG"))
PAR = {1: dict(target=640, thr=656, maxg=64, nom=250), 0: dict(target=320, thr=336, maxg=32, nom=125)}        # blob.s par_m12 / par_m6
# the fixed entries at the start of the blob: what the patch sites and the vector table really call (patches/asn_*.s)
ENTRY = {n: asn_build.CODE + 6 * i for i, n in enumerate(("asn_tick", "asn_wd", "asn_lvc", "asn_lv1", "asn_lv2", "asn_mtick", "asn_mstart"))}


def study_sim():
    """work/music_study/amiga/sim.py (needs its mwii_flat.bin), or None."""
    if not (STUDY / "sim.py").exists() or not (STUDY / "mwii_flat.bin").exists():
        return None
    sys.path.insert(0, str(STUDY))
    import sim
    return sim


class Machine:
    def __init__(self, bank: bytes):
        with tempfile.TemporaryDirectory() as td:
            lst = Path(td) / "a.lst"
            asn_build.assemble_blob(lst)
            self.syms = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"^(\w[\w.$]*)\s+A:([0-9A-F]+)\s*$", lst.read_text(), re.M)}
        u = self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        u.ctl_set_cpu_model(mc.UC_CPU_M68K_M68000)
        u.mem_map(0, 0x200000)
        u.mem_map(0xFF8000, 0x8000)
        u.mem_map(0xFFFF8000, 0x8000)
        import mw2patch
        self.file8 = mw2patch.image_bytes("FFA", 8)
        self.bank = bank
        self.stop = 0x1FF000
        self.reset()

    def reset(self):
        u = self.uc
        u.mem_write(0, bytes(0x1000))
        u.mem_write(0x806, self.file8)            # vector table + the YM driver + its tunes ($806-$3104)
        u.mem_write(BANK, self.bank)
        u.mem_write(self.stop, b"\x4e\x71")
        u.mem_write(0xFFFF820A, b"\x02")           # 50 Hz
        u.mem_write(0xFF8900, bytes(0x40))
        self.w8(0xB9A, 2)

    def call(self, label, **regs):
        u = self.uc
        sp = 0x1F0000
        u.reg_write(mc.UC_M68K_REG_A7, sp - 4)
        u.mem_write(sp - 4, struct.pack(">I", self.stop))
        for k, v in regs.items():
            u.reg_write(getattr(mc, "UC_M68K_REG_" + k.upper()), v)
        try:
            u.emu_start(ENTRY.get(label) or self.syms[label] if isinstance(label, str) else label, self.stop, timeout=0, count=20_000_000)
        except UcError as e:
            raise RuntimeError(f"UcError {e} at pc ${u.reg_read(mc.UC_M68K_REG_PC):x} in {label}")
        if u.reg_read(mc.UC_M68K_REG_PC) != self.stop:
            raise RuntimeError(f"{label}: did not return (pc ${u.reg_read(mc.UC_M68K_REG_PC):x})")

    def rd(self, a, n):
        return bytes(self.uc.mem_read(a, n))

    def r8(self, a):
        return self.rd(a, 1)[0]

    def r16(self, a):
        return struct.unpack(">H", self.rd(a, 2))[0]

    def r32(self, a):
        return struct.unpack(">I", self.rd(a, 4))[0]

    def w8(self, a, v):
        self.uc.mem_write(a, bytes([v & 255]))

    def w16(self, a, v):
        self.uc.mem_write(a, struct.pack(">H", v & 0xFFFF))

    def w32(self, a, v):
        self.uc.mem_write(a, struct.pack(">I", v & 0xFFFFFFFF))

    def slot(self, c):
        raw = self.rd(SV + V0 + c * VS, VS)
        vol, avol, per, dma, nsmp, nlnw, dead, smp, lnw, idx, frac, incf, inci, lv = struct.unpack(">4HIHHIH5H", raw)
        return dict(vol=vol, avol=avol, per=per, dma=dma, nsmp=nsmp, nlnw=nlnw, dead=dead, smp=smp, lnw=lnw, idx=idx, frac=frac, incf=incf, inci=inci, lv=lv)

    def set_slot(self, c, s: AM.Slot):
        self.uc.mem_write(SV + V0 + c * VS, struct.pack(">4HIHHIH5H", s.vol, s.avol, s.per, s.dma, s.nsmp, s.nlnw, s.dead, s.smp, s.lnw, s.idx, s.frac, 0, 0, 0))

    def dmapos(self, pos):
        a = RING + pos
        self.w8(0xFF8909, a >> 16)
        self.w8(0xFF890B, a >> 8)
        self.w8(0xFF890D, a)


CMP = ("vol", "avol", "per", "dma", "nsmp", "nlnw", "dead", "smp", "lnw", "idx", "frac")


def slot_of(s: AM.Slot):
    return {k: getattr(s, k) for k in CMP}


class Vbl:
    """asn_mixer as a model around AM.BlobModel: DMA start, top-up to the target, underrun resync, stop after 12 silent VBL, silent advance."""

    def __init__(self, bm: AM.BlobModel, rate: int):
        self.bm, self.p = bm, PAR[rate]
        self.ring = bytearray(RL)
        self.wr = self.dma = self.silent = self.n8 = 0

    def run(self, pos: int):
        bm, p = self.bm, self.p
        act = bm.prep()
        if not self.dma:
            if not act:
                bm.skip(p["nom"])
                return
            self.ring = bytearray(RL)
            self.n8 = min(p["target"] >> 3, p["maxg"])
            self.wr = AM.mix(bm.bank, bm.base, self.ring, 0, self.n8, act, True, bm.sil)
            self.dma, self.silent = 0xFF, 0
        else:
            lead = (self.wr - pos) & (RL - 1)
            if lead > p["thr"]:
                self.wr = (pos + 16) & (RL - 8)
                lead = 16
            self.n8 = 0
            d = p["target"] - lead
            if d > 0 and d >> 3:
                self.n8 = min(d >> 3, p["maxg"])
                self.wr = AM.mix(bm.bank, bm.base, self.ring, self.wr, self.n8, act, True, bm.sil)
            if not act:
                self.silent += 1
                if self.silent >= 12:
                    self.dma = 0
            else:
                self.silent = 0
        bm.skip(self.n8 * 8)


def unit_spec(t, ticks):
    sim = study_sim()
    if sim is None:
        print("spec  : the study's sim.py / mwii_flat.bin not found, skipped")
        return 0
    low = (STUDY / "lowmem_a1200_ks31_hd.bin").read_bytes() if (STUDY / "lowmem_a1200_ks31_hd.bin").exists() else None
    mem = AM.Mem(t.mem.img, low)
    bad = 0
    for tune in range(1, 18):
        a, b = sim.Music(), AM.Music(mem)
        a.start(tune)
        b.start(tune)
        for k in range(ticks + 1):
            if a.out != b.out:
                bad += 1
                print(f"SPEC MISMATCH tune {tune} tick {k}\n  sim.py {a.out}\n  model  {b.out}")
                break
            a.out, b.out = [], []
            a.tick()
            b.tick()
    print(f"spec  : asn_music.Music vs the study's sim.py, 17 tunes x {ticks} ticks of Paula writes, mismatching tunes {bad}")
    return bad


class NegMusic:
    """Negative control: the reference with every period write of channel 2 one unit off."""

    def __init__(self, mu):
        self.mu = mu

    def start(self, tune):
        self.mu.start(tune)
        self.out = self.mu.out

    def tick(self):
        self.mu.out = []
        self.mu.tick()
        self.out = [(k, v + 1) if k == "PER2" else (k, v) for k, v in self.mu.out]


def run_player(M: Machine, t, bank, info, tune, ticks, hz60=False, underruns=False, seed=0, att=None):
    """-> number of VBLs whose state differs (first one printed)."""
    sim = study_sim()
    rate, gset = info["rates"][tune], info["gains"][tune]
    bm = AM.BlobModel(t.mem, bank, BANK, info, VT)
    mu = sim.Music() if sim else AM.Music(t.mem, fixed_env=True)
    bm.start(tune, rate, gset, NegMusic(mu) if NEG else mu)
    vb = Vbl(bm, rate)
    M.reset()
    M.w8(SV, 2)                                   # mode: DMA (the probe is hardware)
    M.w32(0xB96, tune)
    if hz60:
        M.uc.mem_write(0xFFFF820A, b"\x00")
    M.call("asn_mstart")
    assert M.r8(SV + 0x12) == tune, "asn_mstart did not take the tune"
    rng = random.Random(seed)
    pos = 0.0
    acc = 0
    bad = 0
    step = (12516.58 if rate else 6258.29) / 50.053 * (50 / 60 if hz60 else 1)
    a = 2
    for k in range(ticks):
        if att is not None:
            a = att(k)
            M.w8(0xB9A, a)
        was = M.r8(0xFF8901) & 1
        if was:
            pos += step + rng.uniform(-6, 6)
            if underruns and rng.random() < 0.02:
                pos += rng.choice([300, 700, 1500])       # the VBL was held up
        ipos = int(pos) % RL
        M.dmapos(ipos)
        M.call("asn_mtick")
        tick = True
        if hz60:
            acc += 5
            tick = acc >= 6
            if tick:
                acc -= 6
        if tick:
            bm.tick()
        bm.vols(a)
        vb.run(ipos)
        if not was and M.r8(0xFF8901) & 1:
            pos = 0.0                                     # the DMA just started at the ring start
        ok = M.r16(SV + 4) == vb.wr and M.r8(SV + 2) == vb.dma and M.rd(RING, RL) == bytes(vb.ring) and bool(M.r8(0xFF8901) & 1) == bool(vb.dma)
        diff = None
        for c in range(4):
            got = {x: M.slot(c)[x] for x in CMP}
            if got != slot_of(bm.slots[c]):
                ok, diff = False, (c, got, slot_of(bm.slots[c]))
                break
        if not ok:
            bad += 1
            if bad == 1:
                print(f"PLAYER MISMATCH tune {tune} VBL {k}: wr {M.r16(SV + 4)}/{vb.wr} dma {M.r8(SV + 2)}/{vb.dma} ring_equal {M.rd(RING, RL) == bytes(vb.ring)}")
                if diff:
                    print(f"  voice {diff[0]}\n   blob  {diff[1]}\n   model {diff[2]}")
            if bad > 3:
                break
    return bad


def unit_player(M, t, bank, info, ticks, tunes):
    tot = 0
    res = []
    for tune in tunes:
        b = run_player(M, t, bank, info, tune, ticks, seed=tune)
        res.append((tune, b))
        tot += b
    print(f"player: asn_mstart + asn_mtick per VBL vs {'sim.py' if study_sim() else 'asn_music.Music'} + mixer model, {ticks} VBL each, "
          f"voices + ring + cursor; (tune, mismatching VBLs): {res}")
    b60 = run_player(M, t, bank, info, 1, ticks, hz60=True, seed=99)
    bun = run_player(M, t, bank, info, 1, ticks, underruns=True, seed=98)
    fade = run_player(M, t, bank, info, 1, 900, seed=97, att=lambda k: min(15, 2 + k // 20) if k < 400 else (15 if k < 600 else 2))
    print(f"player: tune 1 at 60 Hz (5 ticks / 6 VBL) {b60} mismatches; with DMA underruns {bun}; with a $b9a fade 2..15, mute, back to 2: {fade}")
    return tot + b60 + bun + fade


def unit_mixer(M, t, bank, info, trials=300):
    rng = random.Random(5)
    bad = 0
    sil = info["sil"]
    insts = list(info["lcraw"].values())                 # (address, loop, bytes)
    recs = [(struct.unpack(">I", bank[asn_build.OFF_REC + off + 0x16:asn_build.OFF_REC + off + 0x1A])[0], r["ln"]) for off, r in t.recs.items() if r["ln"]]
    for trial in range(trials):
        music = trial % 2 == 1
        M.reset()
        M.w8(SV, 2)
        if music:
            M.w8(SV + 0x12, rng.choice(info["tunes"]))
            M.call("mus_enter", a4=SV)
        else:
            M.call("asn_enter", a4=SV)
        rate = M.r8(SV + 0x14)
        gfix = M.r16(SV + 0x16)
        slots = []
        for c in range(4):
            s = AM.Slot(sil)
            if music:
                a, loop, nb = rng.choice(insts)
                s.dma = rng.choice([1, 1, 1, 0])
                s.avol = rng.choice([0, 0, 7, 20, 25, 35, 45, 54, 64, 80])
                s.per = rng.choice([1, 113, 127, 150, 227, 254, 320, 453, 600, 906, 1356, 2100])
                s.smp, s.lnw = a, nb // 2
                a2, _, nb2 = rng.choice(insts)
                s.nsmp, s.nlnw = rng.choice([(a, nb // 2), (sil, 8), (sil, 8), (a2, nb2 // 2)])
                s.idx = rng.choice([0, rng.randrange(nb), max(0, nb - rng.randrange(1, 300))])
            else:
                a, lnw = rng.choice(recs)
                s.vol = rng.choice([0, 0x0100, 0x0900, 0x1000, 0x2000, 0x3000, 0x3F00, 0x4800, 0x8000])
                s.per = rng.choice([248, 300, 400, 520, 632, 888, 1140, 2000, 142, 100])
                s.smp, s.lnw = a, lnw
                s.idx = rng.choice([rng.randrange(2 * lnw), max(0, 2 * lnw - rng.randrange(1, 200))])
                s.nsmp, s.nlnw, s.dma, s.dead = 0, 5, 0, 0xFFFF      # the effect driver's fields that share the bytes (count, record, sequence, group)
                s.avol = rng.randrange(65536)
            s.frac = rng.randrange(65536)
            slots.append(s)
            M.set_slot(c, s)
        att = rng.choice([0, 2, 2, 2, 3, 5, 9, 15])
        M.w8(0xB9A, att)
        wr = rng.randrange(0, RL // 8) * 8
        n8 = rng.randrange(1, 65 if music else 32)
        M.w16(SV + 4, wr)
        ring0 = bytes(rng.randrange(256) for _ in range(RL))
        M.uc.mem_write(RING, ring0)
        if music:
            M.call("mus_vols", a4=SV)
        M.call("asn_prep", a4=SV)
        M.call("asn_mix", a4=SV, d0=n8)
        if music:
            M.call("mus_skip", a4=SV, d0=n8 * 8)
        # model
        ring = bytearray(ring0)
        if music:
            for s in slots:
                s.vol = min(s.avol, 64) * AM.ATT[att] if s.dma and not s.dead else 0
        act = []
        for s in slots:
            s.lv = AM.level_of(s.vol)
            if s.lv:
                s.incf, s.inci = AM.inc_of(s.per, AM.K_MUS if music else AM.K_SFX, (2 if rate else 3) if music else AM.SH_SFX, AM.PMIN_MUS if music else AM.PMIN_SFX)
                act.append(s)
        for s in act:
            g = gfix if music else (0 if len(act) <= 2 else 16 * 256)
            s.vt = VT + g + (s.lv - 1) * 256
        nwr = AM.mix(bank, BANK, ring, wr, n8, act, music, sil)
        if music:
            bm = AM.BlobModel(t.mem, bank, BANK, info, VT)
            bm.slots, bm.sh = slots, 2 if rate else 3
            bm.skip(n8 * 8)
        fields = CMP if music else ("vol", "per", "smp", "lnw", "idx", "frac")
        ok = M.rd(RING, RL) == bytes(ring) and M.r16(SV + 4) == nwr and M.r16(SV + 16) == len(act)
        for c in range(4):
            got = M.slot(c)
            ok = ok and all(got[f] == getattr(slots[c], f) for f in fields)
        if not ok:
            bad += 1
            if bad < 4:
                print(f"MIXER MISMATCH trial {trial} music={music} n8={n8} wr={wr} k={len(act)}/{M.r16(SV + 16)} ring_equal={M.rd(RING, RL) == bytes(ring)}")
                for c in range(4):
                    print("   blob ", {f: M.slot(c)[f] for f in fields}, "\n   model", {f: getattr(slots[c], f) for f in fields})
    print(f"mixer : {trials} random trials (half sound-effect mode, half music mode), ring + cursor + voice state, mismatches {bad}")
    return bad


def unit_iface(M, t, bank, info):
    bad = []

    def chk(name, cond):
        if not cond:
            bad.append(name)

    ymtab = lambda n: M.r32(0x142C + 12 * n)          # the YM driver's first channel pointer of tune n
    missing = [n for n in range(1, 18) if n not in info["tunes"]]
    # a YM machine (mode 1): start and tick are the YM driver's
    M.reset()
    M.w8(SV, 1)
    M.w32(0xB96, 1)
    M.call("asn_mstart")
    chk("ym: tune 1 on the YM driver", M.r32(0x124E) == ymtab(1) and M.r8(SV + 0x12) == 0 and M.r16(0xC44) == 0)
    M.call("asn_mtick")
    chk("ym: the YM tick ran", M.r16(0xC2C) != 0 and M.r8(0xFF8901) == 0 and M.r8(SV + 2) == 0)
    # DMA machine, a tune that is not in the bank
    if missing:
        M.reset()
        M.w8(SV, 2)
        M.w32(0xB96, missing[0])
        M.call("asn_mstart")
        chk("fallback: missing tune on the YM driver", M.r32(0x124E) == ymtab(missing[0]) and M.r8(SV + 0x12) == 0)
    # DMA tune: YM parked on tune 0, $b96 kept
    M.reset()
    M.w8(SV, 2)
    M.w32(0xB96, 1)
    M.call("asn_mstart")
    chk("dma: tune 1 taken, YM driver parked on tune 0", M.r8(SV + 0x12) == 1 and M.r32(0x124E) == ymtab(0) and M.r32(0xB96) == 1 and M.r8(SV + 0x13) == 0)
    heard = 0
    for k in range(40):
        M.dmapos((k * 250) % RL)
        M.call("asn_mtick")
        heard += any(M.slot(c)["vol"] for c in range(4))
    chk("dma: ring running", M.r8(0xFF8901) == 3 and M.r8(0xFF8921) == 0x80 | info["rates"][1] and M.r8(SV + 1) == 2)
    chk("dma: voices audible at $b9a = 2", heard > 20 and any(M.rd(RING, RL)))
    M.w8(0xB9A, 0xF)
    M.call("asn_mtick")
    chk("att: $b9a = $f mutes every voice", not any(M.slot(c)["vol"] for c in range(4)) and M.r32(SV + 0xD0) == 41)
    for _ in range(14):
        M.call("asn_mtick")
    chk("att: the DMA stops after 12 silent VBL, the tune goes on", M.r8(0xFF8901) == 0 and M.r32(SV + 0xD0) == 55 and M.r8(SV + 0x12) == 1)
    M.w8(0xB9A, 2)
    for _ in range(30):
        M.call("asn_mtick")
    chk("att: back to 2: audible again", M.r8(0xFF8901) == 3)
    M.w8(SV + 0x13, 0xFF)
    n = M.r32(SV + 0xD0)
    M.call("asn_mtick")
    chk("lock: no tick while a start is in progress", M.r32(SV + 0xD0) == n)
    M.w8(SV + 0x13, 0)
    M.call("asn_mstart")                              # restart of the same tune
    chk("restart: tick counter 0, ring kept running", M.r32(SV + 0xD0) == 0 and M.r8(0xFF8901) == 3 and M.r8(SV + 1) == 2)
    # the sound effects take over, then the music again
    M.w16(0x6862, 0xFFFF)
    M.w16(0x686C, 0xFFFF)
    M.call("asn_tick")
    chk("sfx: session 1 at 6258 Hz, DMA stopped for the switch", M.r8(SV + 1) == 1 and M.r8(SV + 0x14) == 0 and M.r8(0xFF8901) == 0 and M.r16(SV + 0xC0) == 192)
    M.call("asn_mtick")
    chk("music again: session 2, the tune resumed", M.r8(SV + 1) == 2 and M.r16(SV + 0xC0) == PAR[info["rates"][1]]["target"])
    # a start of a missing tune / tune 0 while a DMA tune plays: DMA off, YM driver
    M.w32(0xB96, 0)
    M.call("asn_mstart")
    chk("tune 0: DMA tune off, YM driver's silent tune", M.r8(SV + 0x12) == 0 and M.r8(0xFF8901) == 0 and M.r32(0x124E) == ymtab(0))
    # once flag: tune 8 (832 ticks) ends -> $b96 = 0, the YM driver's tune 0
    if 8 in info["tunes"]:
        M.reset()
        M.w8(SV, 2)
        M.w32(0xB96, 8)
        M.call("asn_mstart")
        M.w16(0xBA2, 1)
        k = 0
        while M.r8(SV + 0x12) and k < 2000:
            M.dmapos((k * 250) % RL)
            M.call("asn_mtick")
            k += 1
        chk(f"once: tune 8 ended after {k} ticks (expected 833)", k == 833 and M.r32(0xB96) == 0 and M.r8(0xFF8901) == 0 and M.r32(0x124E) == ymtab(0))
        M.reset()
        M.w8(SV, 2)
        M.w32(0xB96, 8)
        M.call("asn_mstart")
        for k in range(900):
            M.dmapos((k * 250) % RL)
            M.call("asn_mtick")
        chk("loop: tune 8 without the once flag keeps playing", M.r8(SV + 0x12) == 8)
    print(f"iface : vector-table behaviour, 20 checks, failed: {bad or 'none'}")
    return len(bad)


def cmd_clip(a):
    t = asn_build.Tables(asn_build.read_mwii(asn_build.ADF))
    bank, info = asn_build.build_bank(t)
    worst = {}
    for tune in info["tunes"]:
        bm = AM.BlobModel(t.mem, bank, BANK, info, VT)
        bm.start(tune, info["rates"][tune], info["gains"][tune])
        acc, mx, over = 0.0, 0, 0
        spt = (12516.58 if info["rates"][tune] else 6258.29) / 50.053
        for _ in range(info["loops"][tune]):
            bm.tick()
            bm.vols(2)
            acc += spt
            n8 = int(acc) // 8
            acc -= n8 * 8
            tot = [0] * (n8 * 8)
            for s in bm.prep():
                ring = bytearray(RL)
                AM.mix(bank, BANK, ring, 0, n8, [s], True, bm.sil)
                for i in range(n8 * 8):
                    tot[i] += ring[i] - 256 if ring[i] > 127 else ring[i]
            bm.skip(n8 * 8)
            if tot:
                mx = max(mx, max(tot), -min(tot))
                over += sum(1 for x in tot if x > 127 or x < -128)
        worst[tune] = (mx, over)
        print(f"tune {tune:2d}: gain set {info['gains'][tune]} ({asn_build.GAINS[info['gains'][tune]]}), {info['loops'][tune]} ticks, largest |sum| {mx} of 127, overflowing samples {over}", flush=True)
    sys.exit(1 if any(o for _, o in worst.values()) else 0)


def cmd_unit(a):
    t = asn_build.Tables(asn_build.read_mwii(asn_build.ADF))
    bank, info = asn_build.build_bank(t)
    print("bank  :", asn_build.describe(bank, info))
    M = Machine(bank)
    assert M.syms["asn_tick"] > asn_build.CODE and info["fixenv"] == BANK + asn_build.OFF_MUS + 0x166 and info["idle"] == BANK + asn_build.OFF_MUS + 0x148
    assert info["silenv"] == BANK + asn_build.OFF_MUS + 0x150 and info["idle_list"] == BANK + asn_build.OFF_MUS + 0x144 and info["sil"] == BANK + 0x40
    tunes = a.tunes or info["tunes"]
    b0 = unit_spec(t, a.ticks)
    b1 = unit_player(M, t, bank, info, a.ticks, tunes)
    b2 = unit_mixer(M, t, bank, info)
    b3 = unit_iface(M, t, bank, info)
    print("RESULT:", "ALL OK" if not (b0 or b1 or b2 or b3) else f"FAILED (spec {b0}, player {b1}, mixer {b2}, iface {b3})" + ("  [ASN_NEG: a failure of `player` is the expected result]" if NEG else ""))
    sys.exit(1 if b0 or b1 or b2 or b3 else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("unit")
    u.add_argument("--ticks", type=int, default=1700)
    u.add_argument("--tunes", nargs="*", type=int)
    sub.add_parser("clip")
    a = ap.parse_args()
    {"unit": cmd_unit, "clip": cmd_clip}[a.cmd](a)


if __name__ == "__main__":
    main()
