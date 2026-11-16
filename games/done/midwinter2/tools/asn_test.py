#!/usr/bin/env python3
"""Tests for the sound-effect part of patches/asn/blob.s (the music part: tools/asn_mus_test.py).

  unit   : the blob's routines run in the Unicorn 68000 emulator against the Python reference model (tools/asn_model.py):
           the Amiga driver port (voice state per tick for every sound id, retriggers, sustained re-request, levels) and the mixer
           (ring bytes per call, bit exact against the integer model of the 16.16 stepping, volume tables and loop ends: asn_music.mix,
           run by asn_mus_test.unit_mixer in sound-effect and in music mode).
           A third check runs the ORIGINAL Amiga driver (`$2f3b2` of MWII, from the Amiga project's flat dump) and compares AUDxPER / AUDxVOL / AUDxLC /
           AUDxLEN with the blob's voices after every tick (ASN_NEG=1 = negative control).

    python3 tools/asn_test.py unit [--ticks 400]
"""
from __future__ import annotations

import os
import random
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import asn_build
import asn_model

from unicorn import Uc, UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UcError, UC_HOOK_CODE
from unicorn import m68k_const as mc

SV = 0xBBE00
BANK = asn_build.BANK
V0, VS = 0x40, 0x20


def assemble_core():
    """patches/asn/blob.s -> (org, bytes, symbols) via vasm with a listing."""
    with tempfile.TemporaryDirectory() as td:
        lst = Path(td) / "a.lst"
        code = asn_build.assemble_blob(lst)
        syms = {}
        for m in re.finditer(r"^(\w[\w.$]*)\s+A:([0-9A-F]+)\s*$", lst.read_text(), re.M):
            syms[m.group(1)] = int(m.group(2), 16)
    return asn_build.CODE, code, syms


class Machine:
    def __init__(self):
        self.org, self.code, self.syms = assemble_core()
        self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.uc.ctl_set_cpu_model(mc.UC_CPU_M68K_M68000)
        u = self.uc
        u.mem_map(0, 0x200000)                # 2 MB: everything the blob touches (game vars $6862.., SV, bank, code)
        u.mem_map(0xFF8000, 0x8000)
        u.mem_map(0xFFFF8000, 0x8000)
        u.mem_write(self.org, self.code)
        bank, self.info = asn_build.build_bank(asn_build.Tables(asn_build.read_mwii(asn_build.ADF)))
        u.mem_write(BANK, bank)
        self.bank = bank
        self.stop = 0x1FF000
        u.mem_write(self.stop, b"\x4e\x71")
        self.count = 0
        u.hook_add(UC_HOOK_CODE, self._h)

    def _h(self, uc, addr, size, ud):
        self.count += 1

    def call(self, label, **regs):
        u = self.uc
        sp = 0x1F0000
        u.reg_write(mc.UC_M68K_REG_A7, sp - 4)
        u.mem_write(sp - 4, struct.pack(">I", self.stop))
        for k, v in regs.items():
            u.reg_write(getattr(mc, "UC_M68K_REG_" + k.upper()), v)
        self.count = 0
        try:
            u.emu_start(self.syms[label] if isinstance(label, str) else label, self.stop, timeout=0, count=2_000_000)
        except UcError as e:
            pc = u.reg_read(mc.UC_M68K_REG_PC)
            print("UcError", e, "pc", hex(pc), {r: hex(u.reg_read(getattr(mc, 'UC_M68K_REG_' + r))) for r in ('A0', 'A2', 'A3', 'A4', 'A6', 'D0', 'D1', 'D4')})
            raise
        return self.count

    def r16(self, a):
        return struct.unpack(">H", bytes(self.uc.mem_read(a, 2)))[0]

    def w16(self, a, v):
        self.uc.mem_write(a, struct.pack(">H", v & 0xFFFF))

    def r32(self, a):
        return struct.unpack(">I", bytes(self.uc.mem_read(a, 4)))[0]

    def voice(self, c):
        a = SV + V0 + c * VS
        f = struct.unpack(">8H", bytes(self.uc.mem_read(a, 16)))
        smp, ln = struct.unpack(">IH", bytes(self.uc.mem_read(a + 0x10, 6)))
        return dict(vol=s16(f[0]), vsl=s16(f[1]), per=s16(f[2]), psl=s16(f[3]), cnt=s16(f[4]), rec=s16(f[5]), seq=s16(f[6]),
                    grp=s16(f[7]), smp=smp, ln=ln)


def s16(x):
    return x - 0x10000 if x & 0x8000 else x


def model_voice(v):
    return dict(vol=v.vol, vsl=v.vsl, per=v.per, psl=v.psl, cnt=v.cnt, rec=v.rec, seq=v.seq, grp=v.grp)


def unit_driver(m: Machine, t: asn_build.Tables, ticks: int):
    bad = 0
    rng = random.Random(1)
    # sound-id request word = id * 6 ($6862); sustained request $686c
    for sid in range(41):
        for lvl in (2, 5, 9):
            d = asn_model.Driver(t)
            d.level = lvl
            # reset the blob state
            m.uc.mem_write(SV, bytes(256))
            for c in range(4):
                m.w16(SV + V0 + c * VS + 0xE, 0xFFFF)
            m.w16(0x6862, 0xFFFF)
            m.w16(0x686C, 0xFFFF)
            script = {0: sid}
            if sid % 3 == 0:
                script[rng.randrange(20, 100)] = rng.randrange(41)       # a second sound on top
            sustained = rng.random() < 0.3
            for k in range(ticks):
                trig = script.get(k)
                m.w16(0x6862, 0xFFFF if trig is None else trig * 6)
                if sustained and k == 3:
                    m.w16(0x686C, ((sid + 5) % 41) * 6)
                    d.last = (sid + 5) % 41
                d.tick(trig)
                m.call("asn_drv", a4=SV, d5=lvl)
                for c in range(4):
                    a, b = model_voice(d.v[c]), {k2: v for k2, v in m.voice(c).items() if k2 in model_voice(d.v[c])}
                    if a != b:
                        bad += 1
                        if bad < 6:
                            print(f"DRIVER MISMATCH sound {sid} lvl {lvl} tick {k} voice {c}\n  model {a}\n  blob  {b}")
                        break
                else:
                    continue
                break
    return bad


AMI_FLAT = Path("/home/ryan/Code/Amiga/gamebench/games/in_progress/Midwinter-2/work/dumps/mwii_flat.bin")
AMI_B = 0x270D0                 # runtime address = flat offset + AMI_B (operands of the flat disassembly carry it)
AMI_TICK = 0x2F3B2 + AMI_B
AMI_TRIG, AMI_LAST, AMI_LEVEL = 0x56820, 0x5732C, 0x5676A
AMI_LCBASE = 0x89478


def unit_amiga(m: Machine, t: asn_build.Tables, ticks: int):
    """Run the ORIGINAL Amiga driver ($2f3b2 of the load file, from work/dumps/mwii_flat.bin of the Amiga project) in Unicorn and compare
    what it writes to Paula (period, volume byte, sample pointer, length) after every tick with the blob's voices."""
    if not AMI_FLAT.exists():
        print("amiga: flat dump not found, skipped")
        return 0
    flat = AMI_FLAT.read_bytes()
    a = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
    a.ctl_set_cpu_model(mc.UC_CPU_M68K_M68000)
    a.mem_map(0, 0x200000)
    a.mem_map(0xDFF000, 0x1000)
    a.mem_write(AMI_B, flat)
    stop = 0x1FF000
    a.mem_write(stop, b"\x4e\x71")
    bad = 0
    rng = random.Random(3)
    for sid in range(41):
        for lvl in (2, 6, 9):
            # fresh Amiga state: wipe the driver variables ($5676c..$5732b region is data we must keep: records, sequences, rows) -> only the channel
            # records and request words are reset
            a.mem_write(0x5676C, bytes(0x5682C - 0x5676C - 0))        # voices ($16 x 4 = $58 .. up to $56824)
            a.mem_write(0x56820, struct.pack(">hh", -1, -1))
            a.mem_write(0x56828, bytes(5))
            a.mem_write(AMI_LAST, struct.pack(">h", -1))
            a.mem_write(AMI_LEVEL, struct.pack(">H", lvl))
            for c in range(4):
                a.mem_write(0x5676C + 0x16 * c + 0xE, struct.pack(">h", -1))
            # the blob side
            m.uc.mem_write(SV, bytes(256))
            for c in range(4):
                m.w16(SV + V0 + c * VS + 0xE, 0xFFFF)
            m.w16(0x6862, 0xFFFF)
            m.w16(0x686C, 0xFFFF)
            script = {0: sid}
            if sid % 4 == 1:
                script[rng.randrange(10, 80)] = rng.randrange(1, 41)
            sust = (sid % 5 == 2)
            for k in range(ticks):
                trig = script.get(k)
                a.mem_write(AMI_TRIG, struct.pack(">h", -1 if trig is None else trig * 8))
                m.w16(0x6862, 0xFFFF if trig is None else trig * 6)
                if sust and k == 2:
                    a.mem_write(AMI_LAST, struct.pack(">h", (sid + 7) % 41 * 8))
                    m.w16(0x686C, (sid + 7) % 41 * 6)
                a.reg_write(mc.UC_M68K_REG_A7, 0x1F0000)
                a.mem_write(0x1F0000, struct.pack(">I", stop))
                a.emu_start(AMI_TICK, stop, timeout=0, count=3_000_000)
                m.call("asn_drv", a4=SV, d5=lvl + (1 if os.environ.get("ASN_NEG") else 0))      # ASN_NEG=1: negative control (wrong level)
                for c in range(4):
                    base = 0xDFF0A0 + 0x10 * c
                    per = struct.unpack(">H", bytes(a.mem_read(base + 6, 2)))[0]
                    vol = bytes(a.mem_read(base + 9, 1))[0]
                    lc, ln = struct.unpack(">IH", bytes(a.mem_read(base, 4)) + bytes(a.mem_read(base + 4, 2)))
                    v = m.voice(c)
                    if v["cnt"] == 0 and (v["vol"] >> 8) & 0xFF == 0 and vol == 0:
                        continue                                           # idle on both sides
                    bvol = (v["vol"] >> 8) & 0xFF
                    smp_off = lc - AMI_LCBASE
                    ok = per == (v["per"] & 0xFFFF) and vol == bvol
                    if v["cnt"] != 0:
                        # sample / length of the active step: map the pool offset to the bank address of that region
                        reg = [(so, ln_) for so, ln_ in t.regions if so == smp_off]
                        ok = ok and bool(reg) and ln == v["ln"]
                    if not ok:
                        bad += 1
                        if bad < 6:
                            print(f"AMIGA MISMATCH sound {sid} lvl {lvl} tick {k} ch {c}: amiga per {per} vol {vol} lc_off {smp_off:#x} len {ln}; "
                                  f"blob per {v['per']} vol {bvol} len {v['ln']} cnt {v['cnt']} vol16 {v['vol']:#x}")
                        break
                else:
                    continue
                break
    return bad


def cmd_unit(a):
    t = asn_build.Tables(asn_build.read_mwii(asn_build.ADF))
    m = Machine()
    print("symbols:", {k: hex(v) for k, v in m.syms.items() if k.startswith(("asn_", "mix"))})
    b1 = unit_driver(m, t, a.ticks)
    print(f"driver: {41 * 3} sound/level runs x {a.ticks} ticks, mismatches {b1}")
    import asn_mus_test
    b2 = asn_mus_test.unit_mixer(asn_mus_test.Machine(m.bank), t, m.bank, m.info)
    print(f"mixer : see the line above, mismatches {b2}")
    b3 = unit_amiga(m, t, a.ticks)
    print(f"amiga : the original Amiga driver vs the blob, 41 sounds x 3 levels x {a.ticks} ticks, mismatches {b3}")
    sys.exit(1 if b1 or b2 or b3 else 0)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("unit")
    u.add_argument("--ticks", type=int, default=400)
    a = ap.parse_args()
    if a.cmd == "unit":
        cmd_unit(a)


if __name__ == "__main__":
    main()
