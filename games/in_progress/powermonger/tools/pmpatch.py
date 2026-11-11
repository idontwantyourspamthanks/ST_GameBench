#!/usr/bin/env python3
"""Powermonger patch delivery tool.  Modelled on games/in_progress/hunter/tools/huntpatch.py and games/done/midwinter/tools/mw1patch.py.
Full reverse-engineering notes and evidence: work/notes/loading.md.

    python3 tools/pmpatch.py verify
    python3 tools/pmpatch.py list
    python3 tools/pmpatch.py dumps        # regenerate work/dumps/entry{576,10a6}.bin (RAM at the two hand-overs) from a cold boot
    python3 tools/pmpatch.py build [--only N ...] [--floppy] [--hd] [--out build] [--samples FILE] [--corrupt]
    python3 tools/pmpatch.py live  [--only N ...] [--out build/live/patches] [--samples FILE] [--no-ste]
    python3 tools/pmpatch.py boot  [--disk build/floppy/powermonger.st | --hd build/hd/ [--acsi]] [--machine ste] [--tos 1.62]
                                   [--mem 1024] [--peek ADDR:LEN] [--peek1 ADDR:LEN] [--fill build/<kind>.json --scenario]
                                   [--call ADDR] [--saveload] [--dump F] [--shots DIR]

Default patch set: empty (every patches/*.s except core.s is `; default: no`); --only selects.  The build with no patch
is NOT pristine: it still carries the front stub, the payload core and the two hook edits.

How a build works (the originals in disks/ are never modified; everything goes to build/):
  * The game is two self-decoding PRGs in series (same packer): AUTO\\WAR.PRG (stage 1: intro, pictures, a FAT12 loader)
    depacks to $576, runs the intro, loads DATA\\SPRITE40.DAT (stage 2) and that depacks the real game to $10A6.
  * WAR.PRG is rewritten as: header (data segment = N) + text with one edit + data (front stub + payload image) + a
    5-byte relocation table.  The edit: its first 8 bytes (`Super(0)`) become `jmp front.l; nop`, front being the
    first thing in the data segment (TOS loads text+data for free: no file API, no change to the disk layout).
  * front copies the payload image to $B8000 (above everything the game uses), calls its uinit (user mode), repeats
    Super(0), calls its init (supervisor) and resumes the original program.
  * Each stage ends in a 32-byte copy routine pushed on the stack by plaintext code (WAR.PRG text $1e4, SPRITE40.DAT
    file $124).  In SPRITE40.DAT (same size, so no FAT change) it ends in `jmp hook2` instead of `rts`; WAR.PRG's gets
    the same edit (`jmp hook1`) only when a patch has `; stage: 1`.
  * hook2 runs at the first moment the game proper is in place (the registers and SR are exactly what the original
    `rts` to $10A6 gave), verifies the ORIGINAL bytes of every site against the file-derived resident image and applies
    them all-or-nothing ('PMPO' / 'PMPF' at $B87F8), then jumps to $10A6.  Sites of `; mandatory: yes` patches (the HD
    loader) are their own group, applied first, so a refused optional patch still leaves a game that runs.
  * --floppy writes build/floppy/powermonger.st: protected.st with the new WAR.PRG (the FAT chain is extended into
    free clusters) and the edited SPRITE40.DAT; nothing else on the disk changes.  --hd writes build/hd/: the same
    WAR.PRG plus DATA/ and SAVEDISK.DAT for a GEMDOS folder, with the hd_* patches (work/notes/loading.md section 7).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                       # games/in_progress/powermonger
BENCH = ROOT.parent.parent.parent               # gamebench
sys.path.insert(0, str(BENCH / "tools"))

PATCHDIR = ROOT / "patches"
BUILD = ROOT / "build"
VASM = "vasmm68k_mot"
DISK = ROOT / "disks" / "protected.st"
ENTRY_DUMPS = {1: ROOT / "work" / "dumps" / "entry576.bin", 2: ROOT / "work" / "dumps" / "entry10a6.bin"}   # 1 MB STE RAM at each hand-over

# ---- the two stages (work/notes/loading.md section 1) -------------------------------------------------------------
WAR_PATH, SPR_PATH = "AUTO\\WAR.PRG", "DATA\\SPRITE40.DAT"
HDR = 0x1C
TEXT_LEN = 0x45E90              # WAR.PRG text size (no data, bss, symbols, relocations)
SPR_TEXT_LEN = 0x18CCC          # SPRITE40.DAT text size (same wrapper)
BLOCK1, BLOCK2 = 0x216, 0x13A   # text offset of the packed block (tree table at +4): WAR.PRG, SPRITE40.DAT
BASE1, BASE2 = 0x576, 0x10A6    # RAM address of the depacked stage 1 / stage 2 text (the stub's copy destination)
PUSH1, PUSH2 = 0x1E4, 0x108     # text offset of the 8 `move.l #imm,-(a7)` that build the 32-byte copy routine
PUSH_ORIG = bytes.fromhex("2f3c005c4e75" "2f3c00204fef" "2f3c4cef7fff" "2f3c538166fa"
                          "2f3c66fa4219" "2f3c12d85380" "2f3c2549005c" "2f3c45fafffe" "4ed7")   # ... then `jmp (a7)`
FRONT_ORIG = bytes.fromhex("42a73f3c00204e41")   # clr.l -(a7); move.w #$20,-(a7); trap #1  (WAR.PRG text offset 0)

# ---- payload layout ($B8000..$EFFFF) ----------------------------------------------------------------------------
IMG_BASE, IMG_END = 0xB8000, 0xF0000
SAMPLE_BASE, SAMPLE_END = 0xD0000, 0xDD000          # sample bank limit = the snd_ range
HD_SWAP_BASE = 0xDD000                              # reserved: swap buffer S of the HD build (patches/hd_core.s: TOS's low-RAM region R)
HD_SWAP_END = 0xF6000                               # S may spill past IMG_END up to here ($F0000..$F7F45 is never touched: loading.md section 5)
HD_WINDOW = (0xBD000, 0xDD000)                      # the HD build's overlay window (hd_core.s OVL): stage 1's SPRITE40.DAT is read here
HOOK1, HOOK2, APPLY = IMG_BASE + 0x140, IMG_BASE + 0x190, IMG_BASE + 0x1F0
CORE_ORGS = {"front": 0x0, "entry": IMG_BASE, "hook1": HOOK1, "hook2": HOOK2, "apply": APPLY}
PREFIX_RANGES = {                         # blob orgs allowed per patch-name prefix (shared contract, inclusive ends)
    "tick_": (0xB8800, 0xBAFFF), "p3b_": (0xB8800, 0xBAFFF), "test_": (0xCE000, 0xCEFFF),
    "hd_": (0xBB000, 0xBCFFF),
    "p4_": (0xBD000, 0xCDFFF),
    "pm_": (0xCD000, 0xCDFFF),       # PMTooltip: the 4 KB after p4_spr's cache; inside the HD overlay window, so restored from PMLATE.DAT like the rest
    "snd_": (0xD0000, 0xDCFFF),      # $DD000..$EFFFF: reserved for the real-hardware HD build's TOS swap buffer
    "p6_": (0xD5000, 0xDCFFF),       # PMPerf2: raster patches (triangle setup + fill + slope table): the snd_ range's unused tail after its 16 KB STAGE buffer; $CE000.. stays test_ (pmab's test_walk lives there)
    "p7_": (0xDB000, 0xDBFFF),       # PMTriple: triple buffering (3 tiny hooks + data block T); inside p6_'s range after its code, in the HD overlay window
    "fal_": (0xDC000, 0xDC0FF),      # PMPack: Falcon fixes (YM mirror writes): the free page at the end of p6_'s range
    "tt_": (0xBA900, 0xBAFFF),       # PMTT: TT / Falcon fixes (pointer): the free tail of tick_'s / p3b_'s range, outside the HD overlay window
    "qol_": (0xCF000, 0xCFFFF),      # PMQoL: keys + village hover (4 KB carved from test_'s tail; test_*.s end below $CF000); in the HD overlay window (PMLATE.DAT $BD000-$DCFFF)
}
EXTRA_RANGES = {                          # a patch NAME (not prefix) that may also place blobs / data here (the image-overlap check still applies)
    "pm_tooltip": [(0xCF000, 0xCF7FF)],
    "qol_keys": [(0xCD460, 0xCD6FF)], "qol_keys2": [(0xCD460, 0xCD6FF)], "qol_hover": [(0xCD460, 0xCD6FF)], "qol_hover2": [(0xCD460, 0xCD6FF)],   # data blocks + the two small hooks: pm_tooltip's code ends at $CD444, pm_credit starts at $CDB00, so $CD460-$CD6FF is free  # its wording table (patches/pm_tooltip.s `TXT`), $CD000-$CDFFF is full of code + state + pm_credit
}


def ranges_of(name: str) -> list[tuple[int, int]]:
    pre = next((k for k in PREFIX_RANGES if name.startswith(k)), None)
    return ([PREFIX_RANGES[pre]] if pre else []) + EXTRA_RANGES.get(name, [])


def core_equs() -> dict[str, int]:
    out = {}
    for line in (PATCHDIR / "core.s").read_text().splitlines():
        m = re.match(r"^(\w+)\s+equ\s+\$([0-9a-fA-F]+)\s*(;.*)?$", line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


EQU = core_equs()
TABLE, INITTBL, FLAGS, MARKER = EQU["TABLE"], EQU["INITTBL"], EQU["FLAGS"], EQU["MARKER"]
TABLE_END = EQU["UINITTBL"]
UINITTBL = EQU["UINITTBL"]
assert EQU["IMG"] == IMG_BASE and EQU["HOOK1"] == HOOK1 and EQU["HOOK2"] == HOOK2 and EQU["APPLY"] == APPLY


# ---- FAT12 image (the game's own file system: work/notes/loading.md section 4) --------------------------------------
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

    def write_file(self, path: str, data: bytes):
        """Replace an existing file: reuse its chain, extend into the lowest free clusters (or release the surplus)."""
        o, _, _, start, size = self.find(path)
        need = -(-len(data) // self.csize)
        ch = self.chain(start)
        if need > len(ch):
            free = [n for n in range(2, self.ncl + 2) if self.get(n) == 0]
            if len(free) < need - len(ch):
                raise SystemExit(f"{path}: needs {need - len(ch)} more clusters, only {len(free)} free "
                                 f"({len(free) * self.csize} bytes) on the disk")
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


# ---- WAR.PRG: parse, depack (the stub's own algorithm), relocate -------------------------------------------------
_cache: dict = {}


def disk_image() -> bytes:
    return DISK.read_bytes()


def prg_file(path: str) -> bytes:
    if path not in _cache:
        _cache[path] = Fat12(disk_image()).read_file(path)
    return _cache[path]


def prg_text(path: str) -> bytes:
    f = prg_file(path)
    tsz, dsz, bsz, ssz = struct.unpack(">4I", f[2:18])
    want = TEXT_LEN if path == WAR_PATH else SPR_TEXT_LEN
    if f[:2] != b"\x60\x1a" or (tsz, dsz, ssz) != (want, 0, 0) or len(f) < HDR + tsz:
        raise SystemExit(f"{path} is not the original (text ${want:x}, no data/symbols)")
    if path == WAR_PATH and (bsz != 0 or len(f) != HDR + tsz + 4 or f[HDR + tsz:] != bytes(4)):
        raise SystemExit("AUTO/WAR.PRG is not the original (no bss, empty relocation table expected)")
    return f[HDR:HDR + tsz]


def pm_depack(text: bytes, b: int) -> bytes:
    """The packed block at text offset `b` (a Huffman tree + RLE escape $f100, bitstream read backwards, output written
    backwards): a transcription of the stub's loop (WAR.PRG text $10a..$140; work/notes/loading.md section 1.2)."""
    p = b + struct.unpack_from(">H", text, b + 2)[0] + 4
    psize, usize = struct.unpack_from(">II", text, p)
    src, tree = text[p + 8:p + 8 + psize], text[b + 4:]
    out = bytearray()
    pos = len(src)

    def rb():
        nonlocal pos
        pos -= 1
        return src[pos]

    d1, d3, d2, rem = rb(), 7, 0, usize
    while rem > 0:
        a4 = 0
        while True:
            bit = (d1 >> 7) & 1
            d1 = (d1 << 1) & 0xFF
            d3 -= 1
            if d3 < 0:
                d3, d1 = 7, rb()
            if bit:
                a4 += 2
            w = struct.unpack_from(">h", tree, a4)[0]
            if w < 0:
                break
            a4 += w
        d4 = w & 0xFFFF
        if d2 < 0:                              # run mode: this leaf is the count; repeat the last byte
            n = ((d2 + (d4 & 0xFF)) & 0xFF) + 1
            out += bytes([out[-1]]) * n
            rem -= n
            d2 = 0
            continue
        if d4 == 0xF100:
            d2 = -1
            continue
        out.append(d4 & 0xFF)
        rem -= 1
    return bytes(out[::-1])


def resident_image(stage: int) -> bytes:
    """The stage's text+data as it is in RAM when its stub's final `rts` hands over: depack, relocate by the load base
    ($576 for WAR.PRG, $10A6 for SPRITE40.DAT)."""
    if ("res", stage) not in _cache:
        path, blk, base = (WAR_PATH, BLOCK1, BASE1) if stage == 1 else (SPR_PATH, BLOCK2, BASE2)
        img = pm_depack(prg_text(path), blk)
        t, dd, ss = (struct.unpack(">I", img[o:o + 4])[0] for o in (2, 6, 14))
        if img[:2] != b"\x60\x1a":
            raise SystemExit("unexpected nested PRG header")
        body = bytearray(img[HDR:HDR + t + dd])
        rel = img[HDR + t + dd + ss:]
        off, p = struct.unpack(">I", rel[:4])[0], 4
        while off:
            struct.pack_into(">I", body, off, (struct.unpack_from(">I", body, off)[0] + base) & 0xFFFFFFFF)
            while True:
                c = rel[p]
                p += 1
                if c == 0:
                    off = 0
                    break
                if c == 1:
                    off += 254
                else:
                    off += c
                    break
        _cache[("res", stage)] = bytes(body)
    return _cache[("res", stage)]


def resident_bytes(stage: int, addr: int, n: int):
    r = resident_image(stage)
    o = addr - (BASE1 if stage == 1 else BASE2)
    return r[o:o + n] if 0 <= o and o + n <= len(r) else None


# ---- patch sources -----------------------------------------------------------------------------------------------
ORG_RE = re.compile(r"^\s*org\s+\$?([0-9a-fA-F]+)\s*$", re.I)
HDR_RE = re.compile(r"^;\s*([a-z]+):\s*(.*)$")


def hx(v: str) -> int:
    v = v.strip()
    return int(v.lstrip("$"), 16) if v.startswith("$") else int(v, 0)


class Patch:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.default = True
        self.site = None
        self.falcon = False       # `; falcon: yes` (stage 1 only): applied by hook1 only when the _MCH cookie says Falcon (site class 4)
        self.mandatory = False    # `; mandatory: yes`: verified/applied as its own group before the optional sites
        self.stage = 2            # 1 = applied at WAR.PRG's hand-over ($576), 2 = at the game's ($10A6)
        self.orig = None
        self.data = []            # (addr, len) zero-init reservations
        self.inits = []           # absolute addresses of routines the core calls from `init` (supervisor, TOS's world)
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
                elif k == "stage": self.stage = int(v)
                elif k == "falcon": self.falcon = v.lower() in ("yes", "true", "1")
                elif k == "mandatory": self.mandatory = v.lower() in ("yes", "true", "1")
                elif k == "orig": self.orig = bytes.fromhex(v.replace(" ", ""))
                elif k == "data":
                    a, l = v.split()
                    self.data.append((hx(a), int(l, 0)))
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
    return [p for p in (Patch(f) for f in sorted(PATCHDIR.glob("*.s")) if f.name != "core.s")
            if p.site is not None or p.segments]


# ---- assembly -----------------------------------------------------------------------------------------------------
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
    again = assemble(0x1000, by_org[0], equ)          # runs wherever TOS put the program
    if again != segs["front"]:
        raise SystemExit("core.s front stub is not position independent")
    order = ["entry", "hook1", "hook2", "apply"]
    for a, b in zip(order, order[1:] + ["table"]):
        end = CORE_ORGS[a] + len(segs[a])
        if end > (CORE_ORGS[b] if b != "table" else TABLE):
            raise SystemExit(f"core segment {a} ({len(segs[a])} B) overflows into {b}")
    return segs


def site_bytes(p: Patch):
    seg = [s for s in p.segments if s[0] == p.site]
    if not seg:
        raise SystemExit(f"{p.name}: no `org ${p.site:x}` segment")
    return assemble(p.site, seg[0][1], "\n".join(p.preamble))


def resolve(p: Patch):
    new = site_bytes(p)
    n = max(len(new), len(p.orig or b""))
    orig = resident_bytes(p.stage, p.site, n)
    if orig is None:
        base = BASE1 if p.stage == 1 else BASE2
        raise SystemExit(f"{p.name}: site ${p.site:x}+{n} is outside the stage {p.stage} resident image "
                         f"${base:x}..${base + len(resident_image(p.stage)) - 1:x}")
    if p.orig is not None and p.orig != orig[:len(p.orig)]:
        raise SystemExit(f"{p.name}: declared orig {p.orig.hex()} != derived {orig[:len(p.orig)].hex()}")
    if len(new) < n:
        if (n - len(new)) % 2:
            raise SystemExit(f"{p.name}: new bytes leave an odd gap; pad to an even count")
        new += b"\x4e\x71" * ((n - len(new)) // 2)
    return orig, new


# ---- payload image ------------------------------------------------------------------------------------------------
def entry_len(n: int) -> int:
    return 8 + 2 * n


def fill_byte(a: int) -> int:
    """Deterministic non-zero pattern for the free-RAM proof (never 0, differs between neighbouring pages)."""
    return 1 + ((a * 167 + (a >> 8) * 53) % 251)


def build_image(patches: list[Patch], samples: bytes | None = None, corrupt: bool = False, hd: bool = False):
    """Returns (flat image bytes for $B8000.. (zeros where nothing is stored), sites, used spans, zero spans).  The zero spans
    (`; data:` reservations and the init-table / FLAGS / MARKER area) are cleared by `front` at boot; everything else that is
    zero in the flat image is simply not stored (see pack_records)."""
    core = core_segments()
    sites = []
    for p in patches:
        if p.site is None:
            continue
        orig, new = resolve(p)
        sites.append(dict(name=p.name, addr=p.site, stage=p.stage, mandatory=p.mandatory, falcon=p.falcon, orig=orig, new=new))
    by_addr = sorted(sites, key=lambda s: (s["stage"], s["addr"]))
    for a, b in zip(by_addr, by_addr[1:]):
        if a["stage"] == b["stage"] and a["addr"] + len(a["orig"]) > b["addr"]:
            raise SystemExit(f"site overlap: {a['name']} ${a['addr']:x}+{len(a['orig'])} vs {b['name']} ${b['addr']:x}")
    tbl = bytearray()
    for s in sites:
        orig = bytearray(s["orig"])
        if corrupt and s is next(x for x in sites if not x["mandatory"]):
            orig[0] ^= 0xFF                      # test only: the core must refuse (PMPF) and apply nothing
        tbl += struct.pack(">IHH", s["addr"], len(orig), 4 if s["falcon"] else s["stage"] - 1 + 2 * s["mandatory"]) + bytes(orig) + s["new"]
    tbl += b"\0\0\0\0"
    if TABLE + len(tbl) > TABLE_END:
        raise SystemExit(f"site table overflow: {len(tbl)} B > {TABLE_END - TABLE} B in ${TABLE:x}..${TABLE_END - 1:x}")
    inits = [a for p in patches for a in p.inits]
    uinits = [a for p in patches for a in p.uinits]
    if len(inits) > 11 or len(uinits) > 11:
        raise SystemExit("more than 11 init / uinit routines")
    used = [(CORE_ORGS[k], CORE_ORGS[k] + len(core[k])) for k in ("entry", "hook1", "hook2", "apply")] + [
            (TABLE, TABLE + len(tbl)), (UINITTBL, UINITTBL + 48), (INITTBL, INITTBL + 48), (FLAGS, FLAGS + 4), (MARKER, MARKER + 4)]
    blobs = []
    for p in patches:
        for org, lines in p.segments:
            if org == p.site:
                continue
            rg = ranges_of(p.name)
            if not rg:
                raise SystemExit(f"{p.name}: blob orgs need a name prefix from {sorted(PREFIX_RANGES)}")
            b = assemble(org, lines, "\n".join(p.preamble))
            if not any(lo <= org and org + len(b) - 1 <= hi for lo, hi in rg):
                raise SystemExit(f"{p.name}: blob ${org:x}..${org + len(b) - 1:x} outside " + ", ".join(f"${lo:x}..${hi:x}" for lo, hi in rg))
            blobs.append((org, b, p.name))
            used.append((org, org + len(b)))
        for a, ln in p.data:
            if not any(lo <= a and a + ln - 1 <= hi for lo, hi in ranges_of(p.name)):
                raise SystemExit(f"{p.name}: data ${a:x}+{ln} outside the range of its prefix")
            used.append((a, a + ln))
    if samples is not None:
        if SAMPLE_BASE + len(samples) > SAMPLE_END:
            raise SystemExit(f"samples {len(samples)} B exceed ${SAMPLE_BASE:x}..${SAMPLE_END - 1:x} ({SAMPLE_END - SAMPLE_BASE} B)")
        used.append((SAMPLE_BASE, SAMPLE_BASE + len(samples)))
    used.sort()
    for (a0, a1), (b0, b1) in zip(used, used[1:]):
        if a1 > b0:
            raise SystemExit(f"image overlap: ${a0:x}-${a1:x} vs ${b0:x}-${b1:x}")
    for a0, a1 in used:
        if a1 > HD_SWAP_BASE and a0 < IMG_END:      # every build keeps it free: the HD build's TOS swap buffer lives here
            raise SystemExit(f"payload ${a0:x}-${a1 - 1:x} overlaps ${HD_SWAP_BASE:x}..${IMG_END - 1:x}, reserved for the HD build's TOS swap buffer")
    end = (max(a1 for _, a1 in used) + 3) & ~3
    img = bytearray(end - IMG_BASE)
    for key in ("entry", "hook1", "hook2", "apply"):
        o = CORE_ORGS[key] - IMG_BASE
        img[o:o + len(core[key])] = core[key]
    img[TABLE - IMG_BASE:TABLE - IMG_BASE + len(tbl)] = tbl
    for i, a in enumerate(inits):
        struct.pack_into(">I", img, INITTBL - IMG_BASE + 4 * i, a)
    for i, a in enumerate(uinits):
        struct.pack_into(">I", img, UINITTBL - IMG_BASE + 4 * i, a)
    for org, b, _n in blobs:
        img[org - IMG_BASE:org - IMG_BASE + len(b)] = b
    if samples is not None:
        img[SAMPLE_BASE - IMG_BASE:SAMPLE_BASE - IMG_BASE + len(samples)] = samples
    zeros = [(d, d + ln) for p in patches for d, ln in p.data] + [(UINITTBL, IMG_BASE + 0x800)]
    if hd:
        used.append((HD_SWAP_BASE, IMG_END))         # (S spills up to HD_SWAP_END, which is outside the free-RAM proof anyway)
    return bytes(img), sites, used, zeros


def pack_records(img: bytes, zeros) -> bytes:
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
    while i < n:                                  # maximal non-zero byte spans
        if pad[i] == 0:
            i += 1
            continue
        j = i
        while j < n and pad[j] != 0:
            j += 1
        runs.append([i, j])
        i = j
    for r in runs:                                # long-align, then merge runs closer than 12 bytes
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
    return bytes(out) + b"\0\0\0\0"


# ---- WAR.PRG rebuild ------------------------------------------------------------------------------------------------
def stack_routine(hook: int) -> bytes:
    """The 32-byte copy routine the stub pushes: original ended `lea $5c(a7),a7 ; rts` after patching its own return
    address; ours restores the same registers, lands on the same a7 as that `rts` did and `jmp hook`."""
    c = bytes.fromhex("12d8" "5380" "66fa"        # move.b (a0)+,(a1)+ ; subq.l #1,d0 ; bne  : copy the depacked game
                      "4219" "5381" "66fa"        # clr.b (a1)+ ; subq.l #1,d1 ; bne        : clear the tail
                      "4cef7fff0020"              # movem.l $20(a7),d0-d7/a0-a6             : the entry registers
                      "4fef0060"                  # lea $60(a7),a7                          : a7 as after the rts
                      "4ef9") + struct.pack(">I", hook) + bytes.fromhex("4e714e71")
    assert len(c) == 32
    return c


def push_code(c: bytes) -> bytes:
    """`move.l #imm,-(a7)` x8 building `c` on the stack (last pushed = lowest address)."""
    return b"".join(b"\x2f\x3c" + c[i:i + 4] for i in range(28, -1, -4))


def patched_text(path: str, push_off: int, hook: int | None) -> bytearray:
    text = bytearray(prg_text(path))
    if bytes(text[push_off:push_off + 50]) != PUSH_ORIG:
        raise SystemExit(f"{path}: the copy-routine pushes at text ${push_off:x} are not the expected original bytes")
    if hook is not None:
        text[push_off:push_off + 48] = push_code(stack_routine(hook))
    return text


def build_war(records: bytes, stage1: bool) -> tuple[bytes, bytes]:
    """New AUTO/WAR.PRG and the front stub bytes."""
    text = patched_text(WAR_PATH, PUSH1, HOOK1 if stage1 else None)
    if bytes(text[:8]) != FRONT_ORIG:
        raise SystemExit("WAR.PRG text does not start with the expected Super(0) call")
    text[0:8] = b"\x4e\xf9" + struct.pack(">I", TEXT_LEN) + b"\x4e\x71"
    front = core_segments()["front"]
    data = front + records
    hdr = bytearray(prg_file(WAR_PATH)[:HDR])
    struct.pack_into(">I", hdr, 6, len(data))
    return bytes(hdr) + bytes(text) + data + struct.pack(">I", 2) + b"\x00", front


def build_spr() -> bytes:
    """DATA/SPRITE40.DAT (stage 2) with its copy routine ending in `jmp hook2`: same size, so the FAT is untouched."""
    f = bytearray(prg_file(SPR_PATH))
    f[HDR:HDR + SPR_TEXT_LEN] = patched_text(SPR_PATH, PUSH2, HOOK2)
    return bytes(f)


# ---- commands ---------------------------------------------------------------------------------------------------------
def selected(patches, only):
    if only:
        names = {p.name for p in patches}
        bad = [n for n in only if n not in names]
        if bad:
            raise SystemExit(f"unknown patch(es): {bad}; have {sorted(names)}")
        return [p for p in patches if p.name in only]
    return [p for p in patches if p.default]


def check_resident() -> bool:
    ok = True
    for stage, base, dump in ((1, BASE1, ENTRY_DUMPS[1]), (2, BASE2, ENTRY_DUMPS[2])):
        try:
            res = resident_image(stage)
        except Exception as e:                # noqa: BLE001
            print(f"stage {stage} resident image: FAILED to derive: {e}")
            ok = False
            continue
        print(f"stage {stage} resident image: {len(res)} bytes ${base:x}..${base + len(res) - 1:x} "
              f"(depacked + relocated from {WAR_PATH if stage == 1 else SPR_PATH})")
        if dump.exists():
            d = dump.read_bytes()
            diff = sum(1 for a, b in zip(d[base:base + len(res)], res) if a != b)
            print(f"  vs RAM dump at the hand-over ({dump.name}): {diff} differing bytes")
            ok = ok and diff == 0
        else:
            print(f"  (no RAM dump {dump.name}: not checked against RAM)")
    return ok


def cmd_verify(patches) -> int:
    bad = 0
    if not check_resident():
        bad += 1
    for path, off in ((WAR_PATH, PUSH1), (SPR_PATH, PUSH2)):
        patched_text(path, off, None)
    prg_text(WAR_PATH)
    print("stubs: both copy-routine pushes and WAR.PRG's Super(0) call match the expected original bytes")
    core_segments()
    stack_routine(HOOK2)
    for p in patches:
        if p.site is None:
            continue
        try:
            orig, new = resolve(p)
            print(f"  ok   {p.name:18s} stage {p.stage} ${p.site:06x} {len(orig):3d} B  {orig.hex()} -> {new.hex()}")
        except SystemExit as e:
            bad += 1
            print(f"  FAIL {p.name}: {e}")
    if bad:
        print(f"{bad} problem(s)")
    return 1 if bad else 0


def cmd_list(patches):
    core = core_segments()
    print(f"core: front {len(core['front'])} B (data segment of WAR.PRG), payload ${IMG_BASE:x}..${IMG_END - 1:x}; "
          f"entry {len(core['entry'])} B, hook1 {len(core['hook1'])} B, hook2 {len(core['hook2'])} B, apply {len(core['apply'])} B, table ${TABLE:x}..${TABLE_END - 1:x}, "
          f"FLAGS ${FLAGS:x}, MARKER ${MARKER:x}")
    print(f"  {'name':20s} {'stage':5s} {'site':8s} {'len':>4s} {'blob':>6s} {'data':>6s}  flags")
    for p in patches:
        site = f"${p.site:06x}" if p.site is not None else "-"
        blob = sum(len(assemble(o, l, "\n".join(p.preamble))) for o, l in p.segments if o != p.site) if p.segments else 0
        n = len(site_bytes(p)) if p.site is not None else 0
        fl = ("default " if p.default else "") + ("mandatory " if p.mandatory else "") + ("init " if p.inits else "") + ("uinit" if p.uinits else "")
        print(f"  {p.name:20s} {p.stage if p.site is not None else '-':>5} {site:8s} {n:4d} {blob:6d} {sum(l for _, l in p.data):6d}  {fl}")


def read_samples(path):
    return Path(path).read_bytes() if path else None


def late_records(flat: bytes, used, zeros) -> bytes:
    """DATA-folder file PMLATE.DAT of the HD build (hd_core.s): the payload bytes inside HD_WINDOW, as records {dest.l, len.l
    [bit 31 = zero fill], bytes} and a terminating {0, 0}.  Stage 1's DATA\\SPRITE40.DAT is read into that window (its destination
    is inside TOS's low-RAM region, so it cannot be read in place) and hd_load reads these records back straight after the plain
    copy of the file to its destination, i.e. before the game proper exists and before any init or patch of stage 2 runs.
    Only the used spans are written (no merging): the free RAM around them must keep whatever it held (free-RAM proof).
    The records are checked by applying them to an image of the window as the overlay leaves it."""
    lo, hi = HD_WINDOW
    zset = sorted(zeros)
    recs = bytearray()
    for a, b in sorted(used):
        a, b = max(a, lo), min(b, hi)
        if b <= a:
            continue
        zero = any(z0 <= a and b <= z1 for z0, z1 in zset)
        if not zero and any(a < z1 and z0 < b for z0, z1 in zset):
            raise SystemExit(f"used span ${a:x}-${b - 1:x} is only partly a zero-fill span: cannot restore it")
        if zero:
            recs += struct.pack(">II", a, 0x80000000 | (b - a))
        else:
            recs += struct.pack(">II", a, b - a) + flat[a - IMG_BASE:b - IMG_BASE]
    recs += struct.pack(">II", 0, 0)
    # assertion: the overlay is dead before anything of the payload is used again.  Simulate: window full of file bytes (0xEE),
    # apply the records, compare with the payload as `front` leaves it (used spans = flat bytes / zero for data spans).
    sim = bytearray(b"\xee" * (hi - lo))
    i = 0
    while True:
        dest, ln = struct.unpack_from(">II", recs, i)
        i += 8
        if dest == 0:
            break
        if ln & 0x80000000:
            ln &= 0x7FFFFFFF
            sim[dest - lo:dest - lo + ln] = bytes(ln)
        else:
            sim[dest - lo:dest - lo + ln] = recs[i:i + ln]
            i += ln
    for a, b in used:
        a, b = max(a, lo), min(b, hi)
        for x in range(a, b):
            want = 0 if any(z0 <= x < z1 for z0, z1 in zset) else flat[x - IMG_BASE]
            if sim[x - lo] != want:
                raise SystemExit(f"PMLATE.DAT does not restore ${x:x}")
    return bytes(recs)


def build_floppy(out: Path, img: bytes, patches):
    prg, front = build_war(img, any(p.stage == 1 for p in patches))
    fat = Fat12(disk_image())
    before = fat.free_bytes()
    nclu = fat.write_file(WAR_PATH, prg)
    fat.write_file(SPR_PATH, build_spr())
    out.mkdir(parents=True, exist_ok=True)
    (out / "powermonger.st").write_bytes(bytes(fat.d))
    print(f"floppy: {out / 'powermonger.st'}  WAR.PRG {len(prg)} B ({nclu} clusters), free on disk {before} -> {fat.free_bytes()} B")


def hd_equs() -> dict[str, int]:
    """The equates of patches/hd_core.s, checked against the shared constants of this file (swap buffer, overlay window)."""
    e = {}
    for line in (PATCHDIR / "hd_core.s").read_text().splitlines():
        m = re.match(r"^(\w+)\s+equ\s+\$([0-9a-fA-F]+)\s*(;.*)?$", line)
        if m:
            e[m.group(1)] = int(m.group(2), 16)
    if not (e["SBASE"] == HD_SWAP_BASE and e["SBASE"] + e["SMAX"] == HD_SWAP_END and e["OVL"] == HD_WINDOW[0]
            and e["OVL"] + e["OVLMAX"] == HD_WINDOW[1]):
        raise SystemExit("hd_core.s SBASE/SMAX/OVL/OVLMAX do not match HD_SWAP_BASE/HD_SWAP_END/HD_WINDOW in pmpatch.py")
    return e


def build_hd(out: Path, img: bytes, patches, late: bytes):
    """A GEMDOS folder: AUTO\\WAR.PRG (same carrier), DATA\\*.DAT extracted from the disk image (SPRITE40.DAT patched) and
    the initial save-game disk SAVEDISK.DAT; the hd_* patches replace the game's FAT12/FDC code by GEMDOS calls."""
    prg, front = build_war(img, any(p.stage == 1 for p in patches))
    fat = Fat12(disk_image())
    hd_equs()
    if len(build_spr()) > HD_WINDOW[1] - HD_WINDOW[0]:
        raise SystemExit(f"DATA\\SPRITE40.DAT ({len(build_spr())} B) does not fit the overlay window ${HD_WINDOW[0]:x}..${HD_WINDOW[1] - 1:x}")
    if out.exists():
        shutil.rmtree(out)
    (out / "AUTO").mkdir(parents=True)
    (out / "DATA").mkdir()
    (out / "AUTO" / "WAR.PRG").write_bytes(prg)
    names = []
    first = fat.find("DATA")[3]
    for _o, name, attr, start, size in fat.dir_entries(first):
        if attr & 0x18 or name[:1] == b".":
            continue
        fn = name[:8].decode().strip() + "." + name[8:].decode().strip()
        data = build_spr() if fn.upper() == "SPRITE40.DAT" else fat.read(start, size)
        (out / "DATA" / fn).write_bytes(data)
        names.append(fn)
    save = bytearray(800 * 512)                            # a freshly formatted save disk: sector 0 = the game's own block
    blk = resident_bytes(2, 0x1BB0E, 512)
    if blk is None or blk[:4] != b"POWE":
        raise SystemExit("save-disk boot block at $1bb0e not found in the stage 2 image")
    save[:512] = blk
    (out / "SAVEDISK.DAT").write_bytes(bytes(save))
    (out / "PMLATE.DAT").write_bytes(late)
    print(f"hd: {out}  AUTO/WAR.PRG {len(prg)} B, DATA/ {len(names)} files, SAVEDISK.DAT {len(save)} B, PMLATE.DAT {len(late)} B")


def cmd_build(patches, out: Path, floppy: bool, hd: bool, samples, corrupt, all_patches):
    hdp = [p for p in all_patches if p.name.startswith("hd_")]
    if cmd_verify(patches + [p for p in hdp if p not in patches]):
        raise SystemExit("verify failed; no build")
    both = not floppy and not hd
    fpatches = [p for p in patches if not p.name.startswith("hd_")]
    hpatches = fpatches + hdp
    for kind, want, plist in (("floppy", floppy or both, fpatches), ("hd", hd or both, hpatches)):
        if not want:
            continue
        flat, sites, used, zeros = build_image(plist, samples, corrupt=corrupt, hd=(kind == "hd"))
        img = pack_records(flat, zeros)
        print(f"{kind}: payload ${IMG_BASE:x}..${IMG_BASE + len(flat) - 1:x} stored as {len(img)} B of records, {len(sites)} site(s)")
        if kind == "floppy":
            build_floppy(out / kind, img, plist)
        else:
            build_hd(out / kind, img, plist, late_records(flat, used, zeros))
        man = dict(kind=kind, patches=[p.name for p in plist], image_base=IMG_BASE, image_len=len(flat), records_len=len(img),
                   used=[[a, b] for a, b in used],
                   sites=[dict(name=s["name"], stage=s["stage"], addr=s["addr"], orig=s["orig"].hex(), new=s["new"].hex())
                          for s in sites])
        (out / f"{kind}.json").write_text(json.dumps(man, indent=1))
        for s in sites:
            print(f"  stage {s['stage']} ${s['addr']:06x} {len(s['orig']):4d} {s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]")


def cmd_live(patches, out: Path, samples, ste=True):
    """Payload image + site bytes for applying a patch set to a restored snapshot (stharness capture_frames(live=)):
    <out>.img at IMG_BASE with FLAGS/MARKER set, <out>.json with the sites (the hook and the front stub are omitted)."""
    patches = [p for p in patches if p.stage == 2 and not p.name.startswith("hd_")]
    img, sites, _, _z = build_image(patches, samples)
    img = bytearray(img)
    struct.pack_into(">I", img, FLAGS - IMG_BASE, 3 if ste else 6)
    img[MARKER - IMG_BASE:MARKER - IMG_BASE + 4] = b"PMPO"
    out.parent.mkdir(parents=True, exist_ok=True)
    Path(str(out) + ".img").write_bytes(bytes(img))
    Path(str(out) + ".json").write_text(json.dumps(dict(
        img_base=IMG_BASE, flags=3 if ste else 6,
        sites=[dict(name=s["name"], addr=s["addr"], orig=s["orig"].hex(), new=s["new"].hex()) for s in sites]), indent=1))
    print(f"live: {out}.img ({len(img)} B at ${IMG_BASE:x}), {out}.json ({len(sites)} sites), FLAGS={3 if ste else 6}")


# ---- cold-boot test (uses the harness; work/notes/loading.md section 8) ------------------------------------------------
def make_pm(disk: Path | None, hd: Path | None, acsi: bool = False, **kw):
    """A PM harness instance: floppy image in A: (disk) or a GEMDOS folder as C: (hd).  Its `key('space')` (the harness
    presses it every 4 s to skip the intro) is suppressed once the game proper has been entered ($10A6 holds `lea.l`):
    a key byte that arrives in the few frames between the game's ACIA reset (pc $10e6) and its enabling of the keyboard
    interrupt leaves the ACIA's IRQ line asserted for good (the MFP only reacts to the edge), and the game then never
    sees a key.  With the slow floppy loads that window is never hit by the 4 s period; with the fast HD loads it was."""
    sys.path.insert(0, str(HERE))
    import pm  # noqa: E402
    h = _make_pm(pm, disk, hd, acsi, **kw)
    orig_key = h.key

    def key(keysym, hold=0.15):
        if keysym == "space" and h.peekw(0x10A6) == 0x41F9:
            return
        orig_key(keysym, hold)

    h.key = key
    orig_peekw = h.peekw

    def peekw(addr):                  # the debugger's answer can come late on a loaded host: ask again
        for _ in range(8):
            try:
                return orig_peekw(addr)
            except IndexError:
                time.sleep(1.0)
        return orig_peekw(addr)

    h.peekw = peekw
    return h


def _make_pm(pm, disk, hd, acsi=False, **kw):
    if hd is None:
        return pm.PM(disk=disk or pm.DISK, **kw)

    class HDPM(pm.PM):
        def __init__(self, folder: Path, **kw2):
            R = Path(tempfile.mkdtemp(prefix="strun-"))
            home = R / "home"
            (home / ".config/hatari").mkdir(parents=True, exist_ok=True)
            txt = (Path.home() / ".config/hatari/hatari.cfg").read_text()
            txt = re.sub(r"(?m)^szMemoryCaptureFileName = .*$", f"szMemoryCaptureFileName = {R}/state.sav", txt)
            (home / ".config/hatari/hatari.cfg").write_text(txt)
            kw2.setdefault("overlay", Path("/nonexistent"))
            kw2.setdefault("autorun", None)
            extra = list(kw2.pop("extra", []))
            if acsi:        # a real ACSI disk with HDDRIVER (hd/README.md): TOS's own GEMDOS + driver, no GEMDOS emulation
                sys.path.insert(0, str(BENCH / "games" / "hunter" / "tools"))
                import hunter  # noqa: E402
                hunter.build_hd(R / "hd.img", game=folder, autorun="C:\\NONE.TOS")
                extra += ["--gemdos-drive", "skip", "--acsi", f"0={R / 'hd.img'}"]
                kw2["files"] = []
            if kw2.get("snapshot"):      # a memstate made by a run of the same kind: its scratch paths are retargeted to this one
                snap_in = R / "snap_in.sav"
                pm.retarget_snapshot(kw2["snapshot"], snap_in, R)
                kw2["snapshot"] = str(snap_in)
            old = os.environ.get("HOME")
            os.environ["HOME"] = str(home)
            try:
                pm.Hatari.__init__(self, game_dir=folder, workdir=str(R), extra=extra, **kw2)
            finally:
                os.environ["HOME"] = old
            self.state = R / "state.sav"

    return HDPM(hd, **kw)


def free_spans(manifest: Path):
    """[(lo, hi)) inside $B8800..$EFFFF not used by the payload of that build."""
    used = sorted(tuple(u) for u in json.loads(manifest.read_text())["used"])
    spans, cur = [], IMG_BASE + 0x800
    for lo, hi in used:
        if hi <= cur:
            continue
        if lo > cur:
            spans.append((cur, min(lo, IMG_END)))
        cur = max(cur, hi)
    if cur < IMG_END:
        spans.append((cur, IMG_END))
    return [(lo, hi) for lo, hi in spans if hi > lo]


def fill_report(name: str, d: bytes, spans, swap: tuple[int, int] | None = None) -> bool:
    n = bad = 0
    runs = []
    for lo, hi in spans:
        for a in range(lo, hi):
            n += 1
            if d[a] != fill_byte(a):
                bad += 1
                if runs and a - runs[-1][1] <= 1:
                    runs[-1][1] = a
                else:
                    runs.append([a, a])
    pat = {a for lo, hi in spans if hi > IMG_END for a in range(max(lo, IMG_END), hi)}      # (HD: the part of $F0000.. that holds the pattern too)
    topnz = [a for a in range(IMG_END, 0xF7FC8) if d[a] and a not in pat and not (swap and swap[0] <= a < swap[1])]
    top = f"{len(topnz)}" + (f" at {[hex(a) for a in topnz[:8]]}" if topnz else "")
    print(f"  fill[{name}]: {n} pattern bytes in the free spans of ${IMG_BASE + 0x800:x}..${IMG_END - 1:x} (HD: and ${IMG_END:x}..${HD_SWAP_END - 1:x} beyond the swap buffer), {bad} changed"
          + (f" first runs {[(hex(x), hex(y)) for x, y in runs[:6]]}" if bad else "")
          + f"; ${IMG_END:x}..$f7fc7 non-zero bytes: {top}" + (f" (swap buffer spill ${swap[0]:x}..${swap[1] - 1:x} excluded)" if swap else ""))
    return bad == 0


REF = ROOT / "work" / "ref"
STATE = (0x3F768, 198 * 512)             # the game state a save slot holds (loading.md section 2.4): $c6 sectors at $3f768


def find_btn(h, ref: str, region=(96, 58, 736, 458), quiet: bool = False):
    """ST-pixel centre of the best match of work/ref/<ref> in the game screen of a screenshot, or None (a dialog of the game
    opens at a position that depends on the pointer, so buttons are found, not clicked at fixed places)."""
    import numpy as np
    from numpy.lib.stride_tricks import sliding_window_view
    from PIL import Image
    im0 = Image.open(h.shot())
    ox, oy = {832: (96, 58), 640: (0, 0), 648: (2, 64)}.get(im0.width, (96, 58))        # ST / TT / Falcon screenshots
    region = (region[0] - 96 + ox, region[1] - 58 + oy, region[2] - 96 + ox, region[3] - 58 + oy)
    img = np.asarray(im0.convert("L"), dtype=np.int16)
    tpl = np.asarray(Image.open(REF / ref).convert("L"), dtype=np.int16)
    th, tw = tpl.shape
    x0, y0, x1, y1 = region
    sub = img[y0:y1, x0:x1]
    best = (1e9, None)
    for ys in range(0, sub.shape[0] - th + 1, 40):
        win = sliding_window_view(sub[ys:min(ys + 40 + th - 1, sub.shape[0])], (th, tw))
        d = np.abs(win - tpl).mean(axis=(2, 3))
        i = np.unravel_index(np.argmin(d), d.shape)
        if d[i] < best[0]:
            best = (float(d[i]), (x0 + i[1] + tw // 2, y0 + ys + i[0] + th // 2))
    if best[0] > 12.0:
        if not quiet:
            print(f"  find_btn: {ref} not found (best match {best[0]:.1f})")
            shutil.copy(h.shot(), f"/tmp/pm_find_{ref}")
        return None
    return (int(best[1][0] - ox) // 2, int(best[1][1] - oy) // 2)


def file_dialog(h, button: str, arm=None):
    """Option symbol -> FILE -> `button` (pm_btn_load.png / pm_btn_save.png): the game's own save / load menu, slot A.  `arm()` runs
    right before the last click (a conditional breakpoint slows the emulation down, so it is set as late as possible)."""
    for _try in range(3):
        h.click_st(72, 138, wait=2.0)                       # the Option symbol (top-left of the command panel)
        p = find_btn(h, "pm_btn_file.png")
        if p is None:
            continue
        h.click_st(*p, wait=2.0)
        p = find_btn(h, button)
        if p is not None:
            h.goto_st(*p)
            if arm:
                arm()
            h.click()
            time.sleep(1.0)
            return True
    return False


def run_saveload(h, acsi: bool) -> bool:
    """Save to slot A through the game's menu, let the game run, load slot A through the menu, and compare.  The state a slot
    holds ($3f768, $c6 sectors) is captured by the debugger at hd_sector's entry of the write (the buffer being written) and at
    the load call's return into the game ($1bdd8: right after the read, before the game touches it); the file on the disk
    (SAVEDISK.DAT in the ACSI image or the GEMDOS folder) is compared with it as well."""
    out = h.R / "sl"
    out.mkdir(exist_ok=True)
    lo, n = STATE
    for f in out.glob("*.bin"):
        f.unlink()
    n_ok = 0
    (h.R / "sv.txt").write_text(f"savebin {out}/save.bin ${lo:x} ${n:x}\n")
    if not file_dialog(h, "pm_btn_save.png", lambda: h.cmd(f"hatari-debug b pc = $bb00c && d3 = $8001 && d2 = $c6 :trace :once :file {h.R / 'sv.txt'}")):
        print("  saveload: the FILE / SAVE buttons were not found")
        return False
    t = time.time()
    while not (out / "save.bin").exists() or (out / "save.bin").stat().st_size < n:
        if time.time() - t > 90:
            print("  saveload: the save never reached hd_sector")
            return False
        time.sleep(1)
        p = find_btn(h, "pm_btn_ok.png", quiet=True)        # the game asks before it overwrites a slot that is in use
        if p is not None and n_ok < 3:
            n_ok += 1
            h.click_st(*p, wait=1.0)
    time.sleep(5)                                           # the game runs on: the state moves away from the saved one
    h.debug(f"savebin {out}/pre.bin ${lo:x} ${n:x}", 3.0)
    (h.R / "l2.txt").write_text(f"savebin {out}/load.bin ${lo:x} ${n:x}\n")
    (h.R / "l1.txt").write_text(f"b pc = $1bdd8 :trace :once :file {h.R / 'l2.txt'}\n")
    if not file_dialog(h, "pm_btn_load.png", lambda: h.cmd(f"hatari-debug b pc = $bb00c && d3 = $8000 && d2 = $c6 :trace :once :file {h.R / 'l1.txt'}")):
        print("  saveload: the FILE / LOAD buttons were not found")
        return False
    t = time.time()
    while not (out / "load.bin").exists() or (out / "load.bin").stat().st_size < n:
        if time.time() - t > 60:
            print("  saveload: the load never returned")
            return False
        time.sleep(1)
    time.sleep(2)
    sv, pre, ld = ((out / f"{k}.bin").read_bytes() for k in ("save", "pre", "load"))
    d_sl = sum(a != b for a, b in zip(sv, ld))
    d_sp = sum(a != b for a, b in zip(sv, pre))
    if acsi:
        sd = subprocess.run(["mcopy", "-i", f"{h.R / 'hd.img'}@@{2 * 512}", "::SAVEDISK.DAT", str(out / "sd.dat")], capture_output=True,
                            env=dict(os.environ, MTOOLS_SKIP_CHECK="1"))
        disk = (out / "sd.dat").read_bytes() if sd.returncode == 0 else b""
    else:
        f = h.R / "C" / "SAVEDISK.DAT"
        disk = f.read_bytes() if f.exists() else b""
    d_disk = disk[512:512 + n] == sv
    ok = d_sl == 0 and d_sp > 0 and d_disk and len(disk) == 800 * 512 and disk[:4] == b"POWE"
    print(f"  saveload: state {n} B; saved vs loaded: {d_sl} differ; saved vs the state just before the load: {d_sp} differ; "
          f"SAVEDISK.DAT slot A == saved: {d_disk} ({len(disk)} B); game iterates: {h.in_game()}")
    return ok and h.in_game()



def run_call(h, addr: int) -> bool:
    """Run the test routine at `addr` (patches/test_hdsav.s) from the main loop via the debugger, then check the results it
    left at $CFFF0.. and the host copy of SAVEDISK.DAT."""
    (h.R / "call.txt").write_text(f"r pc=${addr:x}\n")
    h.cmd(f"hatari-debug b pc = $13020 :trace :once :file {h.R / 'call.txt'}")
    t = time.time()
    while h.peekl(0xCFFEC) != int.from_bytes(b"DONE", "big"):
        if time.time() - t > 90:
            print("  call: the test routine did not finish")
            return False
        time.sleep(2)
    res = {n: h.peekl(a) for n, a in (("write", 0xCFFF0), ("read", 0xCFFF4), ("compare", 0xCFFF8), ("sector0", 0xCFFFC), ("format", 0xCFFE8))}
    pat = b"".join(struct.pack(">I", 0x50414C31 + i) for i in range(256))
    f = h.R / "C" / "SAVEDISK.DAT"
    host = f.read_bytes() if f.exists() else b""
    ok_host = host[5 * 512:7 * 512] == pat and len(host) == 800 * 512 and host[:4] == b"POWE"
    print(f"  call ${addr:x}: {res}  host SAVEDISK.DAT {len(host)} B, sectors 5-6 hold the pattern: {host[5 * 512:7 * 512] == pat}")
    return all(v == 0 for v in res.values()) and ok_host


def cmd_boot(disk, hd, machine, tos, mem, shots, peeks, dump, stop_at_title=False, fill=None, scenario=False, peeks1=None, call=None,
             acsi=False, saveload=False):
    sys.path.insert(0, str(HERE))
    import pm  # noqa: E402
    h = None
    try:
        h = make_pm(disk, hd, acsi=acsi, machine=machine, tos=pm.TOS[tos], memsize_kb=mem)
        spans = []
        if fill:
            spans = free_spans(Path(fill))
            if hd is not None:      # the swap buffer may spill past $EFFFF (hd_core.s SMAX): prove the rest of $F0000..$F5FFF free as well
                t = time.time()
                while h.peekl(0xBC000) != int.from_bytes(b"HDSW", "big"):      # hd_core `init` has run (long before the stage 2 hand-over)
                    if time.time() - t > 120:
                        raise TimeoutError("hd_core init never set READY")
                    time.sleep(2)
                s_end = (HD_SWAP_BASE + h.peekl(0xBC008) + 3) & ~3
                if s_end < HD_SWAP_END:
                    spans.append((max(s_end, IMG_END), HD_SWAP_END))
            lines = []
            for i, (lo, hi) in enumerate(spans):
                f = h.R / f"f{i}.bin"
                f.write_bytes(bytes(fill_byte(a) for a in range(lo, hi)))
                lines.append(f"loadbin {f} ${lo:x}")
            (h.R / "fill.txt").write_text("\n".join(lines) + "\n")
            if hd is not None:      # the HD build reads stage 1's SPRITE40.DAT through the overlay window (hd_core.s): free bytes in it hold that
                                    # file afterwards by design, so its proof starts at the game's hand-over (the stage 1 half is the floppy's)
                base, first, what = BASE2, 0x41F9, "stage 2"
            else:
                base, first, what = BASE1, 0x4EB9, "stage 1"
            h.cmd(f"hatari-debug b pc = ${base:x} && (${base:x}).w = ${first:x} :trace :once :file {h.R / 'fill.txt'}")
            print(f"  fill armed at the {what} hand-over: {len(spans)} span(s), {sum(hi - lo for lo, hi in spans)} bytes")
        if peeks1:
            (h.R / "peek1.txt").write_text("".join(f"m ${pk.partition(':')[0].lstrip('$')} {pk.partition(':')[2] or 8}\n" for pk in peeks1))
            h.cmd(f"hatari-debug b pc = $1360 :trace :once :file {h.R / 'peek1.txt'}")      # stage 1's `jmp $1008.w`, after its load
        if stop_at_title:
            time.sleep(120)
            for _ in range(3):
                h.key("space")
                time.sleep(4)
        else:
            h.boot_to_game()
        mk = h.peekl(MARKER).to_bytes(4, "big")
        print(f"BOOT OK machine={machine} tos={tos} mem={mem}K  in_game={h.in_game() if not stop_at_title else None}  "
              f"MARKER={mk!r}  FLAGS={h.peekl(FLAGS):#x}")
        for pk in peeks or []:
            a, _, n = pk.partition(":")
            aa = int(a.lstrip("$"), 16)
            print(f"  peek ${aa:x}: {h.ram(aa, int(n or 8)).hex()}")
        ok = True
        if peeks1:
            txt = h._logtext()
            i = txt.find("Reading debugger commands from '" + str(h.R / "peek1.txt"))
            print("  peek at the stage 1 hand-over to stage 2 (pc $1360):" + ("" if i >= 0 else " breakpoint never fired"))
            for ln in txt[i:].splitlines()[1:10] if i >= 0 else []:
                if re.match(r"^[0-9A-F]{8}:", ln) or ln.startswith("> m "):
                    print("   ", ln)
        if call:
            ok &= run_call(h, call)
        if saveload:
            ok &= run_saveload(h, acsi)
        swap = None
        if fill and hd is not None:
            rlen = h.peekl(0xBC008)                       # hd_core.s RLEN: the swap buffer's length in this run
            swap = (HD_SWAP_BASE, HD_SWAP_BASE + rlen)
            print(f"  HD swap buffer: R = [$8, ${8 + rlen:x}) = {rlen} B at ${HD_SWAP_BASE:x}..${HD_SWAP_BASE + rlen - 1:x}, READY={h.peekl(0xBC000).to_bytes(4, 'big')!r}")
        if fill:
            ok &= fill_report("map view", h.ram(0, 0x100000), spans, swap)
        if scenario:
            n = h.scenario_get_men()
            print(f"  get_men: {n} people moving")
            if fill:
                ok &= fill_report("get_men", h.ram(0, 0x100000), spans, swap)
            t = time.time()
            while h.iter_count() < 340 and time.time() - t < 240:
                time.sleep(5)
            print(f"  battle: iteration {h.iter_count()}, MARKER={h.peekl(MARKER).to_bytes(4, 'big')!r}")
            if fill:
                ok &= fill_report("battle", h.ram(0, 0x100000), spans, swap)
        if dump:
            Path(dump).parent.mkdir(parents=True, exist_ok=True)
            Path(dump).write_bytes(h.ram(0, 0x100000))
            print(f"  dumped RAM $0..$fffff to {dump}")
        if shots:
            Path(shots).mkdir(parents=True, exist_ok=True)
            h.shot(str(Path(shots) / f"{machine}_{tos}_{mem}.png"))
        return 0 if ok else 2
    except Exception as e:                      # noqa: BLE001
        print(f"BOOT FAILED machine={machine} tos={tos} mem={mem}K: {e!r}")
        import traceback
        traceback.print_exc()
        if h is not None:
            try:
                print(f"  MARKER={h.peekl(MARKER).to_bytes(4, 'big')!r} FLAGS={h.peekl(FLAGS):#x}")
                if shots:
                    Path(shots).mkdir(parents=True, exist_ok=True)
                    h.shot(str(Path(shots) / f"fail_{machine}_{tos}_{mem}.png"))
            except Exception:                   # noqa: BLE001
                pass
        return 1
    finally:
        if h is not None:
            h.close()


def cmd_dumps() -> int:
    """Regenerate work/dumps/entry576.bin and entry10a6.bin: cold boot of the ORIGINAL disk, 1 MB STE / TOS 1.62, RAM saved at
    each hand-over (Hatari breakpoints pc = $576 && ($576).w = $4eb9 and pc = $10a6 && ($10a6).w = $41f9)."""
    sys.path.insert(0, str(HERE))
    import pm  # noqa: E402
    h = make_pm(None, None, machine="ste", tos=pm.TOS["1.62"], memsize_kb=1024)
    try:
        ENTRY_DUMPS[1].parent.mkdir(parents=True, exist_ok=True)
        for st in (1, 2):
            ENTRY_DUMPS[st].unlink(missing_ok=True)
        for st, base, first in ((1, BASE1, 0x4EB9), (2, BASE2, 0x41F9)):
            (h.R / f"d{st}.txt").write_text(f"savebin {ENTRY_DUMPS[st]} 0 $100000\n")
            h.cmd(f"hatari-debug b pc = ${base:x} && (${base:x}).w = ${first:x} :trace :once :file {h.R / f'd{st}.txt'}")
        t = time.time()
        while not ENTRY_DUMPS[2].exists() or ENTRY_DUMPS[2].stat().st_size < 0x100000:
            if time.time() - t > 300:
                raise TimeoutError("stage 2 hand-over not reached")
            h.key("space")
            time.sleep(4)
        time.sleep(2)
        print(f"wrote {ENTRY_DUMPS[1]} and {ENTRY_DUMPS[2]}")
        return 0
    finally:
        h.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify")
    sub.add_parser("list")
    sub.add_parser("dumps")
    b = sub.add_parser("build")
    b.add_argument("--only", nargs="*", default=None)
    b.add_argument("--floppy", action="store_true")
    b.add_argument("--hd", action="store_true")
    b.add_argument("--out", default=str(BUILD))
    b.add_argument("--samples")
    b.add_argument("--corrupt", action="store_true")
    lv = sub.add_parser("live")
    lv.add_argument("--only", nargs="*", default=None)
    lv.add_argument("--out", default=str(BUILD / "live" / "patches"))
    lv.add_argument("--samples")
    lv.add_argument("--no-ste", action="store_true")
    bo = sub.add_parser("boot")
    bo.add_argument("--disk")
    bo.add_argument("--hd")
    bo.add_argument("--acsi", action="store_true", help="with --hd: boot a real ACSI disk image with HDDRIVER (needs gamebench/hd/) instead of Hatari's GEMDOS folder")
    bo.add_argument("--machine", default="ste")
    bo.add_argument("--tos", default="1.62")
    bo.add_argument("--mem", type=int, default=1024)
    bo.add_argument("--shots")
    bo.add_argument("--peek", action="append")
    bo.add_argument("--peek1", action="append", help="ADDR:LEN read at stage 1's last instruction (`jmp $1008.w` at $1360)")
    bo.add_argument("--call", help="run the routine at ADDR from the main loop (HD save-disk self-test, test_hdsav)")
    bo.add_argument("--dump")
    bo.add_argument("--title", action="store_true", help="only reach the title/intro (no game navigation)")
    bo.add_argument("--fill", help="manifest (build/<kind>.json): load a position-dependent pattern into every unused byte of $B8800..$EFFFF "
                                   "at the stage 1 hand-over and compare it afterwards (free-RAM proof)")
    bo.add_argument("--saveload", action="store_true", help="after the map view: save to slot A through the game's own menu, load it back, compare "
                                                            "(needs work/ref/pm_btn_{file,load,save}.png)")
    bo.add_argument("--scenario", action="store_true", help="after the map view: get_men, then wait for the battle (iteration 340)")
    a = ap.parse_args()
    patches = load_all()
    if a.cmd == "verify":
        sys.exit(cmd_verify(patches))
    elif a.cmd == "list":
        cmd_list(patches)
    elif a.cmd == "dumps":
        sys.exit(cmd_dumps())
    elif a.cmd == "build":
        cmd_build(selected(patches, a.only), Path(a.out), a.floppy, a.hd, read_samples(a.samples), a.corrupt, patches)
    elif a.cmd == "live":
        cmd_live(selected(patches, a.only), Path(a.out), read_samples(a.samples), not a.no_ste)
    elif a.cmd == "boot":
        sys.exit(cmd_boot(Path(a.disk) if a.disk else None, Path(a.hd) if a.hd else None, a.machine, a.tos, a.mem,
                          a.shots, a.peek, a.dump, a.title, a.fill, a.scenario, a.peek1, hx(a.call) if a.call else None, a.acsi, a.saveload))


if __name__ == "__main__":
    main()
