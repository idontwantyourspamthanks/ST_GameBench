#!/usr/bin/env python3
"""Static list of the code that stores into map_blk ($36eb6) and map_bk2 ($3c560).

    python3 writers.py [DUMP]            # default work/dumps/busy.bin

1. Every 32-bit constant in the code ($af40-$21100) that points into a map or 144 bytes round it
   (only the two base addresses may appear for step 2 to be complete).
2. Every instruction that loads a base address: the register is followed over the next instructions
   (pointer arithmetic `add.l a0,d0` / `movea.l d0,a0` included) to its first use, classified as
   WRITE (memory destination of a non-compare instruction), READ, ARG (pea) or ? (to read by hand).
"""
from __future__ import annotations

import bisect
import re
import struct
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent.parent
sys.path.insert(0, str(GAME.parent.parent.parent / "tools"))
import capstone  # noqa: E402
import m68dis  # noqa: E402

LO, HI = 0xAF40, 0x21100
MAPS = {"map_blk": 0x36EB6, "map_bk2": 0x3C560}
RO = ("cmp", "cmpi", "tst", "btst", "cmpa", "cmpm")
md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)


def split_ops(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        depth += ch in "([" 
        depth -= ch in ")]"
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def one(ram: bytes, a: int):
    return next(md.disasm(ram[a:a + 10], a), None)


def classify(ram: bytes, base: int, targets: list[int]):
    pat = struct.pack(">I", base)
    a = LO
    while True:
        i = ram.find(pat, a, HI)
        if i < 0:
            return
        a = i + 2
        s = i - 2
        ins = one(ram, s)
        if not ins or f"${base:x}" not in ins.op_str:
            yield (s, 0, "?not-an-operand", "", 0, "")
            continue
        fn = targets[bisect.bisect_right(targets, s) - 1]
        ops0 = split_ops(ins.op_str)
        kind, where, text = "?", 0, ""
        if ins.mnemonic.startswith("pea"):
            kind = "ARG"
        elif re.fullmatch(r"a\d", ops0[-1]):
            regs = {ops0[-1]}
            p = s + ins.size
            for _ in range(10):
                n = one(ram, p)
                if not n:
                    break
                mn = n.mnemonic.split(".")[0]
                ops = split_ops(n.op_str)
                hit = [k for k, o in enumerate(ops) if any(re.search(rf"\b{r}\b", o) for r in regs)]
                if hit:
                    dst = ops[-1]
                    if mn in ("add", "adda", "movea", "move") and len(ops) == 2 and ops[0] in regs \
                            and re.fullmatch(r"[da]\d", dst):
                        regs.add(dst)                       # the pointer moves to another register
                        p += n.size
                        continue
                    if mn in ("adda", "add", "ext") and dst in regs:
                        p += n.size
                        continue
                    where, text = p, f"{n.mnemonic} {n.op_str}"
                    k = hit[-1]
                    if "(" not in ops[k]:
                        kind = "?pointer kept"
                    elif k == len(ops) - 1 and mn not in RO and mn not in ("lea", "pea") and \
                            (len(ops) == 2 or mn in ("clr", "st", "sf", "not", "neg", "addq", "subq", "tas")):
                        kind = "WRITE"
                    elif mn in ("lea", "pea"):
                        kind = "?pointer kept"
                    else:
                        kind = "READ"
                    break
                if mn in ("jsr", "rts", "bra", "jmp", "bsr"):
                    kind = "?flow"
                    break
                p += n.size
        yield (s, fn, kind, f"{ins.mnemonic} {ins.op_str}", where, text)


def main() -> int:
    ram = Path(sys.argv[1] if len(sys.argv) > 1 else GAME / "work" / "dumps" / "busy.bin").read_bytes()
    targets = m68dis.call_targets(ram)
    for name, base in MAPS.items():
        c = Counter(struct.unpack_from(">I", ram, a)[0] for a in range(LO, HI, 2)
                    if base - 0x90 <= struct.unpack_from(">I", ram, a)[0] < base + 0x1000 + 0x90)
        inside = {k: v for k, v in c.items() if base <= k < base + 0x1000}
        print(f"{name}: constants pointing into the map: " + ", ".join(f"${k:x} x {v}" for k, v in sorted(inside.items())))
        rows = list(classify(ram, base, targets))
        print(f"{name}: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(r[2] for r in rows).items())))
        for s, fn, kind, txt, where, text in rows:
            if kind != "READ":
                print(f"  {kind:14} routine ${fn:x}: {s:06x} {txt}" + (f"  ->  {where:06x} {text}" if where else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
