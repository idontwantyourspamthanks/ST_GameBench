#!/usr/bin/env python3
"""Offline lock-step test of the VBL pointer patches (p4_ptr_a / p4_ptr_b) against the original pointer code, in the 68000 emulator (unicorn).

    python3 tools/wwptr_test.py [--dump ste_get_men ste_map_idle ste_random] [--trials 200] [--steps 80] [--seed 1] [--patch p4_ptr_a p4_ptr_b]

WW1_PATCHDIR as for wwpatch.py (a mutant patch directory).  Two emulated machines start from the SAME 1 MB RAM dump of the running game (tools/wwdumps.py); one has the patch sites and blobs written
over it.  Each step applies the SAME random event to both and runs the VBL pointer block ($874: the hide test, restore of the saved lines, new position, save + draw, ACIA wait) up to $9c0 in both, then
compares the whole 1 MB (the patch's own blob / data area excluded).  Events: nothing (the skip case), the pointer moves (any position incl. x > 304 = one column and y > 184 = clipped), the buffers flip
([$2ed98] <-> [$2ed9c]), random bytes written into the displayed buffer under the pointer or elsewhere (what the icon / tooltip blits do), the animation frame word [$2cfde] set to 0 / $320 / animated
values, the VBL counter advances, the pointer is hidden ([$1d4d2] / [$1d2ba] = 0), a changed pointer row count / stride record.  This is what the Hatari A/B scenes only sample.
Exit status 0 = every step of every trial identical; also prints how many steps took the skip path (hits of the two `jmp $9b8` of part A).
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

from unicorn import UcError
from unicorn.m68k_const import UC_M68K_REG_A7

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wwfill_test as F  # noqa: E402
import wwpatch  # noqa: E402

START, END = 0x874, 0x9C0
FRAMES = [0, 0x320, 0xA0, 0x140, 0x1E0, 0x280]


def apply(emu, writes):
    for a, b in writes:
        emu.mu.mem_write(a, b)


def run_block(emu):
    emu.mu.mem_write(0xFFFFFC00, b"\x02")                    # ACIA status: transmit ready
    emu.mu.reg_write(UC_M68K_REG_A7, 0xC0000)
    emu.mu.emu_start(START, END, count=2_000_000)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", nargs="*", default=["ste_get_men", "ste_map_idle", "ste_random"])
    ap.add_argument("--trials", type=int, default=100)
    ap.add_argument("--steps", type=int, default=80)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--patch", nargs="*", default=["p4_ptr_a", "p4_ptr_b"])
    a = ap.parse_args()
    writes = F.load_patch(a.patch)
    allp = {p.name: p for p in wwpatch.load_all()}
    skip_pcs = set()
    for n in a.patch:
        p = allp[n]
        for org, lines in p.segments:
            if org != p.site:
                blob = wwpatch.assemble(org, lines, "\n".join(p.preamble))
                k = 0
                while (k := blob.find(bytes.fromhex("4ef9000009b8"), k)) >= 0:
                    skip_pcs.add(org + k)
                    k += 2
    masked = sorted({(ad, ad + len(b)) for ad, b in writes} | {(0x75C00, 0x76400)})
    rng = random.Random(a.seed)
    bad = steps = skips = 0
    kinds = {}
    for dn in a.dump:
        ram = (F.DUMPS / f"{dn}.bin").read_bytes()
        for t in range(a.trials):
            e0, e1 = F.Emu(ram), F.Emu(ram)
            for e in (e0, e1):
                e.mu.mem_map(0xFFFF0000, 0x10000)               # $fc00.w sign-extends to $fffffc00
            apply(e1, writes)
            hits = [0]

            def hk(mu, addr, size, ud):
                hits[0] += 1
            for pc in skip_pcs:
                e1.mu.hook_add(__import__("unicorn").UC_HOOK_CODE, hk, begin=pc, end=pc)
            bufs = [e0.rl(0x2ED98), e0.rl(0x2ED9C)]
            for s in range(a.steps):
                r = rng.random()
                ev = []
                if r < 0.35:
                    kind = "nothing"
                elif r < 0.50:
                    kind = "move"
                    x, y = (rng.choice([0, 1, 15, 16, 160, 303, 304, 305, 311, 319]) if rng.random() < .5 else rng.randint(0, 319)), \
                           (rng.choice([0, 1, 183, 184, 185, 190, 199]) if rng.random() < .5 else rng.randint(0, 199))
                    ev = [("w", 0x2EDB2, x), ("w", 0x2EDB4, y)]
                elif r < 0.60:
                    kind = "flip"
                    c0, c1 = e0.rl(0x2ED98), e0.rl(0x2ED9C)
                    ev = [("l", 0x2ED98, c1), ("l", 0x2ED9C, c0)]
                elif r < 0.75:
                    kind = "poke screen"
                    base = e0.rl(0x2ED98)
                    p = e0.rl(0x1D2BA)
                    where = (p + rng.randrange(0, 16) * 160 + rng.randrange(0, 16)) if (p and rng.random() < .7) else base + rng.randrange(0, 32000 - 8)
                    ev = [("b", where, bytes(rng.getrandbits(8) for _ in range(rng.choice([1, 2, 4, 8]))))]
                elif r < 0.82:
                    kind = "frame word"
                    ev = [("w", 0x2CFDE, rng.choice(FRAMES))]
                elif r < 0.88:
                    kind = "vbl counter"
                    ev = [("l", 0x71B7C, e0.rl(0x71B7C) + rng.choice([1, 1, 2, 7, 8]))]
                elif r < 0.93:
                    kind = "hide"
                    ev = [("w", 0x1D4D2, rng.choice([0, 1]))]
                elif r < 0.96:
                    kind = "pointer record cleared"
                    ev = [("l", 0x1D2BA, 0)]
                else:
                    kind = "buffer pointer elsewhere"
                    ev = [("l", 0x2ED98, rng.choice(bufs))]
                kinds[kind] = kinds.get(kind, 0) + 1
                for e in (e0, e1):
                    for k, ad, v in ev:
                        if k == "w":
                            e.ww(ad, v)
                        elif k == "l":
                            e.wl(ad, v)
                        else:
                            e.mu.mem_write(ad, v)
                h0 = hits[0]
                try:
                    run_block(e0)
                    run_block(e1)
                except UcError as ex:
                    print(f"{dn} trial {t} step {s} ({kind}): emulator fault {ex}")
                    bad += 1
                    break
                steps += 1
                skips += hits[0] - h0
                m0, m1 = e0.mu.mem_read(0, 0x100000), e1.mu.mem_read(0, 0x100000)
                if m0 != m1:
                    d = [i for i in range(0x100000) if m0[i] != m1[i] and not any(l <= i < h for l, h in masked)]
                    if d:
                        bad += 1
                        print(f"{dn} trial {t} step {s} ({kind}): {len(d)} bytes differ, first ${d[0]:x} (orig {m0[d[0]]:02x} patched {m1[d[0]]:02x})")
                        break
    print(f"PTRTEST {steps} steps in {len(a.dump) * a.trials} trials over {len(a.dump)} dumps, events {kinds}; skip path taken in {skips} steps; "
          + (f"{bad} MISMATCH" if bad else "IDENTICAL (whole 1 MB after every step)"))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
