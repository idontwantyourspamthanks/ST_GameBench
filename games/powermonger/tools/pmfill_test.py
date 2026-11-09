#!/usr/bin/env python3
"""Offline differential test of the terrain-raster patches (p6_tri, ...) against the original game code.

    python3 tools/pmfill_test.py [--patch p6_slope p6_tri ...] [--fuzz N] [--dump get_men map_idle battle_320] [--views 500] [--seed 1]

Needs `pip install unicorn` (QEMU 68000 core; no cycle counts: those come from Hatari, tools/pmab.py / pmprof2.py).
Each trial restores a RAM dump taken from a running game (work/dumps/*.bin, 1 MB), pokes a random camera (scroll $4bb3a/$4bb3c,
heading $ff9a, tilt $ff96/$ff98, scale $ff9c, zoom $57ffc + `jsr $fe04`, water phase $4bb3e) and runs the landscape/object renderer
`$f898` twice from the same state: original code, and with the patches' sites and blobs written over it.  After both runs the whole
1 MB must be identical (screen buffers, tables, stack below the frame excluded) - not just the picture.  Also reports every stream
fed to the filler (shape statistics) so that the assumptions in the patch headers can be seen to hold.
"""
from __future__ import annotations

import argparse
import random
import struct
import sys
from pathlib import Path

from unicorn import (UC_ARCH_M68K, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, Uc, UcError)
from unicorn.m68k_const import *  # noqa: F403

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))
import pmpatch  # noqa: E402

DUMPS = GAME / "work" / "dumps"
SP = 0x60000
RET = 0xFE0000


def load_patch(names):
    """[(addr, bytes)] writes for the patches' sites and blobs (the same bytes pmpatch puts into a build)."""
    writes = []
    for n in names:
        p = pmpatch.Patch(pmpatch.PATCHDIR / f"{n}.s")
        equ = "\n".join(p.preamble)
        for org, lines in p.segments:
            b = pmpatch.assemble(org, lines, equ)
            if org == p.site:
                orig = pmpatch.resident_bytes(p.stage, org, len(b))
                if p.orig is not None:
                    assert orig[:len(p.orig)] == p.orig, (n, orig.hex())
                if len(b) < len(p.orig or b""):
                    b += b"\x4e\x71" * ((len(p.orig) - len(b)) // 2)
            writes.append((org, b))
    return writes


class Emu:
    def __init__(self, ram: bytes):
        self.mu = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.mu.ctl_set_cpu_model(UC_CPU_M68K_M68000)
        self.mu.mem_map(0, 0x100000)
        self.mu.mem_write(0, ram[:0x100000])
        self.mu.mem_map(0xFF0000, 0x10000)
        self.mu.mem_map(0xFE0000, 0x1000)
        self.mu.mem_map(0xE00000, 0x40000)

    def rl(self, a): return struct.unpack(">I", self.mu.mem_read(a, 4))[0]
    def rw(self, a): return struct.unpack(">H", self.mu.mem_read(a, 2))[0]
    def ww(self, a, v): self.mu.mem_write(a, struct.pack(">H", v & 0xFFFF))
    def wl(self, a, v): self.mu.mem_write(a, struct.pack(">I", v & 0xFFFFFFFF))

    def call(self, addr, regs=None, sp=SP, maxn=0):
        self.wl(sp - 4, RET)
        self.mu.reg_write(UC_M68K_REG_A7, sp - 4)
        for k, v in (regs or {}).items():
            self.mu.reg_write(k, v & 0xFFFFFFFF)
        self.mu.emu_start(addr, RET, count=maxn)


def view_params(rng, ram):
    z = rng.choice([3, 4, 4, 5, 6])
    return dict(
        x=rng.randint(0, 30) if rng.random() < .8 else rng.randint(0, 63),
        y=rng.randint(z, 60),
        hd=16 * rng.randrange(16),
        tilt=0x82 + 10 * rng.randint(-4, 4),
        tilt2=0x140 + 10 * rng.randint(-4, 4),
        scale=0x15 + rng.randint(-3, 3),
        z=z,
        phase=rng.randrange(1 << 16),
    )


def run(ram, vp, writes, track=None):
    e = Emu(ram)
    for a, b in writes:
        e.mu.mem_write(a, b)
    e.ww(0x4BB3A, vp["x"]); e.ww(0x4BB3C, vp["y"]); e.ww(0xFF9A, vp["hd"])
    e.ww(0xFF96, vp["tilt"]); e.ww(0xFF98, vp["tilt2"]); e.ww(0xFF9C, vp["scale"]); e.ww(0x57FFC, vp["z"])
    e.wl(0x4BB3E, vp["phase"])
    e.call(0xFE04, {UC_M68K_REG_D1: vp["z"]})            # view tables for this zoom, as the zoom keys do
    back = e.rl(0x2DF7C)
    e.mu.mem_write(back, bytes(ram[0x78000:0x78000 + 32000]))
    e.wl(0xFFA2 + 0, e.rl(0xFFA2))
    if track is not None:
        def hs(mu, addr, size, ud):
            track["streams"].append((mu.reg_read(UC_M68K_REG_A0),))
        e.mu.hook_add(UC_HOOK_CODE, hs, begin=0xE3E6, end=0xE3E6)
        def hx(mu, addr, size, ud):
            track["scan"] += 1
        e.mu.hook_add(UC_HOOK_CODE, hx, begin=0xE456, end=0xE456)
    # word / long accesses at odd addresses would be address errors on a 68000
    odd = []
    def chk(mu, access, addr, size, value, ud):
        if size > 1 and addr & 1:
            odd.append((mu.reg_read(UC_M68K_REG_PC), addr, size))
    e.mu.hook_add(UC_HOOK_MEM_READ | UC_HOOK_MEM_WRITE, chk, begin=0, end=0xFFFFF)
    try:
        e.call(0xF898, maxn=50_000_000)
    except UcError as ex:
        return None, f"exception {ex} at pc ${e.mu.reg_read(UC_M68K_REG_PC):x}", odd
    return e, None, odd


def fuzz(a, writes):
    """Direct calls of the triangle setup `$ef62` with random vertices (d0-d2 = x<<16|y, d3 = colour) on a random screen: covers
    the divide fall-backs, flat tops, crossing edges (the abort), the clipper, every orientation.  Compares the whole RAM."""
    rng = random.Random(a.seed)
    ram = (DUMPS / "get_men.bin").read_bytes()
    bad = 0
    stats = {"calls": 0}
    for k in range(a.fuzz):
        def mk():
            m = rng.random()
            if m < 0.6:   # small triangle near a point
                cx, cy = rng.randint(0, 255), rng.randint(0, 199)
                return [((max(0, min(255, cx + rng.randint(-30, 30))) << 16) | max(0, min(199, cy + rng.randint(-25, 25)))) for _ in range(3)]
            if m < 0.8:   # anything in range
                return [((rng.randint(0, 255) << 16) | rng.randint(0, 199)) for _ in range(3)]
            if m < 0.9:   # shared y / x (flat tops, bottoms, verticals)
                y = rng.randint(0, 199); x = rng.randint(0, 255)
                v = [(rng.randint(0, 255) << 16) | y, (rng.randint(0, 255) << 16) | y, (x << 16) | rng.randint(0, 199)]
                rng.shuffle(v)
                return v
            return [((rng.randint(0, 258) << 16) | rng.randint(0, 203)) for _ in range(3)]   # partly outside: the clipper
        v = mk()
        col = rng.randint(0, 63)
        scr = bytes(rng.getrandbits(8) for _ in range(32000))
        F = (0x5C000 + 2 * rng.randrange(0, 128)) if k % 3 else None
        outs = []
        for wr in ([], writes):
            e = Emu(ram)
            for ad, b in wr:
                e.mu.mem_write(ad, b)
            back = e.rl(0x2DF7C)
            e.mu.mem_write(back, scr)
            if F is not None:
                e.wl(0xFFA2, F)
            regs = {UC_M68K_REG_D0: v[0], UC_M68K_REG_D1: v[1], UC_M68K_REG_D2: v[2], UC_M68K_REG_D3: col, UC_M68K_REG_A6: 0xECE2}
            try:
                e.call(0xEF62, regs, maxn=20_000_000)
                sp = e.mu.reg_read(UC_M68K_REG_A7); a6 = e.mu.reg_read(UC_M68K_REG_A6)
                err = None if (sp == SP and a6 == 0xECE2) else f"sp {sp:x} a6 {a6:x}"
            except UcError as ex:
                err = f"exception {ex}"
            m = bytearray(e.mu.mem_read(0, 0x100000)); m[SP - 0x400:SP] = bytes(0x400)
            outs.append((err, None, m))
        o0, o1 = outs
        stats["calls"] += 1
        if o0[0] and o0[0] == o1[0]:
            stats["both_fault"] = stats.get("both_fault", 0) + 1
            continue
        masked = [(ad, ad + len(b)) for ad, b in writes] + [(0xF1E2, 0xF1E2 + 48)]
        if o0[0] != o1[0]:
            bad += 1
            print(f"fuzz #{k} {[hex(x) for x in v]} colour {col}: orig {o0[0]} patched {o1[0]}")
        elif o0[2] != o1[2]:
            d = [i for i in range(0x100000) if o0[2][i] != o1[2][i] and not any(l <= i < h for l, h in masked)]
            if d:
                bad += 1
                if bad <= a.show:
                    print(f"fuzz #{k} {[hex(x) for x in v]} colour {col}: {len(d)} bytes differ, first ${d[0]:x}")
    print(f"fuzz: {stats['calls']} triangles ({stats.get('both_fault', 0)} where the original faults too), {bad} MISMATCH" if bad else
          f"fuzz: {stats['calls']} triangles ({stats.get('both_fault', 0)} where the original faults too): IDENTICAL (whole RAM)")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patch", nargs="*", default=["p6_slope", "p6_tri"])
    ap.add_argument("--dump", nargs="*", default=["get_men", "map_idle", "battle_320"])
    ap.add_argument("--views", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--show", type=int, default=5)
    ap.add_argument("--fuzz", type=int, default=0, help="direct random calls of the triangle setup (instead of views)")
    ap.add_argument("--mask", nargs="*", default=["f1e2:30"], help="ADDR:LEN ranges that may differ (scratch: the setup's record buffer, which p6_tri no longer writes)")
    a = ap.parse_args()
    writes = load_patch(a.patch)
    if a.fuzz:
        sys.exit(1 if fuzz(a, writes) else 0)
    rng = random.Random(a.seed)
    bad = 0
    total = 0
    scans = 0
    clip = 0
    skipped = 0
    for dn in a.dump:
        ram = (DUMPS / f"{dn}.bin").read_bytes()
        for i in range(a.views):
            vp = view_params(rng, ram)
            tr = dict(streams=[], scan=0)
            e0, err0, odd0 = run(ram, vp, [], tr)
            e1, err1, odd1 = run(ram, vp, writes)
            total += 1
            scans += tr["scan"]
            clip += sum(1 for s in tr["streams"] if s[0] != 0xF1E2)
            if err0 or err1:
                if err0 == err1:                    # the original itself faults here (divide by zero in the clipper for this made-up view): not comparable
                    skipped += 1
                    continue
                bad += 1
                if bad <= a.show:
                    print(f"{dn} #{i} {vp}: orig {err0} patched {err1}")
                continue
            m0 = bytearray(e0.mu.mem_read(0, 0x100000)); m0[SP - 0x400:SP] = bytes(0x400)   # the stack below the frame is scratch
            m1 = bytearray(e1.mu.mem_read(0, 0x100000)); m1[SP - 0x400:SP] = bytes(0x400)
            # the patched blob area is the only legitimate difference
            masked = [(ad, ad + len(b)) for ad, b in writes] + [(int(m.split(':')[0], 16), int(m.split(':')[0], 16) + int(m.split(':')[1])) for m in a.mask]
            d = [k for k in range(0, len(m0)) if m0[k] != m1[k] and not any(l <= k < h for l, h in masked)] if m0 != m1 else []  # noqa
            if odd1:
                bad += 1
                print(f"{dn} #{i} {vp}: odd-address access in patched run {[(hex(p), hex(x), s) for p, x, s in odd1[:4]]}")
            if d:
                bad += 1
                if bad <= a.show:
                    print(f"{dn} #{i} {vp}: {len(d)} bytes differ, first at ${d[0]:x} (orig {m0[d[0]]:02x} patched {m1[d[0]]:02x})")
    print(f"{total} views ({skipped} skipped: the original faults too), {scans} scanlines (original), {clip} non-setup streams, {bad} MISMATCH" if bad else
          f"{total} views ({skipped} skipped: the original faults too), {scans} scanlines (original), {clip} non-setup streams: IDENTICAL (whole RAM)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
