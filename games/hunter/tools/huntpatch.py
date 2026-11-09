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

PATCHDIR = ROOT / "patches"
BUILD = ROOT / "build"
VASM = "vasmm68k_mot"
TAILDUMP = ROOT / "work" / "dumps" / "boot" / "ram_tail_1mb.bin"    # 1 MB STE, TOS 1.62, at START's final `jmp $800.w`
GAMEDUMP = ROOT / "work" / "dumps" / "boot" / "ram_game.bin"        # same machine, in the 3D view
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
    if "vol" not in _cache:
        offs, _ = decode_reloc(start_program()[28 + START_TEXT:])
        vol = [(HOOK_RAM + o - HOOK_SRC, HOOK_RAM + o - HOOK_SRC + 4) for o in offs if HOOK_SRC <= o and o + 4 <= HOOK_SRC + HOOK_LEN]
        vol += [(HOOK_RAM + (a - START_BASE) - HOOK_SRC, HOOK_RAM + (a - START_BASE) - HOOK_SRC + 4) for a in RUNTIME_OPERANDS]
        _cache["vol"] = sorted(set(vol))
    return _cache["vol"]


def tail_ram() -> dict[int, bytes]:
    """What RAM holds at START's final `jmp $800.w`, rebuilt from the shipped files (checked against the dump)."""
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
        if f.name == "core.s":
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
    d = TAILDUMP.read_bytes()
    ok = True
    vol = volatile_ranges()
    for base, b in tail_ram().items():
        n = sum(1 for i in range(len(b)) if not any(a <= base + i < z for a, z in vol))
        eq = all(d[base + i] == b[i] for i in range(len(b)) if not any(a <= base + i < z for a, z in vol))
        print(f"tail image ${base:05x}..${base + len(b):05x} ({len(b)} B, {n} compared) vs {TAILDUMP.name}: "
              f"{'IDENTICAL' if eq else 'DIFFERS'}")
        ok &= eq
    print("  machine-dependent (volatile) operands, not patchable: " + " ".join(f"${a:x}+4" for a, _z in vol))
    return ok


def cmd_verify(patches, fps=()) -> int:
    bad = 0
    if not check_tail_image():
        bad += 1
    core_segments()
    d = TAILDUMP.read_bytes()
    g = GAMEDUMP.read_bytes()
    for p in patches:
        try:
            orig, new = resolve(p)
        except SystemExit as e:
            print(f"{p.name:18s} site ${p.site:05x}: {e}")
            bad += 1
            continue
        src = "START tail RAM" if p.load is None else f"{p.load[0]} @ ${p.load[1]:x}"
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


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--only", nargs="*", default=None)
    b.add_argument("--out", default="build/game")
    b.add_argument("--samples", default=None, help="raw sample bank bytes placed at $90000 (max 126976 B)")
    b.add_argument("--fill", action="store_true", help="fill every unused payload byte with a pattern (free-RAM proof)")
    b.add_argument("--corrupt", action="store_true", help="TEST ONLY: corrupt the first orig byte in the payload (expects HNPF)")
    lv = sub.add_parser("live")
    lv.add_argument("--only", nargs="*", default=None)
    lv.add_argument("--out", default="build/live/patches")
    lv.add_argument("--samples", default=None)
    lv.add_argument("--no-ste", action="store_true", help="set FLAGS as a plain ST (default: STE)")
    sub.add_parser("list")
    sub.add_parser("verify")
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
    td.add_argument("--out", default=str(TAILDUMP))
    fc = sub.add_parser("fillcheck")
    fc.add_argument("dump")
    fc.add_argument("--manifest", default="build/game.json")
    a = ap.parse_args()
    patches, fps = load_all()
    if a.cmd == "list":
        cmd_list(patches, fps)
    elif a.cmd == "verify":
        sys.exit(cmd_verify(patches, fps))
    elif a.cmd == "boot":
        sys.exit(cmd_boot(ROOT / a.game, a.machine, a.tos, a.mem, ROOT / a.shots if a.shots else None, a.peek, a.dump, a.play))
    elif a.cmd == "taildump":
        sys.exit(cmd_taildump(Path(a.out)))
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
        if a.cmd == "build":
            cmd_build(sel, fsel, ROOT / a.out, smp, a.fill, a.corrupt)
        else:
            if fsel:
                raise SystemExit("file patches are applied at build time, not live")
            cmd_live(sel, ROOT / a.out, smp, not a.no_ste)


if __name__ == "__main__":
    main()
