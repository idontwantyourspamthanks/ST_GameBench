#!/usr/bin/env python3
"""Powermonger WW1 patch builder: reads patches/*.s, writes a patched floppy image from the EA original.  Same method as master's
games/done/powermonger/tools/pmpatch.py (read its header for the long version), adapted to WW1's single packed program:

  * AUTO\\WW1.PRG is rewritten as: header (data segment = N) + text with two edits + data (front stub + payload records) + a
    5-byte relocation table.  Edit 1: the first 8 bytes of text (`Super(0)`) become `jmp front.l; nop`, front being the first thing
    in the data segment (TOS loads text+data for free: no file API, no change to the disk layout).  Edit 2: the 32-byte copy routine
    that the unpacker pushes on the stack (text $2cc) ends in `jmp hook` instead of `rts`.
  * front copies the payload to $72000 (patches/core.s; the placement is argued in work/notes/placement.md), calls its init, and
    resumes the original program.  The hook runs when the unpacked game is in place at $576: it verifies the ORIGINAL bytes of every
    site against the file-derived resident image (tools/wwdepack.py), applies them all-or-nothing ('PMPO' / 'PMPF' at $727F8) and
    jumps to $576 with the register file and a7 the original `rts` produced.
  * --floppy writes build/floppy/powerwww1.st: ea.st with the new WW1.PRG (FAT chain extended into free clusters); nothing else changes.

    python3 tools/wwpatch.py verify | list | dumps | checkdisk DISK | build [--floppy] [--only NAME ...] [--out DIR] [--corrupt] [--fill]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import wwdepack  # noqa: E402

PATCHDIR = Path(os.environ.get("WW_PATCHDIR", str(ROOT / "patches")))      # WW_PATCHDIR: a scratch copy of patches/ (negative-control builds)
BUILD = ROOT / "build"
VASM = "vasmm68k_mot"
DISK = ROOT / "disks" / "ea.st"
PRG_PATH = "AUTO\\WW1.PRG"
ENTRY_DUMP = ROOT / "work" / "dumps" / "entry576.bin"       # 1 MB STE RAM at the hand-over (`dumps` command)

HDR = wwdepack.HDR
TEXT_LEN = wwdepack.TEXT_LEN
GAME = wwdepack.BASE                    # $576
PUSH_OFF = 0x2CC                        # text offset of the 8 `move.l #imm,-(a7)` that build the 32-byte copy routine
PUSH_ORIG = bytes.fromhex("2f3c005c4e75" "2f3c00204fef" "2f3c4cef7fff" "2f3c538166fa"
                          "2f3c66fa4219" "2f3c12d85380" "2f3c2549005c" "2f3c45fafffe" "4ed7")   # ... then `jmp (a7)`
FRONT_ORIG = bytes.fromhex("42a73f3c00204e41")           # clr.l -(a7); move.w #$20,-(a7); trap #1  (text offset 0)

# ---- payload layout ($72000..$77FFF, below the game's BSS end $71b84 .. TOS-style screen at $78000; work/notes/placement.md) ----
IMG_BASE, IMG_END = 0x72000, 0x78000
CODE_BASE = 0x72800                     # first address a patch blob may use
# ---- HIGH area $b0000-$f6fff: big buffers only (work/notes/memory_plan.md 3.2).  HI_BASE is also the resource-cache cap CAPLIM (pm_cachecap.s):
# the cache grows up from $80000 and must never reach a HIGH byte.  $f7000-$fffff is TOS's (start-up stack, screen on a 1 MB machine): never ours.
HI_BASE, HI_END = 0xB0000, 0xF7000
LOW_MAX_SPAN = 0x800                    # rule: a blob / `; data:` / `; scratch:` span larger than 2 KB goes HIGH
# patch-name prefix -> (LOW ranges [lo, hi), HIGH ranges [lo, hi)); first match wins; memory_plan.md 3.1 / 3.2 (pm_tooltip, qol_: where stage 3 / 2 put them)
RANGES = [
    ("pm_credit",   [(0x72800, 0x72900)], []),
    ("tick_",       [(0x72900, 0x72C00)], []),
    ("qol_",        [(0x72C00, 0x73400), (0x73900, 0x73C00), (0x74B00, 0x75800)], []),
    ("pm_tooltip",  [(0x73400, 0x75800)], []),
    ("p3b_",        [(0x73C00, 0x74000)], [(0xC0000, 0xC2000)]),
    ("tt_",         [(0x75800, 0x75C00)], []),
    ("pm_mste",     [(0x75800, 0x75C00)], []),
    ("pm_cachecap", [(0x75800, 0x75C00)], []),
    ("pm_intro_",   [(0x75800, 0x75C00)], []),
    ("fal_",        [(0x75800, 0x75C00)], []),
    ("p4_",         [(0x75C00, 0x76400)], [(0xDF000, HI_END)]),       # sprite cache $df000 + the reserve above it
    ("snd_",        [(0x76400, 0x76800)], [(0xBC000, 0xC0000)]),
    ("p6_",         [(0x76800, 0x77200)], [(0xB8000, 0xBC000)]),
    ("p7_",         [(0x77200, 0x77400)], [(0xB0000, 0xB8000)]),
    ("hd_",         [(0x77400, 0x77C00)], [(0xC2000, 0xDF000)]),
    ("test_",       [(0x77C00, 0x78000)], []),
]


def ranges_of(name: str):
    for pre, lo, hi in RANGES:
        if name.startswith(pre):
            return lo, hi
    return [], []


def check_span(pname: str, what: str, a: int, ln: int):
    """Build errors for a blob / data / scratch span: outside its patch's ranges, between the areas, a LOW span > 2 KB, HIGH below HI_BASE."""
    e = a + ln
    if ln <= 0:
        raise SystemExit(f"{pname}: empty {what} at ${a:x}")
    lo_r, hi_r = ranges_of(pname)
    if IMG_BASE <= a < IMG_END:
        if e > IMG_END or not any(l <= a and e <= h for l, h in lo_r):
            raise SystemExit(f"{pname}: {what} ${a:x}..${e - 1:x} outside its LOW range(s) " + (", ".join(f"${l:x}..${h - 1:x}" for l, h in lo_r) or "(none: the name has no entry in RANGES)"))
        if ln > LOW_MAX_SPAN:
            raise SystemExit(f"{pname}: {what} ${a:x}+{ln} is larger than 2 KB: big buffers go in the HIGH area (rule of memory_plan.md 3.1)")
    elif a >= HI_BASE:
        if e > HI_END or not any(l <= a and e <= h for l, h in hi_r):
            raise SystemExit(f"{pname}: {what} ${a:x}..${e - 1:x} outside its HIGH range(s) " + (", ".join(f"${l:x}..${h - 1:x}" for l, h in hi_r) or "(none)") + f" (HIGH area ${HI_BASE:x}..${HI_END - 1:x})")
    else:
        raise SystemExit(f"{pname}: {what} ${a:x}..${e - 1:x} is neither in the LOW area ${IMG_BASE:x}..${IMG_END - 1:x} nor at or above HI_BASE ${HI_BASE:x} (the resource cache lives in between)")

HOOK, APPLY = IMG_BASE + 0x140, IMG_BASE + 0x1F0
CORE_ORGS = {"front": 0x0, "entry": IMG_BASE, "hook": HOOK, "apply": APPLY}


def core_equs() -> dict[str, int]:
    out = {}
    for line in (PATCHDIR / "core.s").read_text().splitlines():
        m = re.match(r"^(\w+)\s+equ\s+\$([0-9a-fA-F]+)\s*(;.*)?$", line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


EQU = core_equs()
TABLE, UINITTBL, INITTBL, MARKER = EQU["TABLE"], EQU["UINITTBL"], EQU["INITTBL"], EQU["MARKER"]
assert EQU["IMG"] == IMG_BASE and EQU["HOOK"] == HOOK and EQU["APPLY"] == APPLY and EQU["GAME"] == GAME
assert EQU["PUSHOFF"] == PUSH_OFF


# ---- FAT12 image (GEMDOS: 512 B sectors, 2 sectors/cluster; 1 or 2 sides) -----------------------------------------------
class Fat12:
    def __init__(self, img: bytes):
        self.d = bytearray(img)
        (self.bps, self.spc, self.res, self.nfats, self.rootent, self.nsec, self.media, self.spf,
         self.spt, self.heads) = struct.unpack_from("<HBHBHHBHHH", self.d, 11)
        self.fat0 = self.res * self.bps
        self.root = (self.res + self.nfats * self.spf) * self.bps
        self.dstart = self.root + self.rootent * 32
        self.csize = self.spc * self.bps
        self.ncl = (self.nsec * self.bps - self.dstart) // self.csize

    def get(self, n: int) -> int:
        o = self.fat0 + n * 3 // 2
        v = self.d[o] | (self.d[o + 1] << 8)
        return (v >> 4) if n & 1 else (v & 0xFFF)

    def put(self, n: int, val: int):
        for k in range(self.nfats):
            o = self.fat0 + k * self.spf * self.bps + n * 3 // 2
            v = self.d[o] | (self.d[o + 1] << 8)
            v = ((v & 0x000F) | (val << 4)) if n & 1 else ((v & 0xF000) | val)
            self.d[o], self.d[o + 1] = v & 0xFF, v >> 8

    def chain(self, n: int) -> list[int]:
        out = []
        while 2 <= n < 0xFF0:
            out.append(n)
            n = self.get(n)
        return out

    def coff(self, n: int) -> int:
        return self.dstart + (n - 2) * self.csize

    def read(self, first: int, size: int) -> bytes:
        return b"".join(bytes(self.d[self.coff(c):self.coff(c) + self.csize]) for c in self.chain(first))[:size]

    def dir_entries(self, first: int | None):
        """(offset, name11, attr, start, size) of a directory: the root (first=None) or a cluster chain."""
        if first is None:
            spans = [(self.root, self.rootent * 32)]
        else:
            spans = [(self.coff(c), self.csize) for c in self.chain(first)]
        for off, ln in spans:
            for o in range(off, off + ln, 32):
                if self.d[o] == 0:
                    return
                if self.d[o] == 0xE5:
                    continue
                yield (o, bytes(self.d[o:o + 11]), self.d[o + 11],
                       struct.unpack_from("<H", self.d, o + 26)[0], struct.unpack_from("<I", self.d, o + 28)[0])

    def find(self, path: str):
        first = None
        parts = path.upper().split("\\")
        for i, part in enumerate(parts):
            name = (part.split(".")[0].ljust(8) + (part.split(".")[1] if "." in part else "").ljust(3)).encode()
            for ent in self.dir_entries(first):
                if ent[1] == name:
                    if i == len(parts) - 1:
                        return ent
                    first = ent[3]
                    break
            else:
                raise FileNotFoundError(path)
        raise FileNotFoundError(path)

    def read_file(self, path: str) -> bytes:
        o, _, _, start, size = self.find(path)
        return self.read(start, size)

    def write_file(self, path: str, data: bytes) -> int:
        """Replace an existing file: reuse its chain, extend into the lowest free clusters (or release the surplus)."""
        o, _, _, start, size = self.find(path)
        need = -(-len(data) // self.csize)
        ch = self.chain(start)
        if need > len(ch):
            free = [n for n in range(2, self.ncl + 2) if self.get(n) == 0]
            if len(free) < need - len(ch):
                raise SystemExit(f"{path}: needs {need - len(ch)} more clusters, only {len(free)} free ({len(free) * self.csize} bytes) on the disk")
            ch += free[:need - len(ch)]
        for c in ch[need:]:
            self.put(c, 0)
        ch = ch[:need]
        for a, b in zip(ch, ch[1:]):
            self.put(a, b)
        self.put(ch[-1], 0xFFF)
        padded = data + bytes(need * self.csize - len(data))
        for i, c in enumerate(ch):
            self.d[self.coff(c):self.coff(c) + self.csize] = padded[i * self.csize:(i + 1) * self.csize]
        struct.pack_into("<I", self.d, o + 28, len(data))
        return len(ch)

    def free_bytes(self) -> int:
        return sum(1 for n in range(2, self.ncl + 2) if self.get(n) == 0) * self.csize


_prg_cache: dict = {}


def prg_file() -> bytes:
    if "prg" not in _prg_cache:
        _prg_cache["prg"] = Fat12(DISK.read_bytes()).read_file(PRG_PATH)
    return _prg_cache["prg"]


def prg_text() -> bytes:
    f = prg_file()
    tsz, dsz, bsz, ssz = struct.unpack(">4I", f[2:18])
    if (tsz, dsz, bsz, ssz) != (TEXT_LEN, 0, 0, 0) or len(f) != HDR + TEXT_LEN + 4 or f[HDR + TEXT_LEN:] != bytes(4):
        raise SystemExit(f"{PRG_PATH}: header/size is not the EA original ({tsz:#x},{dsz:#x},{bsz:#x},{ssz:#x}, {len(f)} B)")
    return f[HDR:HDR + TEXT_LEN]


_img_cache: dict = {}


def resident_image() -> bytes:
    if "img" not in _img_cache:
        _img_cache["img"] = wwdepack.resident_image(prg_file())
    return _img_cache["img"]


def resident_bytes(addr: int, n: int) -> bytes | None:
    img = resident_image()
    o = addr - GAME
    return img[o:o + n] if 0 <= o and o + n <= len(img) else None


# ---- patch sources ---------------------------------------------------------------------------------------------------
HDR_RE = re.compile(r"^;\s*([a-z]+):\s*(.*)$")
ORG_RE = re.compile(r"^\s+org\s+\$([0-9a-fA-F]+)\s*(;.*)?$")


def hx(v: str) -> int:
    v = v.strip()
    return int(v.lstrip("$"), 16) if v.startswith("$") else int(v, 0)


class Patch:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.default = True
        self.site = None
        self.mandatory = False    # `; mandatory: yes`: verified/applied as its own group before the optional sites
        self.orig = None
        self.data = []            # (addr, len) zero-init reservations
        self.scratch = []         # (addr, len) HIGH spans the patch writes at run time but that need no initial value (no record, not zero-filled)
        self.inits = []           # routines the core calls from `init` (supervisor, TOS's world)
        self.uinits = []          # same from `uinit` (user mode, before Super)
        self.segments = []        # (org, lines)
        self.preamble = []
        cur = None
        for line in path.read_text().splitlines():
            if cur is None and re.match(r"^\s*\w+\s+equ\s+", line):
                self.preamble.append(line)
                continue
            m = HDR_RE.match(line)
            if m and cur is None:
                k, v = m.group(1), m.group(2).strip()
                if k == "name": self.name = v
                elif k == "default": self.default = v.lower() not in ("no", "false", "0")
                elif k == "site": self.site = hx(v)
                elif k == "mandatory": self.mandatory = v.lower() in ("yes", "true", "1")
                elif k == "orig": self.orig = bytes.fromhex(v.replace(" ", ""))
                elif k == "data":
                    a, l = v.split()
                    self.data.append((hx(a), int(l, 0)))
                elif k == "scratch":
                    a, l = v.split()
                    self.scratch.append((hx(a), int(l, 0)))
                elif k == "init": self.inits.append(hx(v))
                elif k == "uinit": self.uinits.append(hx(v))
                continue
            m = ORG_RE.match(line)
            if m:
                cur = (int(m.group(1), 16), [])
                self.segments.append(cur)
            elif cur is not None:
                cur[1].append(line)
            elif line.strip() and not line.strip().startswith(";"):
                raise SystemExit(f"{path}: code before first org")


def load_all():
    return [p for p in (Patch(f) for f in sorted(PATCHDIR.glob("*.s")) if f.name != "core.s") if p.site is not None or p.segments]


def selected(patches, only, hd=False):
    """--only NAMES (exactly those), else every default patch; `hd` adds the hd_* patches (HD build: GEMDOS loader + save disk file, `; mandatory: yes`)."""
    if only:
        names = {p.name for p in patches}
        bad = [n for n in only if n not in names]
        if bad:
            raise SystemExit(f"unknown patch(es): {bad}; have {sorted(names)}")
        return [p for p in patches if p.name in only or (hd and p.name.startswith("hd_"))]
    return [p for p in patches if p.default or (hd and p.name.startswith("hd_"))]


def assemble(org: int, lines: list[str], equ: str = "") -> bytes:
    src = equ + f"\n\torg\t${org:x}\n" + "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "seg.s"
        s.write_text(src)
        out = Path(td) / "seg.bin"
        r = subprocess.run([VASM, "-Fbin", "-m68000", "-quiet", "-o", str(out), str(s)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"vasm failed:\n{src}\n{r.stderr}")
        return out.read_bytes()


def core_segments() -> dict[str, bytes]:
    p = Patch(PATCHDIR / "core.s")
    equ = "\n".join(p.preamble + [f"TEXTLEN equ ${TEXT_LEN:x}"])
    by_org = {org: lines for org, lines in p.segments}
    if set(by_org) != set(CORE_ORGS.values()):
        raise SystemExit(f"core.s orgs {sorted(by_org)} != {sorted(CORE_ORGS.values())}")
    segs = {name: assemble(org, by_org[org], equ) for name, org in CORE_ORGS.items()}
    if assemble(0x1000, by_org[0], equ) != segs["front"]:
        raise SystemExit("core.s front stub is not position independent")
    if PUSH_ORIG[:48] not in segs["front"]:
        raise SystemExit("core.s front stub does not carry the original copy-routine pushes (its `.refuse` path restores them)")
    order = ["entry", "hook", "apply"]
    for a, b in zip(order, order[1:] + ["table"]):
        end = CORE_ORGS[a] + len(segs[a])
        if end > (CORE_ORGS[b] if b != "table" else TABLE):
            raise SystemExit(f"core segment {a} ({len(segs[a])} B) overflows into {b}")
    return segs


def resolve(p: Patch):
    seg = [s for s in p.segments if s[0] == p.site]
    if not seg:
        raise SystemExit(f"{p.name}: no `org ${p.site:x}` segment")
    new = assemble(p.site, seg[0][1], "\n".join(p.preamble))
    n = max(len(new), len(p.orig or b""))
    orig = resident_bytes(p.site, n)
    if orig is None:
        raise SystemExit(f"{p.name}: site ${p.site:x}+{n} is outside the resident image ${GAME:x}..${GAME + len(resident_image()) - 1:x}")
    if p.orig is not None and p.orig != orig[:len(p.orig)]:
        raise SystemExit(f"{p.name}: declared orig {p.orig.hex()} != derived {orig[:len(p.orig)].hex()}")
    if len(new) < n:
        if (n - len(new)) % 2:
            raise SystemExit(f"{p.name}: new bytes leave an odd gap; pad to an even count")
        new += b"\x4e\x71" * ((n - len(new)) // 2)
    return orig, new


def fill_byte(a: int) -> int:
    """Deterministic non-zero pattern for the free-RAM proof (never 0, differs between neighbouring pages)."""
    return 1 + ((a * 167 + (a >> 8) * 53) % 251)


def build_image(patches: list[Patch], corrupt: bool = False, fill: tuple[int, int] | None = None):
    """Returns (flat image for $72000.. (zeros where nothing is stored), sites, used spans, zero spans, fill spans)."""
    core = core_segments()
    sites = []
    for p in patches:
        if p.site is None:
            continue
        orig, new = resolve(p)
        sites.append(dict(name=p.name, addr=p.site, mandatory=p.mandatory, orig=orig, new=new))
    by_addr = sorted(sites, key=lambda s: s["addr"])
    for a, b in zip(by_addr, by_addr[1:]):
        if a["addr"] + len(a["orig"]) > b["addr"]:
            raise SystemExit(f"site overlap: {a['name']} ${a['addr']:x}+{len(a['orig'])} vs {b['name']} ${b['addr']:x}")
    tbl = bytearray()
    for s in sites:
        orig = bytearray(s["orig"])
        if corrupt and s is next(x for x in sites if not x["mandatory"]):
            orig[0] ^= 0xFF                      # test only: the hook must refuse (PMPF) and apply nothing optional
        tbl += struct.pack(">IHH", s["addr"], len(orig), 2 * s["mandatory"]) + bytes(orig) + s["new"]
    tbl += b"\0\0\0\0"
    if TABLE + len(tbl) > UINITTBL:
        raise SystemExit(f"site table overflow: {len(tbl)} B > {UINITTBL - TABLE} B in ${TABLE:x}..${UINITTBL - 1:x}")
    inits = [a for p in patches for a in p.inits]
    uinits = [a for p in patches for a in p.uinits]
    if len(inits) > 11 or len(uinits) > 11:
        raise SystemExit("more than 11 init / uinit routines")
    used = [(CORE_ORGS[k], CORE_ORGS[k] + len(core[k])) for k in ("entry", "hook", "apply")] + [
        (TABLE, TABLE + len(tbl)), (UINITTBL, UINITTBL + 48), (INITTBL, INITTBL + 48), (MARKER, MARKER + 4)]
    blobs, hi_blobs, hi_used, hi_data, hi_scratch = [], [], [], [], []
    for p in patches:
        m = re.search(r"^\s*CAPLIM\s+equ\s+\$([0-9a-fA-F]+)", "\n".join(p.preamble), re.M)
        if m and int(m.group(1), 16) != HI_BASE:
            raise SystemExit(f"{p.name}: CAPLIM ${m.group(1)} != HI_BASE ${HI_BASE:x}: the resource-cache cap must be exactly the start of the HIGH area")
        for org, lines in p.segments:
            if org == p.site:
                continue
            b = assemble(org, lines, "\n".join(p.preamble))
            check_span(p.name, "blob", org, len(b))
            if org >= HI_BASE:
                hi_blobs.append((org, b, p.name))
                hi_used.append((org, org + len(b)))
            else:
                blobs.append((org, b, p.name))
            used.append((org, org + len(b)))
        for a, ln in p.data:
            check_span(p.name, "data", a, ln)
            used.append((a, a + ln))
            if a >= HI_BASE:
                hi_data.append((a, a + ln))
        for a, ln in p.scratch:
            if a < HI_BASE:
                raise SystemExit(f"{p.name}: `; scratch:` is for HIGH spans only (${a:x})")
            check_span(p.name, "scratch", a, ln)
            used.append((a, a + ln))
            hi_scratch.append((a, a + ln))
    used.sort()
    for (a0, a1), (b0, b1) in zip(used, used[1:]):
        if a1 > b0:
            raise SystemExit(f"image overlap: ${a0:x}-${a1:x} vs ${b0:x}-${b1:x}")
    lo_used = [u for u in used if u[0] < IMG_END]
    end = (max(a1 for _, a1 in lo_used) + 3) & ~3
    img = bytearray(end - IMG_BASE)
    for key in ("entry", "hook", "apply"):
        o = CORE_ORGS[key] - IMG_BASE
        img[o:o + len(core[key])] = core[key]
    img[TABLE - IMG_BASE:TABLE - IMG_BASE + len(tbl)] = tbl
    for i, a in enumerate(inits):
        struct.pack_into(">I", img, INITTBL - IMG_BASE + 4 * i, a)
    for i, a in enumerate(uinits):
        struct.pack_into(">I", img, UINITTBL - IMG_BASE + 4 * i, a)
    for org, b, _n in blobs:
        img[org - IMG_BASE:org - IMG_BASE + len(b)] = b
    zeros = [(d, d + ln) for p in patches for d, ln in p.data] + [(UINITTBL, IMG_BASE + 0x800)]
    fills = []
    if fill:                                       # test build: every free long in [lo, hi) holds a known non-zero pattern
        lo, hi = fill
        marks = sorted(lo_used + [(a, b) for a, b in zeros if a < IMG_END])
        cur = lo
        for a, b in marks:
            a, b = a & ~3, (b + 3) & ~3
            if a > cur:
                fills.append((cur, min(a, hi)))
            cur = max(cur, b)
        if cur < hi:
            fills.append((cur, hi))
        fills = [(a, b) for a, b in fills if b > a]
    hi = dict(blobs=hi_blobs, used=sorted(hi_used), data=sorted(hi_data), scratch=sorted(hi_scratch))
    return bytes(img), sites, lo_used, zeros, fills, hi


def free_hi(hi: dict):
    """HIGH spans no patch declared (blob / data / scratch): the gate fills them with a pattern and demands 0 changes.  Guards and reserve included."""
    marks = sorted(hi["used"] + hi["data"] + hi["scratch"])
    out, cur = [], HI_BASE
    for a, b in marks:
        if a > cur:
            out.append((cur, a))
        cur = max(cur, b)
    if cur < HI_END:
        out.append((cur, HI_END))
    return out




def pack_records(img: bytes, zeros, fills=(), hi_blobs=()) -> bytes:
    """The payload as `front` reads it: records {dest.l, len.l, bytes}, zero-fill records {dest.l, len.l | $80000000}, a long 0
    at the end.  Zero spans first (so the non-zero runs overwrite where they overlap), then the non-zero runs of `img`, long
    aligned, runs closer than 12 zero bytes merged.  Empty space between blobs costs no disk bytes."""
    out = bytearray()
    for lo, hi in sorted(zeros):
        lo, hi = lo & ~3, (hi + 3) & ~3
        if hi > lo:
            out += struct.pack(">II", lo, 0x80000000 | (hi - lo))
    pad = img + bytes(-len(img) % 4)
    runs, i, n = [], 0, len(pad)
    while i < n:
        if pad[i] == 0:
            i += 1
            continue
        j = i
        while j < n and pad[j] != 0:
            j += 1
        runs.append([i, j])
        i = j
    for r in runs:
        r[0] &= ~3
        r[1] = (r[1] + 3) & ~3
    merged = []
    for a, b in runs:
        if merged and a - merged[-1][1] < 12:
            merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
        else:
            merged.append((a, b))
    for a, b in merged:
        out += struct.pack(">II", IMG_BASE + a, b - a) + pad[a:b]
    for a, b in fills:
        out += struct.pack(">II", a, b - a) + bytes(fill_byte(x) for x in range(a, b))
    for org, blob, _n in hi_blobs:                  # HIGH blobs (rare: the big buffers are zero spans or generated at init)
        blob += bytes(-len(blob) % 4)
        out += struct.pack(">II", org, len(blob)) + blob
    return bytes(out) + b"\0\0\0\0"


# ---- WW1.PRG rebuild ----------------------------------------------------------------------------------------------------
def stack_routine(hook: int) -> bytes:
    """The 32-byte copy routine the stub pushes: the original ended `lea $5c(a7),a7 ; rts` after patching its own return address
    (= $576); ours restores the same registers, lands on the same a7 as that `rts` did and `jmp hook`."""
    c = bytes.fromhex("12d8" "5380" "66fa"        # move.b (a0)+,(a1)+ ; subq.l #1,d0 ; bne  : copy the unpacked game to $576
                      "4219" "5381" "66fa"        # clr.b (a1)+ ; subq.l #1,d1 ; bne        : clear the tail
                      "4cef7fff0020"              # movem.l $20(a7),d0-d7/a0-a6             : the entry registers
                      "4fef0060"                  # lea $60(a7),a7                          : a7 as after the rts
                      "4ef9") + struct.pack(">I", hook) + bytes.fromhex("4e714e71")
    assert len(c) == 32
    return c


def push_code(c: bytes) -> bytes:
    """`move.l #imm,-(a7)` x8 building `c` on the stack (last pushed = lowest address)."""
    return b"".join(b"\x2f\x3c" + c[i:i + 4] for i in range(28, -1, -4))


def build_prg(records: bytes) -> tuple[bytes, bytes]:
    """New AUTO/WW1.PRG and the front stub bytes."""
    text = bytearray(prg_text())
    if bytes(text[PUSH_OFF:PUSH_OFF + 50]) != PUSH_ORIG:
        raise SystemExit(f"{PRG_PATH}: the copy-routine pushes at text ${PUSH_OFF:x} are not the expected original bytes")
    text[PUSH_OFF:PUSH_OFF + 48] = push_code(stack_routine(HOOK))
    if bytes(text[:8]) != FRONT_ORIG:
        raise SystemExit(f"{PRG_PATH} text does not start with the expected Super(0) call")
    text[0:8] = b"\x4e\xf9" + struct.pack(">I", TEXT_LEN) + b"\x4e\x71"
    front = core_segments()["front"]
    data = front + records
    hdr = bytearray(prg_file()[:HDR])
    struct.pack_into(">I", hdr, 6, len(data))
    return bytes(hdr) + bytes(text) + data + struct.pack(">I", 2) + b"\x00", front


# ---- commands --------------------------------------------------------------------------------------------------------
def check_resident() -> bool:
    """The file-derived image must equal the RAM dump taken at the hand-over (when the dump exists)."""
    img = resident_image()
    print(f"resident image {len(img)} B md5 {hashlib.md5(img).hexdigest()}")
    if not ENTRY_DUMP.exists():
        print(f"  (no {ENTRY_DUMP.relative_to(ROOT)}: run `dumps` for the independent check)")
        return True
    d = ENTRY_DUMP.read_bytes()[GAME:GAME + len(img)]
    ok = d == img
    print(f"  vs {ENTRY_DUMP.relative_to(ROOT)}: {'IDENTICAL' if ok else 'DIFFERENT (%d bytes)' % sum(a != b for a, b in zip(d, img))}")
    return ok


def cmd_verify(patches) -> int:
    ok = check_resident()
    prg_text()
    stack_routine(HOOK)
    core_segments()
    for p in patches:
        if p.site is None:
            continue
        orig, new = resolve(p)
        print(f"  {p.name:14s} site ${p.site:x} orig {orig.hex()} -> {new.hex()}")
    return 0 if ok else 1


def cmd_list(patches):
    for p in patches:
        print(f"{p.name:16s} default={'yes' if p.default else 'no ':3s} site={'$%x' % p.site if p.site else '-':8s} blobs={[hex(o) for o, _ in p.segments if o != p.site]}")


def build_floppy(out: Path, prg: bytes):
    fs = Fat12(DISK.read_bytes())
    n = fs.write_file(PRG_PATH, prg)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(fs.d))
    return n


def cmd_build(patches, out: Path, floppy: bool, corrupt: bool, fill: bool, all_patches, hd: bool = False):
    fillr = (IMG_BASE, IMG_END) if fill else None
    img, sites, used, zeros, fills, hi = build_image(patches, corrupt, fillr)
    records = pack_records(img, zeros, fills, hi["blobs"])
    prg, front = build_prg(records)
    out.mkdir(parents=True, exist_ok=True)
    (out / "WW1.PRG").write_bytes(prg)
    manifest = dict(patches=[p.name for p in patches], sites=[dict(name=s["name"], addr=s["addr"], orig=s["orig"].hex(), new=s["new"].hex()) for s in sites],
                    used=[list(u) for u in used], fills=[list(f) for f in fills],
                    data=[dict(patch=p.name, addr=a, len=ln) for p in patches for a, ln in p.data if a < IMG_END], image_base=IMG_BASE, image_end=IMG_END,
                    hi_base=HI_BASE, hi_end=HI_END, caplim=HI_BASE,
                    hi_used=[list(u) for u in hi["used"]], hi_data=[list(u) for u in hi["data"]], hi_scratch=[list(u) for u in hi["scratch"]],
                    free_hi=[list(u) for u in free_hi(hi)],
                    prg_md5=hashlib.md5(prg).hexdigest(), prg_size=len(prg), records=len(records))
    print(f"patches: {[p.name for p in patches]}")
    print(f"payload {len(img)} B image, {len(records)} B of records; WW1.PRG {len(prg)} B (original {len(prg_file())}); md5 {manifest['prg_md5']}")
    for s in sites:
        print(f"  site {s['name']:14s} ${s['addr']:x} {s['orig'].hex()} -> {s['new'].hex()}")
    if floppy:
        st = out / "floppy.st"
        n = build_floppy(st, prg)
        manifest["floppy"] = str(st)
        manifest["floppy_md5"] = hashlib.md5(st.read_bytes()).hexdigest()
        print(f"floppy {st} ({n} clusters for WW1.PRG, {Fat12(st.read_bytes()).free_bytes()} B free) md5 {manifest['floppy_md5']}")
    if hd:                                      # the hard-disk layout (master's): AUTO\WW1.PRG, the game's files in the root, SAVEDISK.DAT (the game's own save disk image)
        import shutil
        import pmww
        hdd = out / "hd"
        shutil.rmtree(hdd, ignore_errors=True)
        (hdd / "AUTO").mkdir(parents=True)
        (hdd / "AUTO" / "WW1.PRG").write_bytes(prg)
        fs = Fat12(DISK.read_bytes())
        names = []
        for _o, name11, attr, start, size in fs.dir_entries(None):
            if attr & 0x18 or name11[:3] == b"AUT":          # volume label / directory
                continue
            fn = name11[:8].decode().rstrip() + ("." + name11[8:].decode().rstrip() if name11[8:].strip() else "")
            (hdd / fn).write_bytes(fs.read(start, size))
            names.append(fn)
        (hdd / "SAVEDISK.DAT").write_bytes(pmww.save_disk_image())
        manifest["hd"] = str(hdd)
        print(f"hd folder {hdd}: AUTO\\WW1.PRG ({len(prg)} B), {len(names)} data files, SAVEDISK.DAT")
    exp = bytearray(IMG_END - IMG_BASE)           # what $72000..$77fff must hold at any time after the hand-over
    exp[:len(img)] = img
    for a, b in fills:
        exp[a - IMG_BASE:b - IMG_BASE] = bytes(fill_byte(x) for x in range(a, b))
    (out / "expect.bin").write_bytes(bytes(exp))
    hexp = bytearray(fill_byte(HI_BASE + i) for i in range(HI_END - HI_BASE))        # HIGH: pattern in the free spans, the blobs' bytes where a HIGH blob sits
    for org, blob, _n in hi["blobs"]:
        hexp[org - HI_BASE:org - HI_BASE + len(blob)] = blob
    (out / "hi_expect.bin").write_bytes(bytes(hexp))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return 0


def cmd_checkdisk(path: Path) -> int:
    """packcheck: the built floppy differs from the original only in the FAT copies, the size field of WW1.PRG's directory entry and the
    clusters of WW1.PRG (its old chain + the free clusters it was extended into); every other file reads back identical; the FAT is a
    valid chain structure (no cross-links, no lost clusters, all chains end)."""
    a, b = DISK.read_bytes(), path.read_bytes()
    fa, fb = Fat12(a), Fat12(b)
    ok = len(a) == len(b)
    print(f"size {len(a)} / {len(b)} bytes")
    chain_b = set(fb.chain(fb.find(PRG_PATH)[3]))
    chain_a = set(fa.chain(fa.find(PRG_PATH)[3]))
    allowed = set()
    for k in range(fa.nfats):                       # FAT copies
        allowed |= set(range(fa.fat0 + k * fa.spf * fa.bps, fa.fat0 + (k + 1) * fa.spf * fa.bps))
    ent = fa.find(PRG_PATH)[0]
    allowed |= set(range(ent + 28, ent + 32))        # the file size field
    for c in chain_a | chain_b:
        allowed |= set(range(fa.coff(c), fa.coff(c) + fa.csize))
    bad = [i for i in range(len(a)) if a[i] != b[i] and i not in allowed]
    print(f"bytes differing outside FAT / size field / WW1.PRG clusters: {len(bad)}")
    ok &= not bad
    new_clusters = sorted(chain_b - chain_a)
    print(f"WW1.PRG chain {len(chain_a)} -> {len(chain_b)} clusters; newly used (were free in the original): {new_clusters}; all free before: "
          f"{all(fa.get(c) == 0 for c in new_clusters)}")
    ok &= all(fa.get(c) == 0 for c in new_clusters)
    n_files, same_all = 0, True
    for _, n, at, st, sz in fa.dir_entries(None):
        if at & 0x10:
            continue
        nm = n.decode()
        n_files += 1
        same_all &= fa.read(st, sz) == fb.read(fb.find(nm[:8].strip() + "." + nm[8:].strip())[3], sz)
    ok &= same_all
    print(f"{n_files} root files read back identical: {same_all}")
    # cross-link / lost-cluster check over the whole FAT
    owner: dict[int, str] = {}
    def walk(first, name):
        for c in fb.chain(first):
            if c in owner:
                print(f"CROSS-LINK cluster {c}: {owner[c]} / {name}")
                return False
            owner[c] = name
        return True
    good = True
    def scan(dirfirst, prefix):
        nonlocal good
        for _, n, at, st, sz in fb.dir_entries(dirfirst):
            nm = n.decode().strip()
            if nm.startswith("."):
                continue
            if at & 0x10:
                good &= walk(st, prefix + nm + "\\")
                scan(st, prefix + nm + "\\")
            else:
                good &= walk(st, prefix + nm)
                need = -(-sz // fb.csize) if sz else 0
                good &= len(fb.chain(st)) == need
    scan(None, "")
    used = {c for c in range(2, fb.ncl + 2) if fb.get(c)}
    lost = sorted(used - set(owner))
    print(f"FAT: cross-links/length mismatches: {not good}; clusters marked used but owned by no file: {lost}")
    ok &= good and not lost
    print("CHECKDISK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_dumps() -> int:
    """work/dumps/entry576.bin: cold boot of the ORIGINAL disk, 1 MB STE / TOS 1.62, RAM saved at the hand-over (breakpoint
    pc = $576 && ($576).w = $41f9, the first instruction of the unpacked game)."""
    import time
    import pmww  # noqa: E402
    h = pmww.PMW(disk=DISK)
    try:
        ENTRY_DUMP.parent.mkdir(parents=True, exist_ok=True)
        ENTRY_DUMP.unlink(missing_ok=True)
        (h.R / "d1.txt").write_text(f"savebin {ENTRY_DUMP} 0 $100000\n")
        h.cmd(f"hatari-debug b pc = ${GAME:x} && (${GAME:x}).w = $41f9 :trace :once :file {h.R / 'd1.txt'}")
        t = time.time()
        while not ENTRY_DUMP.exists() or ENTRY_DUMP.stat().st_size < 0x100000:
            if time.time() - t > 300:
                raise TimeoutError("hand-over not reached")
            time.sleep(1)
        time.sleep(2)
        print(f"wrote {ENTRY_DUMP}")
        return 0
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify")
    sub.add_parser("list")
    sub.add_parser("dumps")
    cd = sub.add_parser("checkdisk")
    cd.add_argument("disk")
    b = sub.add_parser("build")
    b.add_argument("--only", nargs="*", default=None)
    b.add_argument("--none", action="store_true", help="core only: no patch at all (the hook runs and applies nothing)")
    b.add_argument("--floppy", action="store_true")
    b.add_argument("--out", default=str(BUILD / "default"))
    b.add_argument("--corrupt", action="store_true")
    b.add_argument("--fill", action="store_true", help="test build: free payload RAM holds a known pattern (free-RAM proof)")
    b.add_argument("--hd", action="store_true", help="HD build: adds the hd_* patches and writes <out>/hd/ (AUTO\\WW1.PRG, the game's files, SAVEDISK.DAT)")
    a = ap.parse_args()
    allp = load_all()
    if a.cmd == "list":
        return cmd_list(allp)
    if a.cmd == "dumps":
        return cmd_dumps()
    if a.cmd == "checkdisk":
        return cmd_checkdisk(Path(a.disk))
    pats = [] if getattr(a, "none", False) else selected(allp, getattr(a, "only", None), getattr(a, "hd", False))
    if a.cmd == "verify":
        return cmd_verify(pats)
    return cmd_build(pats, Path(a.out), a.floppy, a.corrupt, a.fill, allp, a.hd)


if __name__ == "__main__":
    sys.exit(main())
