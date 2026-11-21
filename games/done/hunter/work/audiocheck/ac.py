#!/usr/bin/env python3
"""Hunter audio check helpers (work/notes/audiocheck.md).  Own workdirs /tmp/huntbank/<cell>, private HOME /tmp/huntbank/home.

Cold boots of the SHIPPED zips (unzipped to /tmp/huntbank/rel/<zip name>) with emulated sound ON, bank/payload RAM compared with the source
bytes (FILES/P of the HD zip: `$8BA00..` = the payload image, `$90000..` = the sample bank), checkpoints, effect capture.
Used by cell.py.  Never touches the real HOME, never kills anything but its own Hatari (stharness close()).
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
BENCH = GAME.parent.parent.parent
sys.path[:0] = [str(BENCH / "tools"), str(GAME / "tools")]
T = Path("/tmp/huntbank")
HOME = T / "home"
REL = T / "rel"
os.environ.setdefault("HATARI", "/home/ryan/Code/AtariST/hattari/build/src/hatari")
os.environ["SDL_AUDIODRIVER"] = "dummy"

ZIP = {"hd": "Hunter_v1.2.1_patched_hd_2026-11-20", "fl": "Hunter_v1.2.1_patched_floppy_2026-11-20",
       "fl2": "Hunter_v1.2.1_patched_floppy_2disk_2026-11-20",
       "hd12": "Hunter_v1.2_patched_hd_2026-11-13", "fl12": "Hunter_v1.2_patched_floppy_2026-11-13",
       "orig": "(unpatched PP original, repo root)"}
P_FILE = REL / ZIP["hd"] / "HUNTER" / "FILES" / "P"
IMG_BASE = 0x8BA00
BANK = 0x90000
FLAGS, MARKER, SV, RING, DRING = 0x8BFF0, 0x8BFF8, 0x8F000, 0x8F800, 0x8FC00
# machine -> (stharness machine, TOS key, RAM KB, extra args)
MACH = {"ste1": ("ste", "1.62", 1024, []), "ste4": ("ste", "1.62", 4096, []),
        "ms1": ("megaste", "2.06", 1024, []), "ms4": ("megaste", "2.06", 4096, []),
        "st1": ("st", "1.04", 1024, []), "st4": ("st", "1.04", 4096, []),
        "tt4": ("tt", "3.06", 4096, ["--mmu", "true", "--monitor", "vga", "--cpuclock", "32"]),
        "fal4": ("falcon", "4.04", 4096, ["--mmu", "true"])}
# regions of the payload image that are state, not code: (start, end exclusive), from the `; data:` headers of patches/*.s, FLAGS/MARKER, and the 3 blobs' scratch
DYN = [(0x8BFF0, 0x8C000), (0x8C1B2, 0x8C1C2), (0x8D000, 0x8D360), (0x8D9E0, 0x8DA00), (0x8DBC0, 0x8DBD2), (0x8DBF0, 0x8DC00),
       (0x8ECEA, 0x8ED80), (0x8F000, 0x8F100), (0x8F800, 0x90000),
       (0x8F100, 0x8F800), (0x8C940, 0x8C941), (0x8CBB0, 0x8CBC0)]   # sky_ tables/state (game-written), sav_ state words


def setup_home(cap: Path) -> None:
    cfg = HOME / ".config" / "hatari"
    cfg.mkdir(parents=True, exist_ok=True)
    src = Path("/home/ryan/.config/hatari/1040stfm.cfg")
    txt = re.sub(r"(?m)^szYMCaptureFileName.*$", f"szYMCaptureFileName = {cap}", src.read_text())
    (cfg / "hatari.cfg").write_text(txt)
    nv = Path("/home/ryan/.config/hatari/hatari.nvram")
    if nv.exists():
        shutil.copy(nv, cfg / "hatari.nvram")
    os.environ["HOME"] = str(HOME)


def source() -> bytes:
    return P_FILE.read_bytes()


def bank_len() -> int:
    p = source()
    return int.from_bytes(p[BANK - IMG_BASE + 6:BANK - IMG_BASE + 10], "big")


def savebin(h, path: Path, addr: int, n: int, tmo: float = 90) -> bytes:
    path = Path(path)
    path.unlink(missing_ok=True)
    h.cmd(f"hatari-debug savebin {path} ${addr:x} ${n:x}")
    t = time.time()
    while time.time() - t < tmo:
        time.sleep(0.5)
        if path.exists() and path.stat().st_size >= n:
            time.sleep(0.3)
            return path.read_bytes()
    raise RuntimeError(f"savebin {path} did not finish")


def pk(h, addr: int, n: int, wait: float = 0.6) -> bytes:
    out = h.debug(f"m ${addr:x} {n}", wait)
    got = {}
    for m in re.finditer(r"^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", out, re.M | re.I):
        a = int(m.group(1), 16)
        for i, x in enumerate(m.group(2).split()):
            got[a + i] = int(x, 16)
    return bytes(got.get(addr + i, 0) for i in range(n))


def runs(idx, base=0, gap=1):
    out = []
    for i in idx:
        if out and i - out[-1][1] <= gap:
            out[-1][1] = i
        else:
            out.append([i, i])
    return [(base + a, base + b) for a, b in out]


def in_dyn(a: int) -> bool:
    return any(x <= a < y for x, y in DYN)


def compare_payload(ram: bytes, tag: str) -> dict:
    """ram = bytes of RAM starting at IMG_BASE (>= len(P)).  Returns counts for the bank (`$90000..+len`), the sample-bank tail up to the file end, and the code."""
    p = source()
    bl = bank_len()
    bad_bank, bad_tail, bad_code = [], [], []
    for i, b in enumerate(p):
        a = IMG_BASE + i
        if i >= len(ram) or ram[i] != b:
            if in_dyn(a):
                continue
            if BANK <= a < BANK + bl:
                bad_bank.append(a)
            elif a >= BANK + bl:
                bad_tail.append(a)
            else:
                bad_code.append(a)
    return dict(tag=tag, bank=len(bad_bank), tail=len(bad_tail), code=len(bad_code),
                bank_runs=runs(bad_bank, 0)[:6], tail_runs=runs(bad_tail, 0)[:6], code_runs=runs(bad_code, 0)[:6])


def fmt(c: dict) -> str:
    def r(rs):
        return ", ".join(f"${a:x}-${b:x}" for a, b in rs)
    s = f"[{c['tag']:10s}] bank {c['bank']} differ, bank-file tail(panel) {c['tail']}, patch code {c['code']}"
    for k in ("bank_runs", "tail_runs", "code_runs"):
        if c[k]:
            s += f"  {k[:-5]}: {r(c[k])}"
    return s


def gamex_state(low: bytes) -> list[str]:
    """Raw lines about Gamex/D15R state in a RAM dump (>= $100000 bytes): $ffd80 pointer, count, D15R header, derived extents and overlaps."""
    L = []

    def l(a):
        return int.from_bytes(low[a:a + 4], "big")

    def w(a):
        return int.from_bytes(low[a:a + 2], "big")
    L.append(f"$ffd80.l = ${l(0xFFD80):08x}  $ffd86.w = ${w(0xFFD86):04x}  $ffd20: {low[0xFFD20:0xFFD30].hex()}")
    L.append(f"D15R $c0100: {low[0xC0100:0xC0120].hex()}  $c07e6.l = ${l(0xC07E6):08x}  $c0734.w = ${w(0xC0734):04x}  $c0736.l = ${l(0xC0736):08x}")
    ptr, n = l(0xFFD80), w(0xFFD86)
    if 0 < ptr < len(low):
        end = ptr + (n + 1) * 48
        pend = IMG_BASE + len(source())
        bl = bank_len()
        ov_b = max(0, min(end, BANK + bl) - max(ptr, BANK))
        ov_p = max(0, min(end, pend) - max(ptr, IMG_BASE))
        L.append(f"Gamex TOS copy [${ptr:x}, ${end:x}) = {(n + 1) * 48} B (swapped with $8..); payload+bank [${IMG_BASE:x}, ${pend:x}), bank [${BANK:x}, ${BANK + bl:x}): overlap with bank {ov_b} B, with payload {ov_p} B")
    else:
        L.append(f"Gamex pointer ${ptr:x} not inside the dump / not set (no Gamex TOS copy on this build)")
    z0 = IMG_BASE + len(source())
    seg = low[z0:0xC0100]
    nz = [i for i, x in enumerate(seg) if x]
    L.append(f"RAM after the payload file end ${z0:x}: first non-zero byte at ${z0 + nz[0]:x}" if nz else f"RAM ${z0:x}..$c00ff all zero")
    return L


def nz_extent(buf: bytes, base: int, lo: int, hi: int):
    seg = buf[lo - base:hi - base]
    nz = [i for i, x in enumerate(seg) if x]
    return (base + lo - base + nz[0], base + lo - base + nz[-1], len(nz)) if nz else None
