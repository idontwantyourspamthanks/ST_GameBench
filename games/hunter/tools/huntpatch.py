#!/usr/bin/env python3
"""Hunter (PP Gamex HD build) patch delivery tool.  Modelled on games/midwinter/tools/mw1patch.py.
Full reverse-engineering notes and evidence: work/notes/loading.md.

    python3 tools/huntpatch.py verify
    python3 tools/huntpatch.py list
    python3 tools/huntpatch.py build [--only N ...] [--out build/game] [--samples FILE] [--fill] [--corrupt]
    python3 tools/huntpatch.py live  [--only N ...] [--out build/live/patches] [--samples FILE] [--no-ste]
    python3 tools/huntpatch.py boot  [--game build/game] [--machine ste] [--tos 1.62] [--mem 1024]
    python3 tools/huntpatch.py taildump
    python3 tools/huntpatch.py fillcheck DUMP.bin [--manifest build/game.json]

How a build works (the originals are never modified; everything goes to build/game):
  * START.TOS is unpacked (PP's LZ, tools/pp_depack.py) and shipped UNPACKED with two changes: the 6 bytes
    `lea $7e800,a7` just before START's final `jmp $800.w` become `jmp stub` (+1 relocation entry), and a
    142-byte position-independent stub (patches/core.s, org 0) is written into a dead zero run of START's text.
  * The stub reads FILES\\P (the payload image, loaded to $8BA00) through the game's own file loader (D15R,
    `$c0152`), checks the magic 'HNPA' and calls the core.  The core verifies the original bytes of EVERY boot
    site, then applies all of them or none ('HNPO' / 'HNPF' at $8BFF8) and probes for STE DMA sound ($8BFF0).
  * phase=deferred sites (a `; load: FILES/n $dest` header) are applied by the load hook: the single exit of the
    game's file hook at $1a6 (`jmp $d60a.l`) becomes `jmp $8bb00`, which runs the applier on the file just read.
  * `; image: FILES/n` file patches edit the build copy of a game file (like the HAGA patches of Midwinter).
  * The sample bank ($90000..$AEFFF, up to 126976 bytes) is appended to the payload with `--samples FILE`.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                       # games/hunter
BENCH = ROOT.parent.parent               # gamebench
sys.path.insert(0, str(BENCH / "tools"))
from pp_depack import depack as pp_depack_program  # noqa: E402
from fire_depack import depack_fire  # noqa: E402

PATCHDIR = ROOT / "patches"
BUILD = ROOT / "build"
VASM = "vasmm68k_mot"
TAILDUMP = ROOT / "work" / "dumps" / "boot" / "ram_tail_1mb.bin"    # 1 MB STE, TOS 1.62, at START's final `jmp $800.w`
GAMEDUMP = ROOT / "work" / "dumps" / "boot" / "ram_game.bin"        # same machine, in the 3D view
TAILDUMP_FL = ROOT / "work" / "dumps" / "boot" / "ram_tail_floppy_1mb.bin"   # Paper Bag floppy, 1 MB STE, at HUNTER.TOS' final `jmp $800.w`
NOT_GAME = {"work", "tools", "build", "dist", "patches", ".omp", "alt", "__pycache__", "PLAN.md", "README.md"}

# ---- the boot chain (work/notes/loading.md) ------------------------------------------------------------
START_BASE = 0x1AE16                     # START.TOS text address in the 1 MB TOS 1.62 reference run (varies by machine)
START_TEXT = 0x82AE                      # unpacked START text length (no data segment)
START_TAIL = 0x686                       # text offset of `lea $7e800,a7` (4ff9 0007e800), followed by `jmp $800.w`
START_TAIL_ORIG = bytes.fromhex("4ff90007e8004ef80800")
STUB_OFF = 0x7F20                        # text offset of the stub: inside the zero run $7f10..$80d0 (never written, see notes)
STUB_END = 0x80D0
HOOK_SRC = 0x6A4                         # text offset of the game's file hook ($1b4ba), START copies 724 bytes to $150
HOOK_RAM, HOOK_LEN = 0x150, 724
HUM_RAM = 0x800                          # HUM.FIC (32-byte header + PP LZ) unpacks to $800.. (71684 bytes)
HUM_HDR = 0x20
PP_PATCHES = {0xAFF0: bytes.fromhex("4ef801ae"), 0xD542: bytes.fromhex("4ef900000150")}   # START's own RAM patches
PP_CONDITIONAL = (0xA09E, 2)             # `move.w #$302d,$a09e` only if U (unlimited stamina) was pressed at the HW screen
HOOK_SITE = 0x1A6                        # `jmp $d60a.l`: the single exit of the game's file hook $150
HOOK_ORIG = bytes.fromhex("4ef90000d60a")
# RAM destinations of the FILES\<digit> loads observed on a normal boot to the 3D view (work/notes/boot.md section 4)
FILE_BASE = {"6": 0x23000, "4": 0x10FB2, "3": 0x11656, "7": 0x79714, "8": 0x2AD00, "9": 0x2AD00,
             "1": 0x61514, "2": 0x48004, "E": 0x23000}
D15R_MAX = 70000                         # the game's file hook reads at most this many bytes ($c073a = $11170)

# ---- payload layout ($8BA00..$AEFFF) ---------------------------------------------------------------------
IMG_BASE, IMG_END = 0x8BA00, 0xAF000
SAMPLE_BASE = 0x90000
CORE_ORGS = {"stub": 0x0, "entry": 0x8BA00, "hook": 0x8BB00}
PREFIX_RANGES = {                        # blob orgs allowed per patch-name prefix (shared contract, inclusive ends)
    "p4_": (0x8C000, 0x8DFFF),           # Raster
    "snd_": (0x8E000, 0x8FFFF),          # Audio code, mixer state, ring buffer
    "test_": (0x8DC00, 0x8DFFF),         # loader self-tests
}


def core_equs() -> dict[str, int]:
    out = {}
    for line in (PATCHDIR / "core.s").read_text().splitlines():
        m = re.match(r"^\s*(\w+)\s+equ\s+\$([0-9a-fA-F]+)", line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


EQU = core_equs()
TABLE, MARKER, FLAGS = EQU["TABLE"], EQU["MARKER"], EQU["FLAGS"]
TABLE_END = FLAGS                        # the site table must stay below FLAGS ($8BFF0)


# ---- the game's files ------------------------------------------------------------------------------------
def lz_depack(src: bytes) -> bytes:
    """PP's LZ (the loop of tools/pp_depack.py on a bare stream): HUM.FIC after its 32-byte header."""
    out = bytearray()
    i = 0
    while True:
        c = src[i]; i += 1
        if c == 0:
            break
        if c < 0x80:
            out += src[i:i + c]; i += c
            continue
        cnt = c & 0x3F
        if c & 0x40:
            cnt += 3; off = (src[i] << 8) | src[i + 1]; i += 2
        else:
            cnt += 2; off = src[i]; i += 1
        for _ in range(cnt + 1):
            out.append(out[-off])
    return bytes(out)


def decode_reloc(b: bytes):
    p = 0
    first = struct.unpack_from(">I", b, p)[0]; p += 4
    offs = [first]
    while True:
        x = b[p]; p += 1
        if x == 0:
            break
        if x == 1:
            adv = 254
            while b[p] == 1:
                adv += 254; p += 1
            y = b[p]; p += 1
            if y == 0:
                break
            offs.append(offs[-1] + adv + y)
        else:
            offs.append(offs[-1] + x)
    return offs, p


def encode_reloc(offs):
    out = struct.pack(">I", offs[0])
    prev = offs[0]
    for o in offs[1:]:
        delta = o - prev
        k = (delta - 2) // 254
        f = delta - 254 * k
        out += b"\x01" * k + bytes([f])
        prev = o
    return out + b"\x00"


_cache: dict = {}
MODE = {"floppy": False}                 # --floppy: originals come from the Paper Bag floppy release (see the floppy section below)


def dump_path() -> Path:
    """The RAM dump the derived tail image is compared against (regenerate: `taildump [--floppy]`)."""
    p = TAILDUMP_FL if MODE["floppy"] else TAILDUMP
    if not p.exists():
        raise SystemExit(f"{p} is missing: run `huntpatch.py taildump{' --floppy' if MODE['floppy'] else ''}` first")
    return p


def start_program() -> bytes:
    if "start" not in _cache:
        _cache["start"] = pp_depack_program((ROOT / "START.TOS").read_bytes())
    return _cache["start"]


def start_text() -> bytes:
    p = start_program()
    t, d, _b = struct.unpack_from(">III", p, 2)
    assert (t, d) == (START_TEXT, 0), (hex(t), d)
    return p[28:28 + t]


# Operands in the $150 block (a verbatim copy of START's text) that differ per machine: the longs START's loader
# relocates (TPA dependent) and the four operands START patches itself at run time (old trap #1 vector, Malloc pool
# base/size x3: START text $1b618/$1b628/$1b630/$1b638, work/notes/loading.md section 3).
RUNTIME_OPERANDS = (0x1B618, 0x1B628, 0x1B630, 0x1B638)


def volatile_ranges() -> list[tuple[int, int]]:
    """RAM ranges in $150..$424 that are machine dependent (never patch them)."""
    if MODE["floppy"]:
        return []                        # no START block on the floppy: everything below $12004 is the unpacked game
    if "vol" not in _cache:
        offs, _ = decode_reloc(start_program()[28 + START_TEXT:])
        vol = [(HOOK_RAM + o - HOOK_SRC, HOOK_RAM + o - HOOK_SRC + 4) for o in offs if HOOK_SRC <= o and o + 4 <= HOOK_SRC + HOOK_LEN]
        vol += [(HOOK_RAM + (a - START_BASE) - HOOK_SRC, HOOK_RAM + (a - START_BASE) - HOOK_SRC + 4) for a in RUNTIME_OPERANDS]
        _cache["vol"] = sorted(set(vol))
    return _cache["vol"]


def tail_ram() -> dict[int, bytes]:
    """What RAM holds at START's final `jmp $800.w`, rebuilt from the shipped files (checked against the dump)."""
    if MODE["floppy"]:
        return {HUM_RAM: fl_tail()}
    if "tail" not in _cache:
        hum = (ROOT / "HUM.FIC").read_bytes()
        img = bytearray(lz_depack(hum[HUM_HDR:]))
        for a, b in PP_PATCHES.items():
            img[a - HUM_RAM:a - HUM_RAM + len(b)] = b
        _cache["tail"] = {HOOK_RAM: start_text()[HOOK_SRC:HOOK_SRC + HOOK_LEN], HUM_RAM: bytes(img)}
    return _cache["tail"]


def tail_bytes(addr: int, n: int):
    if any(a < addr + n and addr < b for a, b in volatile_ranges()):
        return None
    for base, b in tail_ram().items():
        if base <= addr and addr + n <= base + len(b):
            return b[addr - base:addr - base + n]
    return None


# ---- floppy release (Paper Bag crack): the resident game as RAM holds it at HUNTER.TOS' final `jmp $800.w` ------------------
FL_DIR = ROOT / "alt" / "floppy"
FL_IMG = FL_DIR / "Hunter (1991)(Activision)[cr Paper Bag].st"
FL_MD5 = {"HUNTER.TOS": "af6d5930410063258ac65f4099fdab63", "800": "dc72caf78831f102dd9dc08cbbbe6cb9"}
FL_STORES = (0x136, 0x22A)               # file offsets of HUNTER.TOS' run of `move.[bwl] #imm,abs.l` RAM patches (just before `bra.b $22e`)
FL_LOADER = (0x120, 0x124, 0x232, 0x4F1)  # `lea $232(pc),a0 / lea $d30e.l,a1 / move.l #$4f0,d0 / move.b (a0)+,(a1)+`: PB's file loader -> $d30e
FL_JMP_RAM = 0x6A124                     # `jmp $800.w` of the copy that runs at $6a000 (HUNTER.TOS file offset $22e)
FL_SPLICE_T = 0x68                       # `lea $22a(pc),a0 / move.w #$4e71,(a0)`: the T-key branch patches $22a, which we need for our bsr
FL_SPLICE_1 = 0xB8                       # `move.w #$4e73,$90.w` -> `bsr.w stage1 / nop`
FL_SPLICE_2 = 0x22A                      # `bra.b $22e / nop / jmp $800.w` -> `bsr.w stage2 / jmp $800.w`


class Fat12:
    """Read-only FAT12 view of an Atari .st image (root directory only: that is all the Paper Bag disk has)."""

    def __init__(self, img: bytes):
        self.img = img
        self.bps, self.spc, res, nfat, self.ndir, self.nsec, _media, spf, self.spt, self.sides = \
            struct.unpack_from("<HBHBHHBHHH", img, 11)
        self.fat0 = res * self.bps
        self.root = (res + nfat * spf) * self.bps
        self.data = self.root + self.ndir * 32
        self.cl = self.spc * self.bps

    def _fat(self, c: int) -> int:
        o = self.fat0 + c * 3 // 2
        v = self.img[o] | (self.img[o + 1] << 8)
        return (v >> 4) if c & 1 else (v & 0xFFF)

    def entries(self):
        for i in range(self.ndir):
            e = self.img[self.root + 32 * i:self.root + 32 * i + 32]
            if e[0] == 0:
                break
            if e[0] == 0xE5 or e[11] & 0x08:
                continue
            name = e[:8].decode("latin1").rstrip() + ("." + e[8:11].decode("latin1").rstrip() if e[8:11].strip() else "")
            yield name, struct.unpack_from("<H", e, 26)[0], struct.unpack_from("<I", e, 28)[0]

    def chain(self, c: int) -> list[int]:
        out = []
        while 2 <= c < 0xFF0:
            out.append(c)
            c = self._fat(c)
        return out

    def read(self, name: str) -> bytes:
        for n, c, size in self.entries():
            if n == name:
                b = b"".join(self.img[self.data + (k - 2) * self.cl:self.data + (k - 1) * self.cl] for k in self.chain(c))
                return b[:size]
        raise KeyError(name)

    def first_cluster(self, name: str) -> int:
        return next(c for n, c, _s in self.entries() if n == name)

    def free_bytes(self) -> int:
        n = (self.nsec * self.bps - self.data) // self.cl
        return sum(1 for c in range(2, n + 2) if self._fat(c) == 0) * self.cl


def fl_image() -> bytes:
    if "flimg" not in _cache:
        if not FL_IMG.exists():
            raise SystemExit(f"floppy base image missing: {FL_IMG}")
        _cache["flimg"] = FL_IMG.read_bytes()
    return _cache["flimg"]


def fl_file(name: str) -> bytes:
    b = Fat12(fl_image()).read(name)
    want = FL_MD5.get(name)
    if want and hashlib.md5(b).hexdigest() != want:
        raise SystemExit(f"{FL_IMG.name}: {name} is not the Paper Bag file this tool was written for (md5 {hashlib.md5(b).hexdigest()})")
    return b


def fl_tos() -> tuple[bytes, bytes]:
    """(header, text) of the original HUNTER.TOS; no data/bss/symbols, 2 relocations."""
    b = fl_file("HUNTER.TOS")
    magic, t, d, bss, sym = struct.unpack_from(">HIIII", b, 0)
    assert magic == 0x601A and d == 0 and bss == 0 and sym == 0 and len(b) == 28 + t + 6, "HUNTER.TOS layout"
    return b[:28], b[28:28 + t]


def fl_tail() -> bytes:
    """The resident game ($800.., 71684 bytes) as HUNTER.TOS leaves it: file 800 unpacked (FIRE), then the cracker's own
    `move.[bwl] #imm,abs.l` patches and its file loader copied to $d30e.  Executed here from the HUNTER.TOS bytes, so the
    originals of every patch site come from the user's floppy release (checked against a RAM dump by `verify --floppy`)."""
    if "fltail" in _cache:
        return _cache["fltail"]
    _hdr, t = fl_tos()
    img = bytearray(depack_fire(fl_file("800")))
    ram = {}
    # the loader block: HUNTER.TOS file $232.. (0x4f1 bytes) -> $d30e
    a0, a1, n = FL_LOADER[2], 0xD30E, FL_LOADER[3]
    assert t[FL_LOADER[0] - 28:FL_LOADER[0] - 28 + 4] == bytes.fromhex("41fa0110") and t[FL_LOADER[1] - 28 + 2:FL_LOADER[1] - 28 + 6] == struct.pack(">I", a1)
    ram[a1] = t[a0 - 28:a0 - 28 + n]
    o = FL_STORES[0] - 28
    while o + 28 < FL_STORES[1]:
        op = struct.unpack_from(">H", t, o)[0]
        if op == 0x23FC:                      # move.l #imm,abs.l
            ram[struct.unpack_from(">I", t, o + 6)[0]] = t[o + 2:o + 6]; o += 10
        elif op == 0x33FC:                    # move.w #imm,abs.l
            ram[struct.unpack_from(">I", t, o + 4)[0]] = t[o + 2:o + 4]; o += 8
        elif op == 0x13FC:                    # move.b #imm,abs.l
            ram[struct.unpack_from(">I", t, o + 4)[0]] = t[o + 3:o + 4]; o += 8
        elif op == 0x21FC:                    # move.l #imm,abs.w  (the $1e02 magic)
            ram[struct.unpack_from(">h", t, o + 6)[0] & 0xFFFFFFFF] = t[o + 2:o + 6]; o += 8
        elif op == 0x4FF9:                    # lea abs.l,a7 (the game's stack): no memory effect
            o += 6
        else:
            raise SystemExit(f"HUNTER.TOS ${o + 28:x}: unexpected opcode {op:04x} in the patch run")
    assert o + 28 == FL_STORES[1], hex(o + 28)
    assert t[FL_STORES[1] - 28:FL_STORES[1] - 28 + 8] == bytes.fromhex("6002" "4e71" "4ef80800"), "HUNTER.TOS tail"
    for a, b in ram.items():
        if a == 0x7E800:                      # the cracker also stores a byte in the stack page: outside the game image
            continue
        if not (HUM_RAM <= a and a + len(b) <= HUM_RAM + len(img)):
            raise SystemExit(f"cracker patch ${a:x}+{len(b)} outside the unpacked game")
        img[a - HUM_RAM:a - HUM_RAM + len(b)] = b
    _cache["fltail"] = bytes(img)
    return _cache["fltail"]


def file_bytes(rel: str) -> bytes:
    return (ROOT / rel).read_bytes()


def load_dest(rel: str):
    """RAM destination of a FILES/<d> file (FILE_BASE) or None."""
    m = re.fullmatch(r"FILES/([0-9A-F])", rel)
    return FILE_BASE.get(m.group(1)) if m else None


# ---- patch sources -----------------------------------------------------------------------------------------
ORG_RE = re.compile(r"^\s*org\s+\$?([0-9a-fA-F]+)\s*$", re.I)
HDR_RE = re.compile(r"^;\s*([a-z]+):\s*(.*)$")
HB_ORG_RE = re.compile(r"^\s*org\s+HB\s*\+\s*\$([0-9a-fA-F]+)\s*$", re.I)


def hx(v: str) -> int:
    return int(v.strip().lstrip("$"), 16) if v.strip().startswith("$") else int(v, 0)


class Patch:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.default = True
        self.site = None
        self.orig = None
        self.phase = None
        self.load = None          # deferred: (game file, RAM destination of that file)
        self.data = []            # (addr, len) zero-init reservations
        self.segments = []        # (org, lines)
        self.preamble = []
        self.image = None         # file patch: game file edited in the build copy
        self.base = None          # file patch: RAM address HB the file is assembled at
        self.edits = []           # file patch: (file offset, expected original bytes)
        self.fsegments = []       # file patch: (file offset, lines)
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
                elif k == "orig": self.orig = bytes.fromhex(v.replace(" ", ""))
                elif k == "phase": self.phase = v.lower()
                elif k == "load":
                    f, d = v.split()
                    self.load = (f, hx(d))
                elif k == "data":
                    a, l = v.split()
                    self.data.append((hx(a), int(l, 0)))
                elif k == "image": self.image = v
                elif k == "base": self.base = hx(v)
                elif k == "edit":
                    a, b = v.split(None, 1)
                    self.edits.append((hx(a), bytes.fromhex(b.replace(" ", ""))))
                continue
            m = HB_ORG_RE.match(line)
            if m:
                cur = (int(m.group(1), 16), [])
                self.fsegments.append(cur)
                continue
            m = ORG_RE.match(line)
            if m:
                cur = (int(m.group(1), 16), [])
                self.segments.append(cur)
            elif cur is not None:
                cur[1].append(line)
            elif line.strip() and not line.strip().startswith(";"):
                raise SystemExit(f"{path}: code before first org")

    def phase_of(self):
        return self.phase or ("boot" if self.load is None else "deferred")


def load_all():
    ps, fps = [], []
    for f in sorted(PATCHDIR.glob("*.s")):
        if f.name in ("core.s", "core_floppy.s"):
            continue
        p = Patch(f)
        if p.image is not None:
            if p.site is not None:
                raise SystemExit(f"{f.name}: `image:` and `site:` are mutually exclusive")
            fps.append(p)
        elif p.site is not None:
            ps.append(p)
    return ps, fps


# ---- assembly -------------------------------------------------------------------------------------------------
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
    equ = "\n".join(p.preamble)
    by_org = {org: lines for org, lines in p.segments}
    if set(by_org) != set(CORE_ORGS.values()):
        raise SystemExit(f"core.s orgs {sorted(by_org)} != {sorted(CORE_ORGS.values())}")
    segs = {name: assemble(org, by_org[org], equ) for name, org in CORE_ORGS.items()}
    # the stub must be position independent: it runs at an address nobody knows at build time
    again = assemble(0x1000, [l for l in by_org[0]], equ)
    if again != segs["stub"]:
        raise SystemExit("core.s stub is not position independent")
    if STUB_OFF + len(segs["stub"]) > STUB_END:
        raise SystemExit(f"stub ({len(segs['stub'])} B) does not fit the dead zone")
    if CORE_ORGS["entry"] + len(segs["entry"]) > CORE_ORGS["hook"]:
        raise SystemExit("core entry segment overflows into the hook segment")
    if CORE_ORGS["hook"] + len(segs["hook"]) > TABLE:
        raise SystemExit("core hook segment overflows into the site table")
    return segs


def site_bytes(p: Patch):
    seg = [s for s in p.segments if s[0] == p.site]
    if not seg:
        raise SystemExit(f"{p.name}: no `org ${p.site:x}` segment")
    return assemble(p.site, seg[0][1], "\n".join(p.preamble))


def site_orig(p: Patch, n: int):
    """Expected original bytes of the site, derived from the shipped files; None if the site is in no known range."""
    if p.load is None:
        ob = tail_bytes(p.site, n)
    else:
        f, dest = p.load
        fb = file_bytes(f)[:D15R_MAX]
        off = p.site - dest
        ob = fb[off:off + n] if 0 <= off and off + n <= len(fb) else None
    return ob


def resolve(p: Patch):
    new = site_bytes(p)
    orig = site_orig(p, len(new))
    if orig is None and p.orig is not None:
        raise SystemExit(f"{p.name}: site ${p.site:x}+{len(new)} outside its source "
                         f"({'the START tail image' if p.load is None else p.load[0]})")
    if orig is None:
        raise SystemExit(f"{p.name}: site ${p.site:x} is in no known range (tail image $150..$424 minus the machine-dependent "
                         f"operands / $800..$12003, or declare `; load: FILES/n $dest`)")
    if p.orig is not None and p.orig != orig[:len(p.orig)]:
        raise SystemExit(f"{p.name}: declared orig {p.orig.hex()} != files {orig[:len(p.orig)].hex()}")
    if len(new) > len(orig):
        raise SystemExit(f"{p.name}: new bytes longer than orig")
    if len(new) < len(orig):
        if (len(orig) - len(new)) % 2:
            raise SystemExit(f"{p.name}: new bytes leave an odd gap; pad to an even count")
        new += b"\x4e\x71" * ((len(orig) - len(new)) // 2)
    if MODE["floppy"]:
        return orig, new
    if PP_CONDITIONAL[0] < p.site + len(orig) and p.site < PP_CONDITIONAL[0] + PP_CONDITIONAL[1] and p.load is None:
        raise SystemExit(f"{p.name}: overlaps $a09e, which START rewrites when U (unlimited stamina) is pressed")
    return orig, new


# ---- image build --------------------------------------------------------------------------------------------------
def entry_len(n: int) -> int:
    return 8 + 2 * n


def build_image(patches: list[Patch], samples: bytes | None = None, fill: bool = False, corrupt: bool = False):
    core = core_segments()
    sites = []
    for p in patches:
        orig, new = resolve(p)
        sites.append(dict(name=p.name, addr=p.site, orig=orig, new=new, phase=p.phase_of(), load=p.load))
    if any(s["phase"] == "deferred" for s in sites):
        sites.append(dict(name="<load-hook>", addr=HOOK_SITE, orig=HOOK_ORIG,
                          new=bytes.fromhex("4ef9") + struct.pack(">I", CORE_ORGS["hook"]), phase="boot", load=None))
    by_addr = sorted(sites, key=lambda s: (s["phase"] == "deferred", s["addr"]))
    for a, b in zip(by_addr, by_addr[1:]):
        if a["phase"] == b["phase"] and a["addr"] + len(a["orig"]) > b["addr"]:
            raise SystemExit(f"site overlap: {a['name']} ${a['addr']:x}+{len(a['orig'])} vs {b['name']} ${b['addr']:x}")
    tbl = bytearray()
    for s in sites:
        orig = bytearray(s["orig"])
        if corrupt and s is sites[0]:
            orig[0] ^= 0xFF                      # test only: the core must refuse (HNPF) and apply nothing
        tbl += struct.pack(">IHH", s["addr"], len(orig), 0 if s["phase"] == "boot" else 1) + bytes(orig) + s["new"]
    tbl += b"\0\0\0\0"
    if TABLE + len(tbl) > TABLE_END:
        raise SystemExit(f"site table overflow: {len(tbl)} B > {TABLE_END - TABLE} B in ${TABLE:x}..${TABLE_END:x}")
    used = [(CORE_ORGS["entry"], CORE_ORGS["entry"] + len(core["entry"])),
            (CORE_ORGS["hook"], CORE_ORGS["hook"] + len(core["hook"])),
            (TABLE, TABLE + len(tbl)), (FLAGS, FLAGS + 4), (MARKER, MARKER + 4)]
    blobs = []
    for p in patches:
        for org, lines in p.segments:
            if org == p.site:
                continue
            pre = next((k for k in PREFIX_RANGES if p.name.startswith(k)), None)
            if pre is None:
                raise SystemExit(f"{p.name}: blob orgs need a name prefix from {sorted(PREFIX_RANGES)}")
            lo, hi = PREFIX_RANGES[pre]
            b = assemble(org, lines, "\n".join(p.preamble))
            if not (lo <= org and org + len(b) - 1 <= hi):
                raise SystemExit(f"{p.name}: blob ${org:x}..${org + len(b) - 1:x} outside ${lo:x}..${hi:x}")
            blobs.append((org, b, p.name))
            used.append((org, org + len(b)))
        for a, ln in p.data:
            pre = next((k for k in PREFIX_RANGES if p.name.startswith(k)), None)
            if pre is None or not (PREFIX_RANGES[pre][0] <= a and a + ln - 1 <= PREFIX_RANGES[pre][1]):
                raise SystemExit(f"{p.name}: data ${a:x}+{ln} outside the range of its prefix")
            used.append((a, a + ln))
    if samples is not None:
        if SAMPLE_BASE + len(samples) > IMG_END:
            raise SystemExit(f"samples {len(samples)} B exceed ${SAMPLE_BASE:x}..${IMG_END - 1:x} ({IMG_END - SAMPLE_BASE} B)")
        used.append((SAMPLE_BASE, SAMPLE_BASE + len(samples)))
    used.sort()
    for (a0, a1), (b0, b1) in zip(used, used[1:]):
        if a1 > b0:
            raise SystemExit(f"image overlap: ${a0:x}-${a1:x} vs ${b0:x}-${b1:x}")
    end = max(a1 for _, a1 in used)
    if fill:
        end = IMG_END
    img = bytearray(end - IMG_BASE)
    if fill:
        for a in range(IMG_BASE, IMG_END):
            img[a - IMG_BASE] = fill_byte(a)
        # zero the used spans so only truly unused bytes carry the pattern
        for a0, a1 in used:
            img[a0 - IMG_BASE:a1 - IMG_BASE] = bytes(a1 - a0)
    for key in ("entry", "hook"):
        o = CORE_ORGS[key] - IMG_BASE
        img[o:o + len(core[key])] = core[key]
    img[TABLE - IMG_BASE:TABLE - IMG_BASE + len(tbl)] = tbl
    for org, b, _n in blobs:
        img[org - IMG_BASE:org - IMG_BASE + len(b)] = b
    if samples is not None:
        img[SAMPLE_BASE - IMG_BASE:SAMPLE_BASE - IMG_BASE + len(samples)] = samples
    if len(img) > IMG_END - IMG_BASE:
        raise SystemExit("payload image overflow")
    return bytes(img), sites, core, used, len(tbl)


def fill_byte(a: int) -> int:
    """Deterministic non-zero pattern for the free-RAM proof (never 0, differs between neighbouring pages)."""
    return 1 + ((a * 167 + (a >> 8) * 53) % 251)


# ---- START.TOS -------------------------------------------------------------------------------------------------------
def build_start(stub: bytes) -> bytes:
    prog = start_program()
    hdr = bytearray(prog[:28])
    text = bytearray(start_text())
    rel = prog[28 + START_TEXT:]
    offs, end = decode_reloc(rel)
    assert end == len(rel) and encode_reloc(offs) == rel, "START reloc table does not round-trip"
    assert bytes(text[START_TAIL:START_TAIL + 10]) == START_TAIL_ORIG, "START tail bytes differ"
    assert not any(text[STUB_OFF:STUB_END]), "START dead zone is not zero"
    assert START_TAIL + 2 not in offs
    text[STUB_OFF:STUB_OFF + len(stub)] = stub
    text[START_TAIL:START_TAIL + 6] = bytes.fromhex("4ef9") + struct.pack(">I", STUB_OFF)   # jmp stub (relocated)
    offs.append(START_TAIL + 2)
    offs.sort()
    return bytes(hdr) + bytes(text) + encode_reloc(offs)


# ---- file patches (FILES/n) ----------------------------------------------------------------------------------------------
def file_patch_bytes(p: Patch) -> dict[int, bytes]:
    base = p.base if p.base is not None else load_dest(p.image)
    if base is None:
        raise SystemExit(f"{p.name}: `image: {p.image}` has no known load address; add `; base: $addr`")
    equ = "\n".join(p.preamble) + f"\nHB equ ${base:x}"
    segs = {}
    for off, lines in p.fsegments:
        segs[off] = assemble(base + off, lines, equ)
    return segs


def cmd_verify_files(fps) -> int:
    bad = 0
    for p in fps:
        if not re.fullmatch(r"FILES/[0-9A-F]", p.image):
            print(f"{p.name:18s} FILE PATCH: image {p.image!r} unsupported (only FILES/0..F; HUM.FIC and START.TOS are packed)")
            bad += 1
            continue
        fb = file_bytes(p.image)
        segs = file_patch_bytes(p)
        print(f"{p.name:18s} file patch {p.image} @ ${p.base if p.base is not None else load_dest(p.image):x} "
              f"({len(p.edits)} edit(s))")
        for off, orig in p.edits:
            new = segs.get(off)
            ok = fb[off:off + len(orig)] == orig and new is not None and len(new) == len(orig)
            print(f"    +${off:x}: orig {orig.hex()}  file {fb[off:off + len(orig)].hex()}  "
                  f"new {new.hex() if new else None}  ({'ok' if ok else 'MISMATCH'})")
            bad += not ok
    return bad


def apply_file_patches(fps, out: Path):
    for p in fps:
        f = out / p.image
        b = bytearray(f.read_bytes())
        for off, new in file_patch_bytes(p).items():
            b[off:off + len(new)] = new
        f.write_bytes(bytes(b))


# ---- commands -------------------------------------------------------------------------------------------------------------
def check_tail_image() -> bool:
    """The rebuilt START-tail RAM image must equal the RAM dump taken at that moment."""
    d = dump_path().read_bytes()
    ok = True
    vol = volatile_ranges()
    for base, b in tail_ram().items():
        n = sum(1 for i in range(len(b)) if not any(a <= base + i < z for a, z in vol))
        eq = all(d[base + i] == b[i] for i in range(len(b)) if not any(a <= base + i < z for a, z in vol))
        print(f"tail image ${base:05x}..${base + len(b):05x} ({len(b)} B, {n} compared) vs {dump_path().name}: "
              f"{'IDENTICAL' if eq else 'DIFFERS'}")
        ok &= eq
    print("  machine-dependent (volatile) operands, not patchable: " + " ".join(f"${a:x}+4" for a, _z in vol))
    return ok


def cmd_verify(patches, fps=()) -> int:
    bad = 0
    if not check_tail_image():
        bad += 1
    core_segments()
    d = dump_path().read_bytes()
    g = GAMEDUMP.read_bytes() if not MODE["floppy"] else b""
    for p in patches:
        try:
            orig, new = resolve(p)
        except SystemExit as e:
            print(f"{p.name:18s} site ${p.site:05x}: {e}")
            bad += 1
            continue
        src = ("floppy tail RAM" if MODE["floppy"] else "START tail RAM") if p.load is None else f"{p.load[0]} @ ${p.load[1]:x}"
        print(f"{p.name:18s} site ${p.site:05x} phase {p.phase_of():8s} src {src} len {len(orig)}")
        print(f"    original : {orig.hex()}")
        print(f"    new      : {new.hex()}")
        if p.load is None:
            dok = d[p.site:p.site + len(orig)] == orig
            print(f"    tail dump: {d[p.site:p.site + len(orig)].hex()}  ({'match' if dok else 'MISMATCH'})")
            bad += not dok
        else:
            gv = g[p.site:p.site + len(orig)]
            print(f"    3D-view dump (info only): {gv.hex()}  ({'file unchanged in RAM' if gv == orig else 'differs from the file'})")
    bad += cmd_verify_files(fps)
    print("verify:", "ALL OK" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


def cmd_list(patches, fps):
    print(f"core: stub {len(core_segments()['stub'])} B at START text ${STUB_OFF:x}; payload ${IMG_BASE:x}..${IMG_END - 1:x}; "
          f"site table ${TABLE:x}..${TABLE_END - 1:x} ({TABLE_END - TABLE} B, {entry_len(0)}+2*len per site); "
          f"FLAGS ${FLAGS:x} MARKER ${MARKER:x}")
    print(f"{'name':20s} {'default':8s} {'site':8s} {'phase':9s} {'len':4s} blobs/data")
    for p in patches:
        blobs = ",".join(f"${o:x}" for o, _ in p.segments if o != p.site) or "-"
        data = ",".join(f"${a:x}+{ln}" for a, ln in p.data) or "-"
        ln = len(site_bytes(p))
        print(f"{p.name:20s} {'yes' if p.default else 'no':8s} ${p.site:06x} {p.phase_of():9s} {ln:4d} {blobs} / {data}")
    for p in fps:
        print(f"{p.name:20s} {'yes' if p.default else 'no':8s} {p.image:8s} {'file':9s} "
              f"{sum(len(b) for _, b in p.edits):4d} (file patch)")


def copy_game(out: Path):
    out.mkdir(parents=True, exist_ok=True)
    for f in ROOT.iterdir():
        if f.name in NOT_GAME or f.is_dir() or f.suffix.lower() in (".md", ".zip", ".py"):
            continue
        shutil.copy(f, out / f.name)
    shutil.copytree(ROOT / "FILES", out / "FILES", dirs_exist_ok=True)


def read_samples(path):
    return Path(path).read_bytes() if path else None


def cmd_build(patches, fps, out: Path, samples=None, fill=False, corrupt=False):
    if cmd_verify(patches, fps):
        raise SystemExit("build aborted: verify failed")
    img, sites, core, used, tbl_len = build_image(patches, samples, fill, corrupt)
    if out.exists():
        shutil.rmtree(out)
    copy_game(out)
    (out / "START.TOS").write_bytes(build_start(core["stub"]))
    (out / "FILES" / "P").write_bytes(img)
    apply_file_patches(fps, out)
    man = {"img_base": IMG_BASE, "img_len": len(img), "fill": fill, "used": used, "marker": MARKER, "flags": FLAGS,
           "sites": [{"name": s["name"], "addr": s["addr"], "phase": s["phase"]} for s in sites]}
    out.with_suffix(".json").write_text(json.dumps(man, indent=1))
    print(f"built {out} with {len(patches)} patch(es) + {len(fps)} file patch(es)"
          f"{' [FILL pattern]' if fill else ''}{' [CORRUPTED first orig]' if corrupt else ''}")
    print(f"  START.TOS unpacked + stub ({len(core['stub'])} B at text ${STUB_OFF:x}), FILES/P = payload {len(img)} B "
          f"(${IMG_BASE:x}..${IMG_BASE + len(img) - 1:x}), site table {tbl_len} B of {TABLE_END - TABLE}")
    print(f"  {'site':8s} {'phase':9s} {'len':4s} orig -> new")
    for s in sites:
        print(f"  ${s['addr']:05x}  {s['phase']:9s} {len(s['orig']):4d} {s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]")


def cmd_live(patches, out: Path, samples=None, ste=True):
    """Payload image + site bytes for applying a patch set to a restored snapshot (load hook omitted: every overlay is
    already loaded).  The snapshot never ran the core, so the image carries MARKER='HNPO' and FLAGS (STE probe result)."""
    if cmd_verify(patches):
        raise SystemExit("live aborted: verify failed")
    img, sites, core, used, _t = build_image(patches, samples)
    img = bytearray(img)
    need = MARKER + 4 - IMG_BASE
    if len(img) < need:
        img += bytes(need - len(img))
    struct.pack_into(">I", img, MARKER - IMG_BASE, int.from_bytes(b"HNPO", "big"))
    struct.pack_into(">I", img, FLAGS - IMG_BASE, 0x3 if ste else 0x2)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".img").write_bytes(bytes(img))
    js = [{"addr": s["addr"], "orig": s["orig"].hex(), "new": s["new"].hex(), "name": s["name"]}
          for s in sites if s["name"] != "<load-hook>"]
    out.with_suffix(".json").write_text(json.dumps({"img_base": IMG_BASE, "flags": FLAGS, "marker": MARKER, "sites": js}, indent=1))
    print(f"wrote {out.with_suffix('.img')} ({len(img)} B at ${IMG_BASE:x}) and {out.with_suffix('.json')} ({len(js)} sites); "
          f"FLAGS={'3 (STE)' if ste else '2 (plain ST)'}")


def cmd_fillcheck(dump: Path, manifest: Path):
    man = json.loads(manifest.read_text())
    if not man["fill"]:
        raise SystemExit("manifest was not built with --fill")
    d = dump.read_bytes()
    used = man["used"]
    bad = []
    for a in range(IMG_BASE, IMG_END):
        if any(u0 <= a < u1 for u0, u1 in used):
            continue
        if a < len(d) and d[a] != fill_byte(a):
            bad.append(a)
    runs = []
    for a in bad:
        if runs and a - runs[-1][1] <= 1:
            runs[-1][1] = a
        else:
            runs.append([a, a])
    free = (IMG_END - IMG_BASE) - sum(u1 - u0 for u0, u1 in used)
    print(f"fillcheck {dump.name}: {free} pattern bytes in ${IMG_BASE:x}..${IMG_END - 1:x}, {len(bad)} changed")
    for a, b in runs[:40]:
        print(f"  ${a:06x}..${b:06x} ({b - a + 1} B)")
    return 1 if bad else 0


# ---- cold-boot test (uses the harness; see work/notes/loading.md section 8) -------------------------------------------------
def cmd_taildump(out: Path):
    """Regenerate the 1 MB STE / TOS 1.62 RAM dump at START's final `jmp $800.w` (the tail copy runs at $80100+; the jmp is
    $80154).  ~30 s.  This is the dump `verify` compares the START tail image against."""
    sys.path.insert(0, str(HERE))
    import hunter  # noqa: E402
    out = out.resolve()
    out.unlink(missing_ok=True)
    h = hunter.Hunter()
    try:
        cf = h.R / "tail.txt"
        cf.write_text(f"savebin {out} 0 $100000\n")
        h.debug("b all", 0.3)
        h.cmd(f"hatari-debug b pc = $80154 :trace :once :file {cf}")
        time.sleep(12); h.keypress(57); time.sleep(8); h.keypress(57)
        t = time.time()
        while not out.exists() and time.time() - t < 120:
            time.sleep(1)
        time.sleep(2)
        print(f"wrote {out} ({out.stat().st_size} B)" if out.exists() else "no dump written")
        return 0 if out.exists() else 1
    finally:
        h.close()


def blind_boot(h, name: str = "bench"):
    """boot_to_game() with fixed waits instead of reference-crop gates (same inputs, work/notes/boot.md section 2)."""
    time.sleep(14)
    h.keypress(57)
    time.sleep(10)
    h.keypress(57)
    time.sleep(32)
    h.key("space", 0.3)
    time.sleep(4)
    h.goto(*h.START_XY, home_xy=h.HOME_XY)
    h.click()
    time.sleep(4)
    h.goto(*h.ACTION_XY, home_xy=h.HOME_XY)
    h.click()
    time.sleep(4)
    for c in name:
        h.key(c, 0.15)
        time.sleep(0.3)
    h.click()
    time.sleep(5)
    h.click()
    time.sleep(12)
    if not h.in_game():
        raise RuntimeError("blind boot: the 3D loop is not running")


def cmd_boot(game: Path, machine: str, tos: str, mem: int, shots: Path | None, peeks: list[str] | None = None, dump: str | None = None, play: float = 0):
    sys.path.insert(0, str(HERE))
    import hunter  # noqa: E402
    orig_build = hunter.build_hd
    hunter.build_hd = lambda img, **k: orig_build(img, game=game, **k)
    h = None
    try:
        h = hunter.Hunter(machine=machine, tos=hunter.TOS[tos], memsize_kb=mem)
        stage = h._stage
        h._stage = lambda s, record, wait, timeout=120: stage(s, record, wait, max(timeout, 400))
        if machine == "st":
            blind_boot(h)        # the reference crops are STE (12-bit palette) pictures; a plain ST renders other colours
        else:
            h.boot_to_game()
        mk = h.peek(MARKER, 4)
        fl = h.peek(FLAGS, 4)
        print(f"BOOT OK machine={machine} tos={tos} mem={mem}K  in_game={h.in_game()}  "
              f"MARKER={mk!r}  FLAGS={fl.hex()}  fps={h.fps(250)}")
        if play:
            h.hold("Up", "Left")                      # walks to the car next to the HQ, boards it, drives
            time.sleep(play)
            h.release("Up", "Left")
        if dump:
            Path(dump).parent.mkdir(parents=True, exist_ok=True)
            h.dump(dump, 0, 0x100000)
            print(f"  dumped RAM $0..$fffff to {dump}")
        for pk in peeks or []:
            a, _, n = pk.partition(":")
            aa = int(a.lstrip("$"), 16)
            print(f"  peek ${aa:x}: {h.peek(aa, int(n or 8)).hex()}")
        if shots:
            shots.mkdir(parents=True, exist_ok=True)
            h.shot(str(shots / f"{machine}_{tos}_{mem}.png"))
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"BOOT FAILED machine={machine} tos={tos} mem={mem}K: {e!r}")
        if h is not None and shots:
            shots.mkdir(parents=True, exist_ok=True)
            try:
                h.shot(str(shots / f"{machine}_{tos}_{mem}_fail.png"))
            except Exception:  # noqa: BLE001
                pass
        return 1
    finally:
        hunter.build_hd = orig_build
        if h is not None:
            h.close()


# ---- floppy build (`build --floppy`; work/notes/floppy.md) ---------------------------------------------------------------------
FL_SCRATCH = 0xB8200                     # 512-byte boot sector buffer of the loader stage (free RAM above the payload area)
FL_SND_SERIAL = 0x485344                 # 24-bit volume serial of the sound disk ('HSD'): how the loader recognises it
FL_SND_SPT = 9                           # sound disk: 720 KB (80 tracks x 2 sides x 9 sectors), 2 sectors per cluster
FL_ST_ENV = dict(os.environ, MTOOLS_SKIP_CHECK="1")


def mtools(*args: str, data: bytes | None = None) -> bytes:
    r = subprocess.run(list(args), capture_output=True, env=FL_ST_ENV, input=data)
    if r.returncode != 0:
        raise SystemExit(f"{' '.join(args)} failed: {r.stderr.decode(errors='replace')}")
    return r.stdout


def core_probe_addr() -> int:
    """Absolute address of core.s' `probe` (the STE detection) inside the payload: the floppy loader calls it early."""
    p = Patch(PATCHDIR / "core.s")
    lines = dict((org, ln) for org, ln in p.segments)[CORE_ORGS["entry"]]
    src = "\n".join(p.preamble) + f"\n\torg\t${CORE_ORGS['entry']:x}\n" + "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "e.s").write_text(src)
        r = subprocess.run([VASM, "-Fbin", "-m68000", "-quiet", "-L", str(Path(td) / "e.lst"), "-o", str(Path(td) / "e.bin"),
                            str(Path(td) / "e.s")], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"vasm failed on the core entry:\n{r.stderr}")
        m = re.search(r"^probe\s+A:([0-9A-Fa-f]+)\s*$", (Path(td) / "e.lst").read_text(), re.M)
    if not m:
        raise SystemExit("core.s has no `probe` label")
    return int(m.group(1), 16)


def floppy_stage(equ: dict[str, int]) -> bytes:
    """patches/core_floppy.s assembled (position independent: checked at two origins)."""
    src = (PATCHDIR / "core_floppy.s").read_text().split("\n")
    pre = "\n".join(f"{k}\tequ\t{v}" for k, v in equ.items())
    body = [l for l in src if not re.match(r"^\s*org\b", l)]
    a = assemble(0, body, pre)
    b = assemble(0x1000, body, pre)
    if a != b:
        raise SystemExit("core_floppy.s is not position independent")
    return a


FL_CACHE = (0x72C, 0x7A0, 0x7FC)         # HUNTER.TOS file offsets: `lea $80200.l,a0` operands (lookup, store) and the `$7fe00` bytes-left long
FL_CACHE_OLD, FL_CACHE_REM = 0x80200, 0x7FE00
FL_STAGE = 0xB8400                       # where the loader stage reads HNPATCH.BIN before it unpacks the records (transient)


def pack_payload(img: bytes) -> bytes:
    """HNPATCH.BIN: records {dest.l, len.w (even), bytes} of the non-zero runs of the payload image (zero gaps of 16 bytes or
    more are not stored; the loader stage clears the whole area first).  Round-trips against `unpack_payload`."""
    recs = bytearray()
    i, n = 0, len(img)
    while True:
        while i < n and img[i] == 0:
            i += 1
        if i >= n:
            break
        last = i                                         # last non-zero byte of this run
        j = i
        while j < n and j - last <= 16:
            if img[j] != 0:
                last = j
            j += 1
        end = last + 1
        if (end - i) % 2:
            end += 1                                     # even length: the next record header stays word aligned
        chunk = bytes(img[i:end]).ljust(end - i, b"\0")
        recs += struct.pack(">IH", IMG_BASE + i, len(chunk)) + chunk
        i = end
    return bytes(recs)


def unpack_payload(recs: bytes, size: int) -> bytes:
    out = bytearray(size)
    o = 0
    while o < len(recs):
        a, ln = struct.unpack_from(">IH", recs, o)
        out[a - IMG_BASE:a - IMG_BASE + ln] = recs[o + 6:o + 6 + ln]
        o += 6 + ln
    return bytes(out)


def build_hunter_tos(stage: bytes, cache_base: int) -> bytes:
    """The Paper Bag HUNTER.TOS with our loader stage appended to its text and these changes (see core_floppy.s):
    $68 T-key patch of $22a off, $b8 `bsr.w stage1`, $22a `bsr.w stage2`, and the RAM file cache of the cracked loader
    (`$80200`..`$FFFFF`, three constants in the helper that HUNTER.TOS copies to $80040) moved up to `cache_base`.
    Relocation table unchanged (no new absolutes)."""
    hdr, text = fl_tos()
    t = bytearray(text)
    off = len(t) + 28                                    # file-offset coordinate of the appended blob (all offsets here include the header)

    def sp(at: int, old: str, new: bytes):
        o = at - 28
        assert bytes(t[o:o + len(new)]) == bytes.fromhex(old) and len(new) * 2 == len(old), f"HUNTER.TOS ${at:x}: {bytes(t[o:o + len(new)]).hex()}"
        t[o:o + len(new)] = new
    sp(FL_SPLICE_T, "41fa01c030bc4e71", bytes.fromhex("4e714e714e714e71"))
    sp(FL_SPLICE_1, "31fc4e730090", b"\x61\x00" + struct.pack(">h", off - (FL_SPLICE_1 + 2)) + b"\x4e\x71")
    sp(FL_SPLICE_2, "60024e714ef80800", b"\x61\x00" + struct.pack(">h", off + 4 - (FL_SPLICE_2 + 2)) + bytes.fromhex("4ef80800"))
    sp(FL_CACHE[0], f"{FL_CACHE_OLD:08x}", struct.pack(">I", cache_base))
    sp(FL_CACHE[1], f"{FL_CACHE_OLD:08x}", struct.pack(">I", cache_base))
    sp(FL_CACHE[2], f"{FL_CACHE_REM:08x}", struct.pack(">I", 0x100000 - cache_base))
    if len(stage) % 2:
        stage += b"\0"
    if off + len(stage) > 0x10A + 16388:
        raise SystemExit("loader stage does not fit the 16388 bytes HUNTER.TOS copies to $6a000")
    rel = fl_file("HUNTER.TOS")[28 + len(text):]
    h = bytearray(hdr)
    struct.pack_into(">I", h, 2, len(text) + len(stage))
    return bytes(h) + bytes(t) + stage + rel


def build_sound_disk(bank: bytes, path: Path, readme: bytes) -> dict:
    """Two-disk set, disk 2: a valid 720 KB Atari FAT12 disk holding HNSOUND.BIN (the sample bank, contiguous) and README.TXT."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    subprocess.run(["mkfs.fat", "-A", "-C", "-F", "12", "-s", "2", "-r", "112", "-R", "1", "-f", "2", "-S", "512",
                    "-i", f"{int.from_bytes(FL_SND_SERIAL.to_bytes(3, 'big'), 'little'):06x}",   # Atari variant: the 3 serial bytes at $08 are little-endian
                    "-n", "HUNTSOUND", str(path), "720"], check=True, capture_output=True)
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "HNSOUND.BIN").write_bytes(bank)
        (Path(td) / "README.TXT").write_bytes(readme)
        mtools("mcopy", "-i", str(path), str(Path(td) / "HNSOUND.BIN"), "::HNSOUND.BIN")
        mtools("mcopy", "-i", str(path), str(Path(td) / "README.TXT"), "::README.TXT")
    img = path.read_bytes()
    fat = Fat12(img)
    assert (fat.bps, fat.spc, fat.spt, fat.sides, fat.nsec) == (512, 2, FL_SND_SPT, 2, 1440), (fat.bps, fat.spc, fat.spt, fat.sides, fat.nsec)
    ser = int.from_bytes(img[8:11], "big")
    if ser != FL_SND_SERIAL:
        raise SystemExit(f"sound disk serial is {ser:06x}, not {FL_SND_SERIAL:06x} (mkfs.fat -A -i)")
    if sum(struct.unpack(">256H", img[:512])) & 0xFFFF == 0x1234:
        raise SystemExit("sound disk boot sector sums to $1234 (would be executed)")
    ch = fat.chain(fat.first_cluster("HNSOUND.BIN"))
    if ch != list(range(ch[0], ch[0] + len(ch))) or fat.read("HNSOUND.BIN") != bank:
        raise SystemExit("HNSOUND.BIN is not contiguous on the sound disk")
    lsn = (fat.data + (ch[0] - 2) * fat.cl) // 512
    return dict(lsn=lsn, secs=(len(bank) + 511) // 512, serial=ser, clusters=len(ch))


def build_disk1(path: Path, tos: bytes, extra: dict[str, bytes], tracks: int, spt: int):
    """Disk 1 = the Paper Bag disk with HUNTER.TOS replaced and `extra` files added.  Same geometry as the original (81 x 10 x 2):
    edited in place with mtools; any other geometry: a fresh Atari FAT12 file system (2 sectors per cluster, which the cracked
    loader's cluster arithmetic requires) with every file copied over by name (the loader finds files by name through the
    BPB, it has no fixed sector numbers).  Returns the free bytes."""
    old = fl_image()
    fa = Fat12(old)
    if (tracks, spt) == (fa.nsec // (fa.spt * fa.sides), fa.spt):
        shutil.copy(FL_IMG, path)
        mtools("mdel", "-i", str(path), "::HUNTER.TOS")
        with tempfile.TemporaryDirectory() as td:
            for name, b in [("HUNTER.TOS", tos)] + list(extra.items()):
                (Path(td) / name).write_bytes(b)
                mtools("mcopy", "-i", str(path), str(Path(td) / name), f"::{name}")
    else:
        path.unlink(missing_ok=True)
        kb = tracks * spt * 2 // 2
        subprocess.run(["mkfs.fat", "-A", "-C", "-F", "12", "-s", "2", "-r", "112", "-R", "1", "-f", "2", "-S", "512", "-M", "0xF9",
                        "-g", f"2/{spt}", "-n", "HUNTER", str(path), str(kb)], check=True, capture_output=True)
        with open(path, "r+b") as f:
            f.seek(8)
            f.write(old[8:11])                           # keep the original volume serial
        with tempfile.TemporaryDirectory() as td:
            for name, _c, _s in fa.entries():
                b = tos if name == "HUNTER.TOS" else fa.read(name)
                (Path(td) / name).write_bytes(b)
                mtools("mcopy", "-i", str(path), str(Path(td) / name), f"::{name}")
            for name, b in extra.items():
                (Path(td) / name).write_bytes(b)
                mtools("mcopy", "-i", str(path), str(Path(td) / name), f"::{name}")
    new = path.read_bytes()
    fb = Fat12(new)
    if (fb.bps, fb.spc, fb.spt, fb.sides, fb.nsec) != (512, 2, spt, 2, tracks * spt * 2):
        raise SystemExit(f"disk 1 geometry {(fb.bps, fb.spc, fb.spt, fb.sides, fb.nsec)}")
    if new[8:11] != old[8:11]:
        raise SystemExit("disk 1 serial changed")
    na = {n for n, _c, _s in fa.entries()}
    nb = {n for n, _c, _s in fb.entries()}
    if nb != na | set(extra):
        raise SystemExit(f"disk 1 directory differs: {sorted(nb ^ (na | set(extra)))}")
    for n in na - {"HUNTER.TOS"}:
        if fa.read(n) != fb.read(n):
            raise SystemExit(f"disk 1: {n} changed")
    for n, b in [("HUNTER.TOS", tos)] + list(extra.items()):
        if fb.read(n) != b:
            raise SystemExit(f"disk 1: {n} does not read back")
    return fb.free_bytes()


def disk2_readme() -> bytes:
    return (b"HUNTER - STE SOUND DISK (disk 2)\r\n\r\nThis disk holds the sampled sound effects for the STE.\r\n"
            b"Boot from HUNTER disk 1; the loader asks for this disk (STE, Mega STE, TT, Falcon) and then for disk 1 again.\r\n")


def cmd_build_floppy(patches, fps, out: Path, samples: bytes | None, zip_out: Path | None, readme_path: Path,
                     two_disk: bool = False, geometry: str = "auto"):
    if fps or any(p.phase_of() == "deferred" for p in patches):
        raise SystemExit("--floppy: deferred (`; load:`) and file (`; image:`) patches are HD-loader features and are not supported "
                         "on the floppy (default patch set: boot sites only)")
    if two_disk and samples is None:
        raise SystemExit("--two-disk needs --samples")
    if cmd_verify(patches, fps):
        raise SystemExit("build aborted: verify failed")
    img, sites, _core, _used, tbl_len = build_image(patches, None)
    pcap = SAMPLE_BASE - IMG_BASE
    if len(img) > pcap:
        raise SystemExit(f"payload code {len(img)} B exceeds ${pcap:x} (the sample bank starts at ${SAMPLE_BASE:x})")
    payload = pack_payload(img)
    assert unpack_payload(payload, len(img)) == img, "payload records do not round-trip"
    readme = readme_path.read_bytes() if readme_path.exists() else b""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    if geometry == "auto":
        geometry = "82x11" if (samples is not None and not two_disk) else "81x10"
    tracks, spt = (int(x) for x in geometry.split("x"))
    equ = dict(PAYLOAD=IMG_BASE, PROBE=core_probe_addr(), FLAGS=FLAGS, PCAP=pcap, SCRATCH=FL_SCRATCH, STAGE=FL_STAGE, BANK=SAMPLE_BASE,
               BANKCAP=IMG_END - SAMPLE_BASE, CACHE=IMG_END, SND_FILE=1 if (samples is not None and not two_disk) else 0,
               SND_DISK=1 if two_disk else 0, SND_LSN=1000, SND_SECS=1000, SND_SPT=FL_SND_SPT, SND_SER=FL_SND_SERIAL)   # LSN/SECS: placeholders >127 (same code size)
    d2 = None
    if samples is not None:
        if SAMPLE_BASE + len(samples) > IMG_END:
            raise SystemExit(f"samples {len(samples)} B exceed ${SAMPLE_BASE:x}..${IMG_END - 1:x}")
        if samples[:4] != b"HSND":
            raise SystemExit("the sample bank does not start with 'HSND'")
    if two_disk:
        d2 = build_sound_disk(samples, out / "HUNTER_disk2_sound.st", disk2_readme())
        equ.update(SND_LSN=d2["lsn"], SND_SECS=d2["secs"])
    stage = floppy_stage(equ)
    tos = build_hunter_tos(stage, IMG_END)
    extra = {"HNPATCH.BIN": payload}
    if samples is not None and not two_disk:
        extra["HNSOUND.BIN"] = samples
    d1p = out / "HUNTER_disk1.st"
    free = build_disk1(d1p, tos, extra, tracks, spt)
    if "HNSOUND.BIN" in extra:
        # the stage reads the bank by raw sectors (whole tracks per XBIOS Floprd): find where the file lies, check it is
        # contiguous, then rebuild with the real LSN (the stage size does not depend on it)
        fat = Fat12(d1p.read_bytes())
        ch = fat.chain(fat.first_cluster("HNSOUND.BIN"))
        if ch != list(range(ch[0], ch[0] + len(ch))):
            raise SystemExit("HNSOUND.BIN is not contiguous on disk 1")
        equ.update(SND_LSN=(fat.data + (ch[0] - 2) * fat.cl) // 512, SND_SECS=(len(samples) + 511) // 512, SND_SPT=spt)
        stage2 = floppy_stage(equ)
        assert len(stage2) == len(stage)
        stage, tos = stage2, build_hunter_tos(stage2, IMG_END)
        free = build_disk1(d1p, tos, extra, tracks, spt)
        fat = Fat12(d1p.read_bytes())
        ch2 = fat.chain(fat.first_cluster("HNSOUND.BIN"))
        assert (fat.data + (ch2[0] - 2) * fat.cl) // 512 == equ["SND_LSN"], "bank moved between passes"
    man = {"payload_base": IMG_BASE, "payload_len": len(img), "payload_file": len(payload), "marker": MARKER, "flags": FLAGS,
           "stage_len": len(stage), "geometry": geometry, "free_bytes": free, "cache_base": IMG_END, "used": _used,
           "bank": [SAMPLE_BASE, len(samples)] if samples is not None else None,
           "sound": "two-disk" if two_disk else ("single-disk" if samples is not None else "none"), "sound_disk": d2,
           "sites": [{"name": s["name"], "addr": s["addr"], "phase": s["phase"]} for s in sites]}
    (out / "manifest.json").write_text(json.dumps(man, indent=1))
    d1 = out / "HUNTER_disk1.st"
    print(f"built {out}: HUNTER_disk1.st ({d1.stat().st_size} B = {tracks} tracks x {spt} sectors x 2 sides, {free} B free)"
          + (f", HUNTER_disk2_sound.st (bank {len(samples)} B at LSN {d2['lsn']}, {d2['secs']} sectors, serial {d2['serial']:06x})" if d2 else "")
          + (f"; bank HNSOUND.BIN {len(samples)} B on disk 1" if samples is not None and not two_disk else "")
          + ("" if samples is not None else "; no sound bank (lean set)"))
    print(f"  HUNTER.TOS {len(tos)} B (stage {len(stage)} B appended; file cache moved to ${IMG_END:x}..$FFFFF), "
          f"HNPATCH.BIN {len(payload)} B (payload image {len(img)} B -> ${IMG_BASE:x}..${IMG_BASE + len(img) - 1:x}), "
          f"site table {tbl_len} B of {TABLE_END - TABLE}")
    print(f"  {'site':8s} {'len':4s} orig -> new")
    for s in sites:
        print(f"  ${s['addr']:05x}  {len(s['orig']):4d} {s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]")
    if zip_out:
        import zipfile
        zip_out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(d1, "HUNTER_disk1.st")
            if d2:
                z.write(out / "HUNTER_disk2_sound.st", "HUNTER_disk2_sound.st")
            z.writestr("README.TXT", readme.decode("latin1").replace("\r\n", "\n").replace("\n", "\r\n"))
        print(f"wrote {zip_out} ({zip_out.stat().st_size} B)")


def cmd_taildump_floppy(out: Path):
    """Regenerate the RAM dump of the ORIGINAL Paper Bag floppy at HUNTER.TOS' final `jmp $800.w` ($6a124).  ~30 s."""
    sys.path.insert(0, str(HERE))
    import huntfloppy  # noqa: E402
    out = out.resolve()
    out.unlink(missing_ok=True)
    h = huntfloppy.HunterFloppy(FL_IMG)
    try:
        cf = h.R / "tail.txt"
        cf.write_text(f"savebin {out} 0 $100000\n")
        h.debug("b all", 0.3)
        h.cmd(f"hatari-debug b pc = ${FL_JMP_RAM:x} :trace :once :file {cf}")
        t = time.time()
        time.sleep(10)
        while not out.exists() and time.time() - t < 120:
            h.keypress(57)                  # "Paper Bag presents": press a key
            time.sleep(4)
        time.sleep(2)
        print(f"wrote {out} ({out.stat().st_size} B)" if out.exists() else "no dump written")
        return 0 if out.exists() else 1
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--only", nargs="*", default=None)
    b.add_argument("--out", default=None, help="default build/game (HD) or build/floppy (--floppy)")
    b.add_argument("--samples", default=None, help="raw sample bank bytes: placed at $90000 in FILES/P (HD); --floppy: written to disk 2")
    b.add_argument("--fill", action="store_true", help="fill every unused payload byte with a pattern (free-RAM proof)")
    b.add_argument("--corrupt", action="store_true", help="TEST ONLY: corrupt the first orig byte in the payload (expects HNPF)")
    b.add_argument("--floppy", action="store_true", help="build the floppy set from the Paper Bag release (alt/floppy): disk 1 [+ disk 2 with --samples]")
    b.add_argument("--zip", nargs="?", const="auto", default=None, help="--floppy: also write dist/Hunter_patched_floppy_<date>.zip (or PATH)")
    b.add_argument("--two-disk", action="store_true", help="--floppy: standard-format 2-disk set (sample bank on a 720 KB disk 2, prompt on STE) instead of one extended disk")
    b.add_argument("--geometry", default="auto", help="--floppy: disk 1 TRACKSxSECTORS (default 82x11 with a bank on one disk, else the original 81x10)")
    lv = sub.add_parser("live")
    lv.add_argument("--only", nargs="*", default=None)
    lv.add_argument("--out", default="build/live/patches")
    lv.add_argument("--samples", default=None)
    lv.add_argument("--no-ste", action="store_true", help="set FLAGS as a plain ST (default: STE)")
    sub.add_parser("list")
    vf = sub.add_parser("verify")
    vf.add_argument("--floppy", action="store_true", help="derive the originals from the Paper Bag floppy release")
    bt = sub.add_parser("boot")
    bt.add_argument("--game", default="build/game")
    bt.add_argument("--machine", default="ste")
    bt.add_argument("--tos", default="1.62")
    bt.add_argument("--mem", type=int, default=1024)
    bt.add_argument("--shots", default="build/shots")
    bt.add_argument("--dump", default=None, help="save RAM $0..$fffff after the boot (for fillcheck)")
    bt.add_argument("--play", type=float, default=0, help="hold Up+Left this many seconds in the 3D view before dumping")
    bt.add_argument("--peek", nargs="*", default=[], help="addr[:len] RAM bytes to print after the boot (hex addr)")
    td = sub.add_parser("taildump")
    td.add_argument("--out", default=None)
    td.add_argument("--floppy", action="store_true", help="dump the original Paper Bag floppy (default: the HD build)")
    fc = sub.add_parser("fillcheck")
    fc.add_argument("dump")
    fc.add_argument("--manifest", default="build/game.json")
    a = ap.parse_args()
    MODE["floppy"] = bool(getattr(a, "floppy", False))
    patches, fps = load_all()
    if a.cmd == "list":
        cmd_list(patches, fps)
    elif a.cmd == "verify":
        if MODE["floppy"]:
            patches, fps = [p for p in patches if p.phase_of() == "boot"], []
        sys.exit(cmd_verify(patches, fps))
    elif a.cmd == "boot":
        sys.exit(cmd_boot(ROOT / a.game, a.machine, a.tos, a.mem, ROOT / a.shots if a.shots else None, a.peek, a.dump, a.play))
    elif a.cmd == "taildump":
        sys.exit(cmd_taildump_floppy(Path(a.out or TAILDUMP_FL)) if MODE["floppy"] else cmd_taildump(Path(a.out or TAILDUMP)))
    elif a.cmd == "fillcheck":
        sys.exit(cmd_fillcheck(Path(a.dump), ROOT / a.manifest))
    else:
        if a.only is None:
            sel = [p for p in patches if p.default]
            fsel = [p for p in fps if p.default]
        else:
            names = set(a.only)
            unknown = names - {p.name for p in patches} - {p.name for p in fps}
            if unknown:
                raise SystemExit(f"unknown patch(es): {sorted(unknown)}")
            sel = [p for p in patches if p.name in names]
            fsel = [p for p in fps if p.name in names]
        smp = read_samples(a.samples)
        if a.cmd == "build" and MODE["floppy"]:
            zp = None
            if a.zip:
                zp = ROOT / "dist" / f"Hunter_patched_floppy_{time.strftime('%Y-%m-%d')}.zip" if a.zip == "auto" else Path(a.zip)
            cmd_build_floppy(sel, fsel, ROOT / (a.out or "build/floppy"), smp, zp, PATCHDIR / "FLOPPY.TXT", a.two_disk, a.geometry)
        elif a.cmd == "build":
            cmd_build(sel, fsel, ROOT / (a.out or "build/game"), smp, a.fill, a.corrupt)
        else:
            if fsel:
                raise SystemExit("file patches are applied at build time, not live")
            cmd_live(sel, ROOT / a.out, smp, not a.no_ste)


if __name__ == "__main__":
    main()
