#!/usr/bin/env python3
"""Parse Hatari `profile save` files (per-address instruction counts + cycles) and build a call-tree cost model.

    from pmprof import Prof
    p = Prof('work/prof/idle_8mhz.txt', 'work/dumps/idle.bin')
    p.frames            # VBL handler executions in the window
    p.table(top=15)     # exclusive cycles per function, calls, cycles/call
    p.incl(0x13040)     # inclusive cycles of one function (average per call x call-site counts)

Function boundaries are the jsr/bsr targets found in the code range of the RAM dump (as tools/m68dis.py does).
"""
from __future__ import annotations

import bisect
import re
import struct
import sys
from pathlib import Path

LINE = re.compile(r"\$([0-9A-Fa-f]+)\s+(.*?)\s+[\d.]+% \((\d+), (\d+),")
CODE_LO, CODE_HI = 0x1000, 0x1C300


class Prof:
    def __init__(self, prof: str | Path, dump: str | Path, vbl_entry: int = 0x1282, extra_entries=()):
        self.rows: dict[int, tuple[str, int, int]] = {}
        for ln in Path(prof).read_text().splitlines():
            m = LINE.match(ln)
            if m:
                self.rows[int(m.group(1), 16)] = (m.group(2), int(m.group(3)), int(m.group(4)))
        self.addrs = sorted(self.rows)
        self.total = sum(c for _, _, c in self.rows.values())
        self.frames = self.rows[vbl_entry][1] if vbl_entry in self.rows else 0
        self.dump = Path(dump).read_bytes()
        self.targets = self._targets(extra_entries)
        self.tsorted = sorted(self.targets)
        self._calls: dict[int, dict[int, int]] = {}
        self._build()

    # -- static call targets from the dump -------------------------------------------------
    def _targets(self, extra) -> set[int]:
        d = self.dump
        t = set(extra)
        # static scan of the code region: jsr/jmp abs.l (4eb9/4ef9) and bsr.w (6100), at even addresses
        for a in range(CODE_LO, CODE_HI - 6, 2):
            w = (d[a] << 8) | d[a + 1]
            if w in (0x4EB9, 0x4EF9):
                tg = struct.unpack(">I", d[a + 2:a + 6])[0]
                if CODE_LO <= tg < CODE_HI and not tg & 1:
                    t.add(tg)
            elif w == 0x6100:
                disp = struct.unpack(">h", d[a + 2:a + 4])[0]
                tg = a + 2 + disp
                if CODE_LO <= tg < CODE_HI and not tg & 1:
                    t.add(tg)
        for a in self.rows:
            ins = self.rows[a][0]
            m = re.match(r"(?:jsr|bsr\.?[wsb]?)\s+\$([0-9a-f]+)(?:\.l)?$", ins)
            if m:
                t.add(int(m.group(1), 16))
        return t

    def func_of(self, addr: int) -> int:
        i = bisect.bisect_right(self.tsorted, addr) - 1
        return self.tsorted[i] if i >= 0 else 0

    def _build(self):
        self.excl: dict[int, int] = {}
        self.entry_count: dict[int, int] = {}
        for a, (ins, n, c) in self.rows.items():
            f = self.func_of(a)
            self.excl[f] = self.excl.get(f, 0) + c
            if a == f:
                self.entry_count[f] = n
        # call-site counts: caller function -> {callee: count}
        for a, (ins, n, c) in self.rows.items():
            m = re.match(r"(?:jsr|bsr\.?[wsb]?)\s+\$([0-9a-f]+)(?:\.l)?$", ins)
            if m and n:
                g = int(m.group(1), 16)
                f = self.func_of(a)
                self._calls.setdefault(f, {})
                self._calls[f][g] = self._calls[f].get(g, 0) + n
        self._incl: dict[int, float] = {}

    def calls(self, f: int) -> int:
        """Number of calls of function f = sum of its call-site counts (entry count if reached by fallthrough/jmp)."""
        return sum(cs.get(f, 0) for cs in self._calls.values()) or self.entry_count.get(f, 0)

    def incl_total(self, f: int, stack=()) -> float:
        """Inclusive cycles of f over the whole window (sum over its invocations)."""
        if f in self._incl:
            return self._incl[f]
        if f in stack:
            return 0.0
        tot = float(self.excl.get(f, 0))
        for g, n in self._calls.get(f, {}).items():
            cg = self.calls(g)
            if cg:
                tot += n * self.incl_total(g, stack + (f,)) / cg
        self._incl[f] = tot
        return tot

    def incl(self, f: int) -> float:
        """Average inclusive cycles per call of f."""
        c = self.calls(f)
        return self.incl_total(f) / c if c else 0.0

    def table(self, top: int = 15):
        fs = sorted(self.excl.items(), key=lambda kv: -kv[1])[:top]
        out = []
        for f, c in fs:
            n = self.calls(f)
            out.append((f, c, c / self.total, n, n / max(1, self.frames), c / n if n else 0))
        return out

    def loop_split(self, loop_calls: dict[int, str]):
        pass


def main():
    p = Prof(sys.argv[1], sys.argv[2])
    print(f"frames(VBL handler)={p.frames} total={p.total} cycles = {p.total / p.frames if p.frames else 0:.0f}/VBL")
    print("func     excl_cycles  excl%  calls  calls/VBL  cycles/call")
    for f, c, pc, n, nf, cc in p.table(int(sys.argv[3]) if len(sys.argv) > 3 else 25):
        print(f"${f:06x} {c:11d} {100*pc:5.2f} {n:6d} {nf:9.2f} {cc:11.0f}")


if __name__ == "__main__":
    main()
