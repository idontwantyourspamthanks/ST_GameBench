#!/usr/bin/env python3
"""Port master's Powermonger address list (patches/*.s of games/done/powermonger) to the WW1 EA image.

Both games are one engine with a piecewise-constant address shift.  Method (everything reproducible from the two resident images):
  1. anchors: 12-byte windows that occur exactly once in each image give the set of candidate shifts (WW1 addr - master addr);
  2. for every master address X (a patch site, or the place where the code uses a variable) the shift whose 64-byte window around X
     matches best is chosen; the score (matching bytes of 64) is reported, a low score is a flag, not a result;
  3. a variable is mapped through the code that uses it: every occurrence of its 4-byte absolute operand in master's code is mapped to WW1
     and the operand found there is the vote.
The output is a CANDIDATE table.  work/notes/addrmap.md lists which entries were then confirmed by disassembly of both sides or by a
Hatari observation.

    python3 tools/addrmap.py sites|vars|check|shifts [--master-dump PATH]
"""
from __future__ import annotations
import argparse
import collections
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))
import wwdepack  # noqa: E402

MASTER = GAME.parent.parent / "done" / "powermonger"
M_DUMP = MASTER / "work" / "dumps" / "entry10a6.bin"      # master: RAM at its game hand-over ($10a6 = start of the game proper)
M_BASE = 0x10A6
W_BASE = wwdepack.BASE
K = 12


class Images:
    def __init__(self, mdump: Path = M_DUMP):
        raw = mdump.read_bytes()
        end = max(i for i in range(len(raw) - 1, M_BASE, -1) if raw[i]) + 1
        self.m = raw[M_BASE:end]
        self.w = wwdepack.resident_image((GAME / "extracted/ea/AUTO/WW1.PRG").read_bytes())
        self.shifts = self._shifts()

    def _shifts(self):
        def grams(b):
            d = collections.defaultdict(list)
            for i in range(len(b) - K + 1):
                d[b[i:i + K]].append(i)
            return d
        gm, gw = grams(self.m), grams(self.w)
        sh = collections.Counter()
        for g, l in gm.items():
            if len(l) == 1 and len(gw.get(g, ())) == 1 and len(set(g)) > 3:
                sh[(gw[g][0] + W_BASE) - (l[0] + M_BASE)] += 1
        return sh

    def mb(self, a: int, n: int) -> bytes:
        return self.m[a - M_BASE:a - M_BASE + n]

    def wb(self, a: int, n: int) -> bytes:
        return self.w[a - W_BASE:a - W_BASE + n]

    def best(self, x: int, half: int = 32):
        """(shift, score of 2*half) of the best-matching diagonal around master address x."""
        lo = x - half
        ref = self.mb(lo, 2 * half)
        bestv = (None, -1)
        for s, _ in self.shifts.items():
            w = self.wb(lo + s, 2 * half)
            if len(w) != len(ref):
                continue
            sc = sum(1 for a, b in zip(ref, w) if a == b)
            if sc > bestv[1]:
                bestv = (s, sc)
        return bestv


def master_sites():
    out = []
    for f in sorted((MASTER / "patches").glob("*.s")):
        name = site = orig = None
        stage = 2
        default = True
        for line in f.read_text().splitlines():
            m = re.match(r"^;\s*([a-z]+):\s*(.*)$", line)
            if not m:
                if line.strip() and not line.startswith(";"):
                    break
                continue
            k, v = m.group(1), m.group(2).strip()
            if k == "name":
                name = v
            elif k == "site":
                site = int(v.lstrip("$"), 16)
            elif k == "orig":
                orig = bytes.fromhex(v.replace(" ", ""))
            elif k == "stage":
                stage = int(v)
            elif k == "default":
                default = v.lower() not in ("no", "false", "0")
        if site is not None and orig is not None and stage == 2 and not f.name.startswith(("hd_", "test_")):
            out.append((name, site, orig, default))
    return out


def cmd_shifts(im):
    for s, c in im.shifts.most_common(40):
        print(f"{'+' if s >= 0 else '-'}{abs(s):#06x}  {c}")


def cmd_sites(im):
    print(f"{'patch':16s} {'master':>8s} {'ww1':>8s} {'shift':>7s} {'score/64':>8s}  orig(master) | ww1 bytes")
    for name, site, orig, default in master_sites():
        s, sc = im.best(site)
        wa = site + s
        wb = im.wb(wa, len(orig))
        same = "same" if wb == orig else "diff"
        print(f"{name:16s} {site:8x} {wa:8x} {s:+7x} {sc:8d}  {orig.hex()} | {wb.hex()} {same}{'' if default else ' (non-default)'}")


def code_refs(im, addr: int):
    pat = struct.pack(">I", addr)
    out, p = [], 0
    while (i := im.m.find(pat, p)) >= 0:
        out.append(i + M_BASE)
        p = i + 1
    return out


def master_constants():
    """Absolute addresses < $80000 that master's patch sources use as operands (comments stripped)."""
    c = collections.Counter()
    for f in (MASTER / "patches").glob("*.s"):
        if f.name.startswith(("hd_", "test_")):
            continue
        for line in f.read_text().splitlines():
            line = re.sub(r";.*", "", line)
            if re.match(r"^\s*\w+\s+equ\s", line):
                continue
            for m in re.finditer(r"\$([0-9a-f]{4,6})\b", line, re.I):
                v = int(m.group(1), 16)
                if 0x1000 <= v < 0x80000:
                    c[v] += 1
    return c


def cmd_vars(im, only=None):
    consts = [a for a in master_constants() if (only is None or a in only)]
    print(f"{'master':>8s} {'ww1':>8s} {'votes':>9s}  detail")
    for a in sorted(consts):
        refs = [r for r in code_refs(im, a) if r < 0x1BA00]
        votes = collections.Counter()
        for r in refs:
            s, sc = im.best(r + 0)
            if sc < 40:
                continue
            w = im.wb(r + s, 4)
            if len(w) == 4:
                votes[struct.unpack(">I", w)[0]] += 1
        if votes:
            top = votes.most_common(3)
            print(f"{a:8x} {top[0][0]:8x} {top[0][1]:4d}/{len(refs):<4d}  " + " ".join(f"{v:x}x{n}" for v, n in top))
        else:
            print(f"{a:8x} {'?':>8s} {0:4d}/{len(refs):<4d}  (no usable code reference)")


ROUTINES = {   # master address -> what it is (master notes: retire.md, protection.md, loading.md, tooltip.md ...)
    0x110e: "RAM probe bus-error handler", 0x1118: "probe write at $80000 (sets the resource-cache cursor)", 0x1132: "probe compare",
    0x1286: "VBL handler", 0x1870: "wait for flip", 0x187a: "flip (swap screen buffers, write $ff8201..)",
    0x7774: "demo check (protection flag)", 0xaf10: "demo check (protection flag)", 0x8838: "window/text composer", 0x8976: "font data",
    0xb2d4: "protection: decoy land + question", 0xb842: "answer compare", 0xb856: "correct-answer write (flag $2c)",
    0xb9ac: "wrong answer -> demo mode box", 0xd2c8: "Retire dispatch", 0xdf52: "resource loader", 0xe000: "cache cursor load (pm_cachecap site)",
    0xe040: "resource address table", 0xe084: "resource size table", 0x11bf4: "person-state handler (starts the protection check)",
    0x12e6a: "tooltip line table 1", 0x12ee4: "tooltip line table 2", 0x13250: "rotate/zoom rect table",
    0x1a4da: "win picture (resource 15)", 0x1a5b2: "lose picture (resource 14)",
}


def _mn(im, side, a, n):
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    b = im.mb(a, 64) if side == "m" else im.wb(a, 64)
    return [(i.mnemonic, f"{i.mnemonic} {i.op_str}") for i in md.disasm(b, a)][:n]


def cmd_check(im):
    """Spot-check by instructions: the first 8 instructions at each mapped site / routine must show the same mnemonic sequence."""
    print(f"{'what':18s} {'master':>7s} {'ww1':>7s} {'shift':>7s} {'bytes':>5s} {'insn':>5s}  master -> ww1 (first 3 instructions)")
    items = [(n, a, f"{n}") for n, a, o, d in master_sites()] + [(f"{a:x}", a, t) for a, t in ROUTINES.items()]
    for name, a, _ in items:
        s, sc = im.best(a)
        m, w = _mn(im, "m", a, 8), _mn(im, "w", a + s, 8)
        same = sum(1 for x, y in zip(m, w) if x[0] == y[0])
        print(f"{name:18s} {a:7x} {a + s:7x} {s:+7x} {sc:5d} {same}/{min(len(m), len(w))}  "
              + " ; ".join(x[1] for x in m[:3]) + "  ->  " + " ; ".join(x[1] for x in w[:3]))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["shifts", "sites", "vars", "check"])
    ap.add_argument("--master-dump", default=str(M_DUMP))
    a = ap.parse_args()
    im = Images(Path(a.master_dump))
    {"shifts": cmd_shifts, "sites": cmd_sites, "vars": cmd_vars, "check": cmd_check}[a.cmd](im)


if __name__ == "__main__":
    main()
