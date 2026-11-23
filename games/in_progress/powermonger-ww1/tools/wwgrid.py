#!/usr/bin/env python3
"""WW1's icon hit test, a Python copy of the game's own click path ($1427a-$142fa: the two line tables $13bde / $13c58 and the cell-code
table $1a89a, all read from the resident image; compare master's pmtt_grid.py: the code is instruction-for-instruction the same).
    python3 tools/wwgrid.py            icon bounding boxes + master's KT points checked against this grid + the handler comparison with master"""
from __future__ import annotations
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import wwpatch  # noqa: E402

IMG = wwpatch.resident_image()
B = wwpatch.GAME
V_TAB, H_TAB, ACT_TAB, RECT_TAB = 0x13BDE, 0x13C58, 0x1A89A, 0x13FC4


def sw(a):
    return struct.unpack(">h", IMG[a - B:a - B + 2])[0]


def tab(base):
    a, out = base, []
    while True:
        r = [sw(a + 2 * i) for i in range(4)]
        if r[0] == 0:
            return out
        out.append(r)
        a += 8


T1, T2 = tab(V_TAB), tab(H_TAB)
ACT = []
a = ACT_TAB
while sw(a) >= 0:
    ACT.append(sw(a))
    a += 2
RECTS = [[sw(RECT_TAB + 8 * r + 2 * i) for i in range(4)] for r in range(4)]


def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def line(x, y, r):
    x0, y0, x1, y1 = r
    d0, d1, d4, d5 = x - x0, y - y0, x1 - x0, y1 - y0
    p = s16(d0) * s16(d5)
    q = int(p / d4) if d4 else None            # divs.w truncates toward zero
    d0 = p if q is None or q < -32768 or q > 32767 else q
    return s16(d1), s16(d0)


def code(x, y):
    d6 = 0
    for r in T1:
        d6 += 1
        d1, d0 = line(x, y, r)
        if not (d1 < d0):
            break
    for r in T2:
        d6 += 0x10
        d1, d0 = line(x, y, r)
        if not (d1 > d0):
            break
    return d6


def icon(x, y):
    """icon id (= index in the action table; the game's d1 / 2) or -1."""
    c = code(x, y)
    for i, v in enumerate(ACT):
        if v == c:
            return i
    return -1


def cells():
    g = {}
    for y in range(6, 200):
        for x in range(0, 320):
            g.setdefault(icon(x, y), []).append((x, y))
    return g


def centre(pts):
    cx, cy = sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    return min(pts, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)


GRID_KEYS = {0x02: 21, 0x03: 20, 0x04: 19, 0x6D: 21, 0x6E: 20, 0x6F: 19, 0x1E: 6, 0x20: 9, 0x12: 8, 0x21: 3, 0x22: 1, 0x23: 5, 0x17: 7, 0x26: 15,
             0x32: 4, 0x31: 12, 0x18: 23, 0x10: 22, 0x13: 10, 0x1F: 13, 0x14: 14, 0x2D: 2, 0x15: 16}      # scan code -> icon id (master's table, qol.md 2.3)
MAP_KEYS = {0x3B: 0, 0x3C: 1, 0x3D: 2, 0x3E: 3}                    # F1..F4 -> map mode x >> 4 (the top strip, y < 7: `lsr.w #4,d0` at $13f5a)
RECT_KEYS = {0x1A: 0, 0x1B: 1, 0x0D: 2, 0x4E: 2, 0x0C: 3, 0x4A: 3}  # [ ] = - and keypad + - -> rotate left / right, zoom in / out (rects $13fc4)
KEYPAT = r"^(?:KT:)?[ \t]+key[ \t]+\$([0-9a-f]+),(\d),(\d+),(\d+)"


def check_points(src: str) -> int:
    """Every KT entry of patches/qol_keys.s against the game's own hit test."""
    bad = n = 0
    seen = set()
    for mm in re.finditer(KEYPAT, src, re.M):
        sc, fl, x, y = int(mm.group(1), 16), int(mm.group(2)), int(mm.group(3)), int(mm.group(4))
        n += 1
        seen.add(sc)
        if sc in MAP_KEYS:
            got, ok = f"map icon {x >> 4}", y < 7 and 0 <= x < 64 and (x >> 4) == MAP_KEYS[sc]
        elif sc in RECT_KEYS:
            r = [k for k, (x0, y0, x1, y1) in enumerate(RECTS) if x0 <= x < x1 and y0 <= y < y1]
            got, ok = f"rect {r}", r == [RECT_KEYS[sc]] and fl & 1 == (1 if sc in (0x0D, 0x4E, 0x0C, 0x4A) else fl & 1)
        elif sc in GRID_KEYS:
            i = icon(x, y)
            got, ok = f"icon {i}", x >= 64 and y >= 7 and i == GRID_KEYS[sc]
        else:
            got, ok = "unknown scan code", False
        print(f"{'ok ' if ok else 'BAD'} scan ${sc:02x} flags {fl} ({x:3d},{y:3d}) -> {got}")
        bad += not ok
    miss = (set(GRID_KEYS) | set(MAP_KEYS) | set(RECT_KEYS)) - seen
    print(f"POINTS {n} entries, {bad} problems, keys of the intended set missing from KT: {sorted(hex(m) for m in miss)}")
    return bad + len(miss)


def handler_compare() -> int:
    """For every icon id: the handler reached through the game's jump table ($14340 + 2 * id) has the same instruction sequence (mnemonics, first 12) as
    master's ($135cc + 2 * id).  This is what makes master's id -> command names valid for WW1."""
    import capstone
    md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)
    m_img = (HERE.parent.parent.parent / "done/powermonger/work/dumps/entry10a6.bin").read_bytes()

    def targets(img, base, tab, n=27):
        out = []
        for i in range(n):
            o = struct.unpack(">h", img[tab + 2 * i - base:tab + 2 * i - base + 2])[0]
            out.append(tab + o)
        return out

    def mn(img, base, addr, k=12):
        return [i.mnemonic for i in md.disasm(img[addr - base:addr - base + 80], addr, k)]
    tw, tm = targets(IMG, B, 0x14340), targets(m_img, 0, 0x135CC)
    diff = 0
    for i in range(24):
        a, b = mn(IMG, B, tw[i]), mn(m_img, 0, tm[i])
        eq = a == b
        diff += not eq
        print(f"{'ok  ' if eq else 'DIFF'} id {i:2d}: WW1 ${tw[i]:x} master ${tm[i]:x}  {' '.join(a[:6])}")
    print(f"HANDLERS 24 jump-table entries, {diff} with a different instruction sequence")
    return diff


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "points":
        sys.exit(1 if check_points((HERE.parent / "patches" / "qol_keys.s").read_text()) else 0)
    if len(sys.argv) > 1 and sys.argv[1] == "handlers":
        sys.exit(1 if handler_compare() else 0)
    g = cells()
    print(f"tables: {len(T1)} vertical + {len(T2)} horizontal lines, {len(ACT)} action entries, rects {RECTS}")
    for i in sorted(g):
        if i >= 0:
            xs, ys = [p[0] for p in g[i]], [p[1] for p in g[i]]
            print(f"icon {i:2d} cell ${ACT[i]:02x}: {len(g[i]):4d} px, bbox ({min(xs)},{min(ys)})-({max(xs)},{max(ys)}), centre {centre(g[i])}")
    m = Path(HERE.parent.parent.parent / "done/powermonger/patches/qol_keys.s").read_text()
    bad = 0
    for mm in re.finditer(r"^[ \t]+key[ \t]+\$([0-9a-f]+),(\d),(\d+),(\d+)[ \t]*;?[ \t]*(.*)$", m, re.M):
        sc, fl, x, y, c = int(mm.group(1), 16), int(mm.group(2)), int(mm.group(3)), int(mm.group(4)), mm.group(5)
        if y >= 129 and x >= 64:
            i = icon(x, y)
            want = re.search(r"icon (\d+)|, (\d+)$|^(\d+)$", c)
            print(f"master KT ({x:3d},{y:3d}) scan ${sc:02x} master comment {c!r:40s} -> WW1 icon {i}")
