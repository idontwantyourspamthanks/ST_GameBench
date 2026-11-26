#!/usr/bin/env python3
"""Moonshine Racers patch delivery tool (design: Midwinter 2 mw2patch.py / Populous 2 pop2patch.py, re-derived for PP's Moonshine Racers HAGA conversion).

Patches are vasm sources in patches/ (format and boot mechanism: patches/README.md).  The tool assembles them, verifies every site's expected ORIGINAL
bytes against the RAM of the unpatched game taken at the hook instant (work/dumps/ram_hook_1024.bin, 1 MB STE; cross-checked against
work/dumps/ram_entry_1024.bin, the same game at its first instruction), and writes a patched COPY of the game; originals are never touched.

    python3 tools/msrpatch.py list
    python3 tools/msrpatch.py verify
    python3 tools/msrpatch.py build [--only NAME ...] [--out DIR] [--zip [PATH]]      (default DIR build/hd; --only replaces the default set)
    python3 tools/msrpatch.py live  [--only NAME ...] [--out build/live/patches]     (payload image + site bytes for a running snapshot)
    python3 tools/msrpatch.py version [--credit]
    python3 tools/msrpatch.py doc FILE                                              (FILE with @VERSION@ / {PATCHES} filled in)

build: a game folder for a hard disk / GEMDOS drive: the patched RUNME.TOS (unpacked; payload appended to its data segment, two edit points), the
HAGA file (with the `; image: HAGA` file patches), and the original FILES\\, pictures and PP's texts.
live: <out>.img (payload image, load at IB = $B2700) + <out>.json (img_base, site bytes) for stharness.Hatari.capture_frames(live=...).
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
import zipfile
from pathlib import Path

ROOT = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers")
BENCH = ROOT.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
from pp_depack import depack as pp_depack  # noqa: E402

ORIG = ROOT / "originals" / "MOONSHR"
PATCHDIR = Path(__import__("os").environ.get("CF_PATCHDIR", str(ROOT / "patches")))
SET_OVERRIDES: dict[str, str] = {}   # `--set NAME=VALUE` (build/live): replaces the value of the `NAME equ ...` line a patch declares before its first `org` (e.g. mg_sync's `SAFE`, the extra-frame deadline margin)
SET_HELP = "override a patch's `NAME equ value` line (before its first org) for this build, e.g. --set SAFE=3 (mg_sync's deadline margin: + = stricter, fewer late ticks; play.sh --safex 3); an unknown NAME is an error"
DUMP_HOOK = ROOT / "work" / "dumps" / "ram_hook_1024.bin"     # 1 MB STE TOS 1.62, unpatched, at `pc = $b204e` (the hook instant)
DUMP_FLOPPY = ROOT / "work" / "floppy" / "ram_answered.bin"  # the original floppy after a correct answer (game loaded, about to start): floppy witness
DUMP_ENTRY = ROOT / "work" / "dumps" / "ram_entry_1024.bin"   # same game at `pc = $6f64` (first game instructions run; second witness)
# Stage 1 = the game's own loader (MSR_S1.FIC unpacked, RAM $78000-$7E3FF; on the floppy the tracks 1-5 side 0).  It draws the title picture
# ("Moonshine Racers" + hotrod) and loads the game while that picture is on screen, so it runs BEFORE the trampoline.  A patch with `; phase: stage1`
# has its site in that code: HD = applied by RUNME's copy routine right after the payload copy (before `jmp $78000`), floppy = a disk A edit of the
# stage-1 sectors (the payload is already in RAM: stage-0 loader of the boot sector).  Never `live` (a snapshot is long past stage 1).
STAGE1_BASE, STAGE1_LEN = 0x78000, 25600
STAGE1_TRACK_BYTES = 5120                  # floppy: stage 1 = tracks 1.. side 0, 10 sectors each, copied to $78000 (the boot sector's 6 x Floprd)


def stage1_image() -> bytes:
    """MSR_S1.FIC unpacked (PP's LZ, the stack-phase block's routine at RAM $B2220: header $20 B, then 0 = end, 1..$7f literal run, $80|n = n+3 bytes
    from a 1-byte offset, $c0|n = n+4 bytes from a 2-byte offset): the stage-1 loader as it stands at $78000 when RUNME's copy routine runs."""
    src = (ORIG / "FILES" / "MSR_S1.FIC").read_bytes()[0x20:]
    out = bytearray()
    i = 0
    while True:
        c = src[i]; i += 1
        if c == 0:
            break
        if c < 0x80:
            out += src[i:i + c]; i += c
            continue
        n = c & 0x3F
        if c & 0x40:
            n += 4; off = (src[i] << 8) | src[i + 1]; i += 2
        else:
            n += 3; off = src[i]; i += 1
        for _ in range(n):
            out.append(out[-off])
    if len(out) != STAGE1_LEN:
        raise SystemExit(f"MSR_S1.FIC unpacks to {len(out)} B, expected {STAGE1_LEN}")
    return bytes(out)
# the same stock game on a 1 MB Mega STE, TOS 2.06 (work/dumps, taken with tools/msrhook.py / work/mste/racedump.py): TOS 2.06 puts live GEM/AES data at $E2C50-$F7FFF
DUMPS_MSTE = ("ram_hook_1024_mste206.bin", "ram_entry_1024_mste206.bin", "ram_race0_1024_mste206.bin")
VASM = "vasmm68k_mot"

# ---- the payload image ---------------------------------------------------------------------------------------------------------------
IB = 0xB2700                      # payload image base: marker long at IB, trampoline at IB+8 .. IB+$FF
CORE = IB + 8
CORE_END = IB + 0x100
TABLE, TABLE_END = 0xB7000, 0xB8000    # site table + orig/new byte pool: 4 KB
FREE_END = 0xE2C00                # last free byte + 1 at 1 MB = the LOWER of the two 1 MB layouts: STE TOS 1.62 is zero to $E83FF, Mega STE TOS 2.06 only to $E2BFF (GEM/AES data from $E2C50, integration.md section 10.3)
BLOB_AREAS = ((0xB2800, TABLE), (TABLE_END, FREE_END))   # blob / data orgs allowed
IMG_MIN_END = TABLE_END           # the image always spans IB .. here (zero-padded); blobs above TABLE_END extend it
IMG_MAX_LEN = 0xF000              # RUNME's own limit on a 1 MB machine ("Too much low RAM occupied"); delivery.md section 6
# ---- the campaign feature (HD build, `; gate: ram2mb`, work/notes/campaign_hd.md): addresses shared by the cp_*.s sources (predefined for every source) ----------------
HIMEM_LO, HIMEM_END = 0x100000, 0x1CD000      # RAM above 1 MB that is zero and unused at 2 MB on an STE (TOS copy at $1D89B4) and a Mega STE (TOS copy at $1CD8BC): trackloader.md section 2
CP_EQUS = {"CPV": 0xB8E00,                    # campaign variables (in the payload image: zero at the trampoline), 32 bytes
           "CPTAB": 0x100000,                 # CRC-32 table (256 longs, built on every load)
           "CPWORK": 0x100400,                # menu scratch (item vectors, text)
           "CPSTORE": 0x110000}               # the campaign file as read (<= 128 KB; the format's maximum is 123,496 B)

# ---- RUNME edit points (text-relative offsets into the unpacked image) --------------------------------------------------------------------
TEXT_LEN = 0x4430
OLD_BSS = TEXT_LEN + 22           # end of the original data = start of the original bss
STAGE_TXT = 0x3B4                 # stack-phase block: `jmp $78000.l` (PP's stage 1 = MSR_S1.FIC unpacked), RAM $B1FA6 at 1 MB
STAGE_ORIG = bytes.fromhex("4ef900078000")
TAIL_TXT = 0x45C                  # PP's patcher tail `jmp $1000.w` (+ 16 B of zero padding, text $460-$46F), RAM $B204E at 1 MB
TAIL_ORIG = bytes.fromhex("4ef81000")
TAIL_PAD = bytes(2)               # the 2 padding bytes the 6-byte `jmp trampoline.l` takes over
STACK_TXT = 0x352                 # the stack-phase block text $352.. is copied to RAM (a3 = $B1F44 at 1 MB)
STACK_RAM = 0xB1F44
# `lea d(pc),aN` that address the bss: text offset -> (register, text-relative target).  The bss moves up by N when the data segment grows and a
# signed 16-bit displacement cannot span the payload, so each becomes `movea.l d(pc),aN` (same 4 bytes, same register, no flag change) loading a
# relocated pointer from slots behind the copy routine.  Found by a scan of the whole text for d16(pc) operands that reach >= OLD_BSS; the other hits
# (NOT_CODE) are displacement words of dbra/bne.
BSS_LEAS = {0x98: (1, 0x4666), 0xB34: (2, 0x4666), 0x40FA: (2, 0x4446), 0x410C: (1, 0x4446)}
BSS_PTR_TARGETS = (0x4666, 0x4446)
NOT_CODE = {0x4EA, 0x413A, 0x4302}
PTRS_LEN = 8

# ---- patch bytes PP puts in RAM that no site may overlap (they depend on the machine, RUNME text $3ba-$45c block) -----------------------------
PP_RAM_PATCHES = [(0x285E, 6), (0x1CC0, 4), (0x2F4A, 2), (0x2F62, 2), (0xCAC0, 6), (0x7C64, 4), (0xCFF8, 6), (0xD1AC, 2), (0xD1C4, 2),
                  (0x78558, 6), (0x78554, 4), (0x78D7A, 2), (0x78D92, 2)]
# PP's low-RAM stub block ($140-$41B, $264...): not a patch target (machine dependent, owned by PP's file service)
PP_LOW = (0x100, 0x5E8)

# ---- patch source parsing ------------------------------------------------------------------------------------------------------------
ORG_RE = re.compile(r"^\s*org\s+(\S+)\s*$", re.I)
HDR_RE = re.compile(r"^;\s*([a-z]+):\s*(.*)$")
HB_ORG_RE = re.compile(r"^\s*org\s+HB\s*\+\s*\$([0-9a-fA-F]+)\s*$", re.I)
VERSION_TAG = "@VERSION@"
CREDIT = "enhanced by dad_prg"
CORE_FILES = ("core.s", "core_floppy.s")


def addr_expr(s: str) -> int:
    """`$b2800`, `IB+$100` -> absolute address."""
    s = s.strip()
    m = re.fullmatch(r"IB\s*(?:\+\s*(\$[0-9a-fA-F]+|\d+))?", s)
    if m:
        return IB + (int(m.group(1).replace("$", "0x"), 0) if m.group(1) else 0)
    m = re.fullmatch(r"\$([0-9a-fA-F]+)", s)
    if m:
        return int(m.group(1), 16)
    raise SystemExit(f"bad address expression {s!r}")


def release_version() -> str:
    """THE one place of the release version: patches/VERSION (credit patches use the @VERSION@ token)."""
    v = (PATCHDIR / "VERSION").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+(\.\d+)?", v):
        raise SystemExit(f"patches/VERSION: {v!r} is not a version number")
    return v


def credit_line() -> str:
    return f"v{release_version()} {CREDIT}"


def build_stamp() -> str:
    """`git <short hash>` of HEAD, plus a note when patches/ or tools/ differ from it (so a zip can never be mistaken for a committed state)."""
    def g(*a):
        return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, check=True).stdout.strip()
    try:
        dirty = g("status", "--porcelain", "--", "patches", "tools") != ""
        return "git " + g("rev-parse", "--short", "HEAD") + (" + uncommitted changes in patches/ or tools/" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "git (unknown)"


def render_doc(text: str) -> str:
    """`{PATCHES}` = the default patches of the HD build (no floppy-only patch); `{PATCHES_FLOPPY}` = the default patches of the floppy build
    (HD file patches excluded: HAGA does not exist there); `{RAM}` = the payload/reserved-RAM map of the default HD set."""
    text = text.replace(VERSION_TAG, release_version())
    text = text.replace("{GIT}", build_stamp())
    if "{RAM}" in text:
        text = text.replace("{RAM}", "\n".join(ram_map(*default_selection(load_patches(), load_file_patches(), False))))
    for token, floppy in (("{PATCHES}", False), ("{PATCHES_FLOPPY}", True)):
        if token not in text:
            continue
        lines = []
        for p in load_patches() + ([] if floppy else load_file_patches()):
            if not p.default or (p.media == "floppy" and not floppy) or (p.media == "hd" and floppy):
                continue
            note = p.doc or next((n for n in p.notes if n.strip()), "")
            if len(note) > 150:
                note = note[:150].rsplit(" ", 1)[0] + " ..."
            lines.append(f"- {p.name}: {note}")
        text = text.replace(token, "\n".join(lines) if lines else "- (none: the unpatched game, only PP's loader plus the patch trampoline)")
    return text


_SET_USED: set[str] = set()


def _override_equ(line: str) -> str:
    """A preamble `NAME equ value ; comment` line with `--set NAME=VALUE` applied (the comment is kept)."""
    m = re.match(r"^(\s*)(\w+)(\s+equ\s+)([^;]*?)(\s*(?:;.*)?)$", line)
    if m and m.group(2) in SET_OVERRIDES:
        _SET_USED.add(m.group(2))
        return f"{m.group(1)}{m.group(2)}{m.group(3)}{SET_OVERRIDES[m.group(2)]}{m.group(5)}"
    return line


class Patch:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.default = True
        self.site = None
        self.orig = None          # declared (optional; the tool derives it from the dumps and cross-checks)
        self.data = []            # (addr, len, tag): zero-init reservations; tag `free` = outside the image (not zeroed)
        self.segments = []        # (org, source lines)
        self.preamble = []        # equ lines before the first org
        self.image = None         # file patch: game file (HAGA) edited in place
        self.media = None         # None = every build; `floppy` = only `build --floppy`; `hd` = only the HD build (never the floppy)
        self.gate = None          # `; gate: ram2mb`: the site goes into the SECOND site table, applied by the trampoline only on an STE / Mega STE with >= 2 MB (HD build only)
        self.himem = []           # (lo, hi_exclusive, label): RAM above 1 MB a gated patch owns (not in the image; checked for overlaps and the 2 MB ceiling)
        self.edits = []           # file patch: (file offset, expected original bytes)
        self.disk = []            # floppy disk patch: (disk letter, disk offset, expected original bytes)
        self.fsegments = []       # file patch: (file offset, source lines)
        self.notes = []
        self.doc = None
        self.ram = []             # (lo, hi_exclusive, label): reserved run-time work RAM, NOT in the payload image, but part of every collision/layout check
        self.stage1 = False       # `; phase: stage1`: site in the stage-1 loader (see STAGE1_BASE)
        self.requires = []        # patch names that must be in the same build
        self.conflicts = []       # patch names that must not be in the same build
        cur = None
        text = path.read_text()
        text = text.replace(VERSION_TAG, release_version())
        for line in text.splitlines():
            if cur is None and re.match(r"^\s*\w+\s+equ\s+", line):
                self.preamble.append(_override_equ(line))
                continue
            m = HDR_RE.match(line)
            if m and cur is None:
                k, v = m.group(1), m.group(2).strip()
                if k == "name": self.name = v
                elif k == "default": self.default = v.split(";")[0].strip().lower() not in ("no", "false", "0")
                elif k == "site": self.site = addr_expr(v.split(";")[0])
                elif k == "orig": self.orig = bytes.fromhex(v.split(";")[0].replace(" ", ""))
                elif k == "phase":
                    ph = v.split(";")[0].strip()
                    if ph not in ("boot", "stage1"):
                        raise SystemExit(f"{path}: phase must be `boot` (site loaded when the trampoline runs) or `stage1` (site in the stage-1 loader, applied before it runs)")
                    self.stage1 = ph == "stage1"
                elif k == "data":
                    parts = v.split(";")[0].split()
                    self.data.append((addr_expr(parts[0]), int(parts[1], 0), parts[2] if len(parts) > 2 else None))
                elif k == "image": self.image = v.strip()
                elif k == "disk":
                    parts = v.split(";")[0].split()
                    if len(parts) != 3 or parts[0] not in ("A", "B"):
                        raise SystemExit(f"{path}: `disk:` needs `A|B <offset> <orig hex>`")
                    self.disk.append((parts[0], int(parts[1].lstrip("$"), 16), bytes.fromhex(parts[2].replace(" ", ""))))
                elif k == "media":
                    if v.strip().lower() not in ("floppy", "hd"):
                        raise SystemExit(f"{path}: media must be `floppy` or `hd`")
                    self.media = v.strip().lower()
                elif k == "gate":
                    if v.split(";")[0].strip() != "ram2mb":
                        raise SystemExit(f"{path}: gate must be `ram2mb`")
                    self.gate = "ram2mb"
                elif k == "himem":
                    parts = v.split(";")[0].split()
                    m = re.fullmatch(r"(\S+?)\s*-\s*(\S+)", parts[0]) if parts else None
                    if not m:
                        raise SystemExit(f"{path}: `himem:` needs `$lo-$hi [label]` (inclusive end, no spaces around the dash)")
                    lo, hi = addr_expr(m.group(1)), addr_expr(m.group(2))
                    if not HIMEM_LO <= lo <= hi < HIMEM_END:
                        raise SystemExit(f"{path}: himem ${lo:x}-${hi:x} is outside ${HIMEM_LO:x}-${HIMEM_END - 1:x} (free at 2 MB on STE and Mega STE, trackloader.md section 2)")
                    self.himem.append((lo, hi + 1, " ".join(parts[1:]) or None))
                elif k == "edit":
                    a, b = v.split(None, 1)
                    self.edits.append((int(a.lstrip("$"), 16), bytes.fromhex(b.split(";")[0].replace(" ", ""))))
                elif k == "note": self.notes.append(v)
                elif k == "doc": self.doc = v
                elif k == "ram":
                    parts = v.split(";")[0].split()
                    m = re.fullmatch(r"(\S+?)\s*-\s*(\S+)", parts[0]) if parts else None
                    if not m and len(parts) >= 3 and parts[1] == "-":
                        m = re.fullmatch(r"(\S+)\s*-\s*(\S+)", " ".join(parts[:3]))
                        parts = parts[2:]
                    if not m:
                        raise SystemExit(f"{path}: `ram:` needs `$lo-$hi [label]` (inclusive end)")
                    lo, hi = addr_expr(m.group(1)), addr_expr(m.group(2))
                    if hi < lo:
                        raise SystemExit(f"{path}: ram range ${lo:x}-${hi:x} is reversed")
                    self.ram.append((lo, hi + 1, " ".join(parts[1:]) or None))
                elif k == "requires": self.requires += v.split(";")[0].split()
                elif k == "conflicts": self.conflicts += v.split(";")[0].split()
                continue
            m = HB_ORG_RE.match(line)
            if m:
                cur = (int(m.group(1), 16), [])
                self.fsegments.append(cur)
                continue
            m = ORG_RE.match(line)
            if m:
                cur = (addr_expr(m.group(1)), [])
                self.segments.append(cur)
            elif cur is not None:
                cur[1].append(line)
            elif line.strip() and not line.strip().startswith(";"):
                raise SystemExit(f"{path}: code before first org")


def _patch_files():
    return [f for f in sorted(PATCHDIR.glob("*.s")) if f.name not in CORE_FILES]


def load_patches():
    return [p for p in (Patch(f) for f in _patch_files()) if p.site is not None or p.disk]


def load_file_patches():
    out = []
    for f in _patch_files():
        p = Patch(f)
        if p.image is not None:
            if p.site is not None:
                raise SystemExit(f"{f.name}: `image:` and `site:` are mutually exclusive")
            out.append(p)
    return out


# ---- assembly --------------------------------------------------------------------------------------------------------------------------
def assemble(org: int, lines: list[str], equ: str = "", table: int = TABLE) -> bytes:
    common = "".join(f"{k}\tequ\t${v:x}\n" for k, v in CP_EQUS.items())
    src = f"IB\tequ\t${IB:x}\nTABLE\tequ\t${table:x}\n{common}{equ}\n\torg\t${org:x}\n" + "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "seg.s"
        s.write_text(src)
        out = Path(td) / "seg.bin"
        r = subprocess.run([VASM, "-Fbin", "-m68000", "-quiet", "-o", str(out), str(s)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"vasm failed:\n{src}\n{r.stderr}")
        return out.read_bytes()


def core_segment(table: int = TABLE, floppy: bool = False, table2: int = 0) -> bytes:
    p = Patch(PATCHDIR / ("core_floppy.s" if floppy else "core.s"))
    if len(p.segments) != 1 or p.segments[0][0] != CORE:
        raise SystemExit("core.s must hold exactly one segment, org IB+8")
    b = assemble(CORE, p.segments[0][1], "\n".join(p.preamble) + f"\nTABLE2\tequ\t${table2:x}", table=table)
    if CORE + len(b) > CORE_END:
        raise SystemExit(f"core overflows by {CORE + len(b) - CORE_END} B (${len(b):x} B)")
    return b


# ---- RAM dumps (the verification source) ---------------------------------------------------------------------------------------------------
_dumps = {}
def dump_bytes(path: Path, addr: int, ln: int) -> bytes:
    if path not in _dumps:
        _dumps[path] = path.read_bytes()
    return _dumps[path][addr:addr + ln]


# ---- file patches (HAGA) ---------------------------------------------------------------------------------------------------------------------
# HAGA is copied by RUNME to phystop-$8000: $F8000 (1 MB), $1F8000 (2 MB), $3F8000 (4 MB and up).  A file patch edits HAGA bytes in the build copy
# and must assemble to identical bytes at every base (position independent).
HAGA_RAM = (0xF8000, 0x1F8000, 0x3F8000)
FILE_IMAGES = ("HAGA",)


def file_patch_bytes(p: Patch) -> dict[int, bytes]:
    segs = {}
    for off, lines in p.fsegments:
        outs = [assemble(hb + off, lines, f"HB\tequ\t${hb:x}\n" + "\n".join(p.preamble)) for hb in HAGA_RAM]
        if any(o != outs[0] for o in outs):
            raise SystemExit(f"{p.name}: segment HB+${off:x} is not position independent ({[o.hex() for o in outs]})")
        if off in segs:
            raise SystemExit(f"{p.name}: two segments at HB+${off:x}")
        segs[off] = outs[0]
    return segs


def cmd_verify_files(fpatches) -> int:
    bad = 0
    used = []
    for p in fpatches:
        print(f"{p.name:18s} image {p.image}  {len(p.edits)} edit(s)")
        if p.image not in FILE_IMAGES:
            raise SystemExit(f"{p.name}: unsupported image {p.image!r} (supported: {FILE_IMAGES})")
        segs = file_patch_bytes(p)
        data = (ORIG / p.image).read_bytes()
        if {o for o, _ in p.edits} != set(segs):
            print(f"    edit offsets {sorted(o for o, _ in p.edits)} != segment offsets {sorted(segs)}")
            bad += 1
            continue
        for off, orig in p.edits:
            new = segs[off]
            ib = data[off:off + len(orig)]
            db = dump_bytes(DUMP_HOOK, HAGA_RAM[0] + off, len(orig))
            ok = ib == orig and db == orig and len(new) == len(orig)
            print(f"    HB+${off:04x} len {len(orig):2d}  orig {orig.hex()}")
            print(f"        file  {ib.hex()}  ({'match' if ib == orig else 'MISMATCH'})")
            print(f"        dump  {db.hex()}  ({'match' if db == orig else 'MISMATCH'})   [HAGA at $F8000 in ram_hook_1024.bin]")
            print(f"        new   {new.hex()}  ({'same length' if len(new) == len(orig) else 'LENGTH MISMATCH'}; identical at HB = " +
                  ", ".join(f"${h:x}" for h in HAGA_RAM) + ")")
            for img, a, b, n in used:
                if img == p.image and off < b and a < off + len(orig):
                    print(f"        OVERLAP with {n} (${a:x}-${b:x})")
                    ok = False
            used.append((p.image, off, off + len(orig), p.name))
            if not ok:
                bad += 1
    return bad


def apply_file_patches(fpatches, out: Path):
    for p in fpatches:
        segs = file_patch_bytes(p)
        f = out / p.image
        b = bytearray(f.read_bytes())
        for off, orig in p.edits:
            if bytes(b[off:off + len(orig)]) != orig:
                raise SystemExit(f"{p.name}: {p.image}+${off:x} is not the expected original bytes")
            b[off:off + len(orig)] = segs[off]
            print(f"{p.image}+${off:04x} {len(orig):4d} {orig.hex()} -> {segs[off].hex()}   [{p.name}]")
        f.write_bytes(bytes(b))


# ---- sites and the payload image -----------------------------------------------------------------------------------------------------------
def site_bytes(p: Patch):
    seg = [s for s in p.segments if s[0] == p.site]
    if not seg:
        raise SystemExit(f"{p.name}: no org ${p.site:x} segment")
    new = assemble(p.site, seg[0][1], "\n".join(p.preamble))
    orig = p.orig if p.orig is not None else dump_bytes(DUMP_HOOK, p.site, len(new))
    if len(new) > len(orig):
        raise SystemExit(f"{p.name}: new bytes ({len(new)}) longer than orig ({len(orig)})")
    if len(new) < len(orig):
        if (len(orig) - len(new)) % 2:
            raise SystemExit(f"{p.name}: orig is {len(orig) - len(new)} byte(s) longer than new; pad to an even number of bytes")
        new = new + b"\x4e\x71" * ((len(orig) - len(new)) // 2)
    return orig, new


def site_list(patches: list[Patch]):
    sites = []
    for p in patches:
        orig, new = site_bytes(p)
        sites.append(dict(name=p.name, addr=p.site, orig=orig, new=new, gate=p.gate))
    by_addr = sorted(sites, key=lambda s: s["addr"])
    for s, t in zip(by_addr, by_addr[1:]):
        if s["addr"] + len(s["orig"]) > t["addr"]:
            raise SystemExit(f"site overlap: {s['name']} ${s['addr']:x}+{len(s['orig'])} vs {t['name']} ${t['addr']:x}")
    for s in sites:
        e = s["addr"] + len(s["orig"])
        for a, n in PP_RAM_PATCHES:
            if s["addr"] < a + n and a < e:
                raise SystemExit(f"{s['name']}: site overlaps PP's RAM patch at ${a:x}+{n}")
        if s["addr"] < PP_LOW[1] and e > PP_LOW[0]:
            raise SystemExit(f"{s['name']}: site ${s['addr']:x} is in PP's low-RAM stub block ${PP_LOW[0]:x}-${PP_LOW[1] - 1:x}")
        if s["addr"] >= IB:
            raise SystemExit(f"{s['name']}: site ${s['addr']:x} is inside the payload area")
    return sites


def in_area(a: int, ln: int) -> bool:
    return any(lo <= a and a + ln <= hi for lo, hi in BLOB_AREAS)

# ---- target layouts and reserved work RAM (`; ram:`) --------------------------------------------------------------------------------------
# Free run(s) for blobs, data and `; ram:` reservations per target layout.  1 MB: $B2700-$E83FF is zero at game start (rendering.md section 3; the
# tool's blob areas start at $B2800, above the trampoline).  4 MB with PP's whole-image disk cache (68000, no pp_bigram_cache): MS1 lands on
# $81000-$C6F2B over the payload and MS2 on $C7900-$13D7FF (delivery.md section 5): nothing in the payload area is free.  With pp_bigram_cache (or the floppy
# build, which has no HAGA cache) the 1 MB map holds at 4 MB (cold boots, delivery.md section 4 and the road patches' RDG1 magic at $C0000, road.md 7.2).
FREE_1MB = [(BLOB_AREAS[0][0], FREE_END)]
LAYOUT_NAMES = ("1MB", "4MB")


def build_layouts(floppy: bool = False, fnames=()) -> dict:
    """-> {layout name: free runs} for the layouts a build supports (`live` = a 1 MB snapshot: pass floppy=False, fnames=())."""
    out = {"1MB": FREE_1MB}
    if floppy or "pp_bigram_cache" in fnames:
        out["4MB"] = FREE_1MB
    return out


def ram_in_runs(lo: int, hi: int, runs) -> bool:
    return any(a <= lo and hi <= b for a, b in runs)



def build_image(patches: list[Patch], table: int = TABLE, min_end: int = IMG_MIN_END, floppy: bool = False, fnames=(), live: bool = False):
    """-> (image bytes at IB, sites).  `table` = where the site table goes (the core is assembled with the same equ);
    `min_end` = the lowest image end (the HD layout pads to $B8000 so that blob area B is inside the image).
    HD layout of the table: [sites that always apply][addr 0][`; gate: ram2mb` sites][addr 0][orig/new byte pool]; the trampoline applies the second list
    only on an STE / Mega STE with >= 2 MB (core.s).  The floppy table is the single list (core_floppy.s): a gated patch cannot be in a floppy build."""
    if live:
        patches = [p for p in patches if not p.stage1 and not p.gate]      # a snapshot is long past stage 1: nothing to apply; the gate is closed at 1 MB
    sites = site_list([p for p in patches if not p.stage1])
    sites = [s for s in sites if not s["gate"]] + [s for s in sites if s["gate"]]
    n = len(sites)
    nfirst = sum(1 for s in sites if not s["gate"])
    tbl_len = (n + 2) * 16                                  # both lists end with a zero 16-byte slot (HD and floppy)
    table2 = table + (nfirst + 1) * 16
    pool = bytearray()
    ptrs = []
    for s in sites:
        o = len(pool); pool += s["orig"]
        nw = len(pool); pool += s["new"]
        ptrs.append((table + tbl_len + o, table + tbl_len + nw))
    if tbl_len + len(pool) > TABLE_END - table:
        raise SystemExit(f"site table + byte pool overflow ${table:x}-${table + TABLE_END - TABLE - 1:x}")
    core = core_segment(table, floppy=floppy, table2=table2)
    placed = [(CORE, CORE + len(core), "core"), (table, table + tbl_len + len(pool), "site table")]
    blobs = []
    rams = []
    for p in patches:
        for org, lines in p.segments:
            if org == p.site:
                continue
            b = assemble(org, lines, "\n".join(p.preamble))
            if not b:
                continue
            if not in_area(org, len(b)):
                raise SystemExit(f"{p.name}: blob ${org:x}+{len(b)} is outside the blob areas " +
                                 ", ".join(f"${lo:x}-${hi - 1:x}" for lo, hi in BLOB_AREAS))
            placed.append((org, org + len(b), p.name))
            blobs.append((org, b))
        for a, l, tag in p.data:
            if tag not in (None, "free"):
                raise SystemExit(f"{p.name}: unknown data tag {tag!r}")
            if not in_area(a, l):
                raise SystemExit(f"{p.name}: data ${a:x}+{l} is outside the blob areas")
            placed.append((a, a + l, p.name + " data"))
        for lo, hi, label in p.ram:
            for lname, runs in build_layouts(floppy, fnames).items():
                if not ram_in_runs(lo, hi, runs):
                    raise SystemExit(f"{p.name}: reserved RAM ${lo:x}-${hi - 1:x} is not free in the {lname} layout (free: " +
                                     ", ".join(f"${a:x}-${b - 1:x}" for a, b in runs) + ")")
            rams.append((lo, hi, f"{p.name} ram" + (f" ({label})" if label else "")))
        for lo, hi, label in p.himem:
            rams.append((lo, hi, f"{p.name} himem" + (f" ({label})" if label else "")))
    if not live and any(p.ram for p in patches) and "4MB" not in build_layouts(floppy, fnames):
        raise SystemExit("reserved RAM (`; ram:`) of " + ", ".join(p.name for p in patches if p.ram) + " is free at 1 MB only: a HD build needs the file patch "
                         "pp_bigram_cache for the 4 MB layout (whole-image disk cache over $B2700.., delivery.md section 5)")
    for (a0, a1, n0), (b0, b1, n1) in zip(sorted(placed + rams), sorted(placed + rams)[1:]):
        if a1 > b0:
            raise SystemExit(f"image overlap: {n0} ${a0:x}-${a1 - 1:x} vs {n1} ${b0:x}-${b1 - 1:x}")
    # the image spans IB .. the highest byte of anything placed (at least IMG_MIN_END); `free` data inside the span is simply not copied
    end = max([min_end] + [b for a, b, _ in placed])
    end = (end + 3) & ~3
    if end - IB > IMG_MAX_LEN:
        raise SystemExit(f"payload image ${IB:x}-${end - 1:x} = {end - IB} B exceeds IMG_MAX_LEN {IMG_MAX_LEN} (RUNME headroom, README.md)")
    img = bytearray(end - IB)
    img[CORE - IB:CORE - IB + len(core)] = core
    for i, s in enumerate(sites):
        slot = i if i < nfirst else i + 1                       # the second list starts behind the first list's terminator
        struct.pack_into(">IHHII", img, table - IB + slot * 16, s["addr"], len(s["orig"]), 0, ptrs[i][0], ptrs[i][1])
    img[table - IB + tbl_len:table - IB + tbl_len + len(pool)] = pool
    for org, b in blobs:
        img[org - IB:org - IB + len(b)] = b
    return bytes(img), sites


# ---- footprints, dependencies, conflicts -------------------------------------------------------------------------------------------------------
RAM_WITNESS = ("ram_hook_1024.bin", "ram_entry_1024.bin", "ram_race0.bin", "ram_race_start.bin", "ram_race_grid.bin", "ram_race_up.bin") + DUMPS_MSTE   # the stock game, never patched: STE 1.62 and Mega STE 2.06, all 1 MB


def footprint(p: Patch) -> list[tuple[int, int, str]]:
    """Every RAM range a RAM patch owns: its site bytes, blobs, `; data:`, `; ram:` -> (lo, hi_exclusive, what)."""
    out = []
    if p.site is None:
        return out
    orig, _ = site_bytes(p)
    out.append((p.site, p.site + len(orig), "site"))
    for org, lines in p.segments:
        if org != p.site:
            b = assemble(org, lines, "\n".join(p.preamble))
            if b:
                out.append((org, org + len(b), "blob"))
    out += [(a, a + l, "data") for a, l, _ in p.data]
    out += [(lo, hi, "ram" + (f" {label}" if label else "")) for lo, hi, label in p.ram]
    out += [(lo, hi, "himem" + (f" {label}" if label else "")) for lo, hi, label in p.himem]
    return out


def conflicting(p: Patch, q: Patch) -> bool:
    return q.name in p.conflicts or p.name in q.conflicts


def check_pairs(patches: list[Patch]) -> list[str]:
    """Footprints of two patches must not overlap unless they declare `; conflicts:` (then they can never be built together)."""
    ps = [p for p in patches if p.site is not None]
    fps = {p.name: footprint(p) for p in ps}
    bad = []
    for i, p in enumerate(ps):
        for q in ps[i + 1:]:
            if conflicting(p, q):
                continue
            for a0, a1, w0 in fps[p.name]:
                for b0, b1, w1 in fps[q.name]:
                    if a0 < b1 and b0 < a1:
                        bad.append(f"{p.name} {w0} ${a0:x}-${a1 - 1:x} overlaps {q.name} {w1} ${b0:x}-${b1 - 1:x} (no `; conflicts:` declared)")
    for p in ps:
        for lo, hi, w in fps[p.name]:
            if w.startswith("ram"):
                for lname, runs in build_layouts(True, ()).items():
                    if not ram_in_runs(lo, hi, runs):
                        bad.append(f"{p.name} {w} ${lo:x}-${hi - 1:x} is not free in the {lname} layout")
                for n in RAM_WITNESS:
                    f = ROOT / "work" / "dumps" / n
                    if f.exists() and any(dump_bytes(f, lo, hi - lo)):
                        bad.append(f"{p.name} {w} ${lo:x}-${hi - 1:x} is not zero in the stock game's RAM dump {n}")
    return bad


def check_free_run() -> list[str]:
    """The claimed free run [blob area start, FREE_END) must be zero in every witness dump (STE 1.62 and Mega STE 2.06 at 1 MB): FREE_END cannot silently drift into TOS data."""
    bad = []
    lo = BLOB_AREAS[0][0]
    for n in RAM_WITNESS:
        f = ROOT / "work" / "dumps" / n
        if not f.exists():
            bad.append(f"witness dump work/dumps/{n} is missing")
        elif any(dump_bytes(f, lo, FREE_END - lo)):
            bad.append(f"free run ${lo:x}-${FREE_END - 1:x} is not zero in the stock game's RAM dump {n}")
    return bad


def check_selection(sel, known_names) -> list[str]:
    """`; requires:` / `; conflicts:` of a selection (patches + file patches); unknown names are an error too."""
    names = {p.name for p in sel}
    bad = []
    for p in sel:
        for r in p.requires:
            if r not in known_names:
                bad.append(f"{p.name} requires unknown patch {r!r}")
            elif r not in names:
                bad.append(f"{p.name} requires {r}, which is not in this build (add it to --only)")
        for c in p.conflicts:
            if c not in known_names:
                bad.append(f"{p.name} conflicts with unknown patch {c!r}")
            elif c in names:
                bad.append(f"{p.name} conflicts with {c}: they must not be built together")
    return bad


def in_build(p: Patch, floppy: bool) -> bool:
    """A patch belongs to the HD build unless it is `; media: floppy`, and to the floppy build unless it is `; media: hd`."""
    return p.media is None or p.media == ("floppy" if floppy else "hd")


def default_selection(patches, fpatches, floppy: bool):
    sel = [p for p in patches if p.default and in_build(p, floppy) and (p.site is not None or p.media == "floppy")]
    fsel = [p for p in fpatches if p.default]
    return sel, fsel


# ---- verification ----------------------------------------------------------------------------------------------------------------------------
def stage1_sites(patches) -> list[dict]:
    """The `; phase: stage1` sites of a selection (addr, orig, new), checked: orig declared and equal to the unpacked MSR_S1.FIC, inside the image."""
    sites = []
    for p in patches:
        if not p.stage1:
            continue
        if p.site is None or p.orig is None:
            raise SystemExit(f"{p.name}: a `; phase: stage1` patch needs `; site:` and `; orig:`")
        orig, new = site_bytes(p)
        x = p.site - STAGE1_BASE
        if x < 0 or x + len(orig) > STAGE1_LEN or len(orig) % 2:
            raise SystemExit(f"{p.name}: stage-1 site ${p.site:x}+{len(orig)} is outside $78000-${STAGE1_BASE + STAGE1_LEN - 1:x} or odd-sized")
        if stage1_image()[x:x + len(orig)] != orig:
            raise SystemExit(f"{p.name}: orig {orig.hex()} is not what MSR_S1.FIC holds at ${p.site:x}")
        sites.append(dict(name=p.name, addr=p.site, orig=orig, new=new))
    site_list([p for p in patches if p.stage1])              # overlaps, PP's RAM patches
    return sites


def stage1_disk_off(addr: int, ln: int) -> int:
    """Floppy: byte offset in disk A of stage-1 RAM byte `addr` (stage 1 = tracks 1.. side 0, 5,120 B each, in RAM order; a site must stay inside a track)."""
    x = addr - STAGE1_BASE
    if x % STAGE1_TRACK_BYTES + ln > STAGE1_TRACK_BYTES:
        raise SystemExit(f"stage-1 site ${addr:x}+{ln} crosses a floppy track boundary")
    return sec_off(1 + x // STAGE1_TRACK_BYTES, 0, 1) + x % STAGE1_TRACK_BYTES


def verify_stage1(p: Patch) -> int:
    """Report and check one stage-1 patch against MSR_S1.FIC (HD) and the original floppy disk A (when the STX images exist)."""
    bad = 0
    try:
        (s,) = stage1_sites([p])
    except SystemExit as e:
        print(f"{p.name:18s} stage-1 site ${p.site:05x}: {e}")
        return 1
    x = s["addr"] - STAGE1_BASE
    print(f"{p.name:18s} stage-1 site ${s['addr']:05x} len {len(s['orig'])}  (phase stage1: applied by RUNME's copy routine / disk A edit, before the trampoline)")
    print(f"    declared orig         : {s['orig'].hex()}")
    print(f"    MSR_S1.FIC unpacked   : {stage1_image()[x:x + len(s['orig'])].hex()}  (match)   [originals/MOONSHR/FILES/MSR_S1.FIC, +${x:04x}]")
    if all((FLOPPY_DIR / n).exists() for n in FLOPPY_STX.values()):
        off = stage1_disk_off(s["addr"], len(s["orig"]))
        have = bytes(stx_disk("A")[off:off + len(s["orig"])])
        print(f"    original floppy disk A: {have.hex()}  ({'match' if have == s['orig'] else 'MISMATCH'})   [disk A +${off:05x}]")
        bad += have != s["orig"]
    print(f"    new                   : {s['new'].hex()}")
    return bad


def cmd_verify(patches, fpatches=()):
    bad = 0
    dpatches = [p for p in patches if p.site is None and p.disk]
    patches = [p for p in patches if p.site is not None]
    for p in patches:
        if p.stage1:
            bad += verify_stage1(p)
            continue
        seg = [s for s in p.segments if s[0] == p.site]
        new = assemble(p.site, seg[0][1], "\n".join(p.preamble)) if seg else b""
        orig = p.orig if p.orig is not None else dump_bytes(DUMP_HOOK, p.site, len(new))
        hk = dump_bytes(DUMP_HOOK, p.site, len(orig))
        en = dump_bytes(DUMP_ENTRY, p.site, len(orig))
        hok, eok = hk == orig and len(orig) > 0, en == orig
        print(f"{p.name:18s} site ${p.site:05x} len {len(orig)}")
        print(f"    declared/derived orig : {orig.hex()}")
        print(f"    ram at hook instant   : {hk.hex()}  ({'match' if hok else 'MISMATCH'})   [work/dumps/ram_hook_1024.bin]")
        print(f"    ram at game entry     : {en.hex()}  ({'match' if eok else 'MISMATCH'})   [work/dumps/ram_entry_1024.bin]")
        print(f"    new                   : {new.hex()}")
        if DUMP_FLOPPY.exists():
            fl = dump_bytes(DUMP_FLOPPY, p.site, len(orig))
            print(f"    ram of the orig floppy: {fl.hex()}  ({'match' if fl == orig else 'differs: HD-only site'})   [work/floppy/ram_answered.bin]")
        if not (hok and eok):
            bad += 1
        try:
            site_list([p])
        except SystemExit as e:
            print(f"    {e}")
            bad += 1
    known = {p.name for p in load_patches()} | {p.name for p in load_file_patches()}
    for msg in check_free_run() + check_pairs(patches):
        print(f"    {msg}")
        bad += 1
    if {p.name for p in patches} >= {p.name for p in load_patches() if p.site is not None}:   # `verify` proper (the whole set, not a build's selection): the default sets must satisfy the rules
        allp, allf = load_patches(), load_file_patches()
        for floppy in (False, True):
            sel, fsel = default_selection(allp, allf, floppy)
            for msg in check_selection(sel + fsel, known):
                print(f"    default {'floppy' if floppy else 'HD'} set: {msg}")
                bad += 1
        print("    dependencies/conflicts/reserved RAM: " + ("checked: all pairs, both default sets, RAM free in every supported layout" if not bad else "FAILED"))
    bad += cmd_verify_runme()
    bad += cmd_verify_files(fpatches)
    bad += cmd_verify_disk(dpatches)
    print("verify:", "ALL OK" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


def floppy_site_mismatches(patches) -> list[str]:
    """RAM sites whose original bytes differ in the ORIGINAL FLOPPY's RAM (DUMP_FLOPPY): the game code on the floppy is expected to be PP's HD code."""
    bad = []
    if not DUMP_FLOPPY.exists():
        return ["work/floppy/ram_answered.bin missing: cannot check the sites against the floppy game"]
    for p in patches:
        if p.site is None or p.stage1:
            continue
        seg = [x for x in p.segments if x[0] == p.site]
        orig = p.orig if p.orig is not None else dump_bytes(DUMP_HOOK, p.site, len(assemble(p.site, seg[0][1], "\n".join(p.preamble))) if seg else 0)
        if dump_bytes(DUMP_FLOPPY, p.site, len(orig)) != orig:
            bad.append(f"{p.name} ${p.site:05x}: floppy RAM has {dump_bytes(DUMP_FLOPPY, p.site, len(orig)).hex()}, expected {orig.hex()}")
    return bad


def cmd_verify_disk(dpatches) -> int:
    """Floppy disk patches: the expected original bytes at every `; disk:` offset of the (STX-converted) original disk, the new bytes assemble to
    the same length.  Skipped (with a note) when the git-ignored STX images are absent."""
    if not dpatches:
        return 0
    bad = 0
    if not all((FLOPPY_DIR / n).exists() for n in FLOPPY_STX.values()):
        print(f"floppy disk patches {[p.name for p in dpatches]}: originals/floppy/*.stx absent, not verified")
        return 0
    disks = {l: stx_disk(l) for l in "AB"}
    for p in dpatches:
        segs = disk_patch_bytes(p)
        for letter, off, orig in p.disk:
            have = bytes(disks[letter][off:off + len(orig)])
            ok = have == orig and len(segs[off]) == len(orig)
            print(f"{p.name:18s} disk {letter} +${off:05x} len {len(orig)}")
            print(f"    declared orig         : {orig.hex()}")
            print(f"    original disk image   : {have.hex()}  ({'match' if have == orig else 'MISMATCH'})")
            print(f"    new                   : {segs[off].hex()}")
            bad += not ok
    return bad


def cmd_verify_runme() -> int:
    """RUNME's two edit points (also in RAM at the stack-phase copy), the bss pc-relative scan, the unpacked-image cross-check."""
    bad = 0
    src = runme_source()
    text = src[28:28 + TEXT_LEN]
    ref = ROOT / "work" / "dumps" / "RUNME_unpacked.tos"
    same = ref.read_bytes() == src
    print(f"RUNME unpack          : pp_depack(RUNME.TOS) {len(src)} B {'== work/dumps/RUNME_unpacked.tos' if same else 'DIFFERS from work/dumps/RUNME_unpacked.tos'}")
    bad += not same
    for name, off, orig in (("stage hook", STAGE_TXT, STAGE_ORIG), ("PP tail", TAIL_TXT, TAIL_ORIG)):
        got = bytes(text[off:off + len(orig)])
        ram = dump_bytes(DUMP_HOOK, STACK_RAM + off - STACK_TXT, len(orig))
        ok = got == orig and ram == orig
        print(f"RUNME {name:11s} text ${off:04x}: file {got.hex()}  ram ${STACK_RAM + off - STACK_TXT:x} {ram.hex()}  ({'match' if ok else 'MISMATCH'})")
        bad += not ok
    pad = bytes(text[TAIL_TXT + 4:TAIL_TXT + 4 + len(TAIL_PAD)])
    print(f"RUNME tail padding    text ${TAIL_TXT + 4:04x}: {pad.hex()}  ({'zero, free' if pad == TAIL_PAD else 'NOT FREE'})")
    bad += pad != TAIL_PAD
    try:
        check_bss_pcrel_complete(text)
        for t, (reg, tgt) in BSS_LEAS.items():
            op, d = struct.unpack_from(">Hh", text, t)
            if op != 0x41FA | reg << 9 or t + 2 + d != tgt:
                raise SystemExit(f"text ${t:x} is not `lea ${tgt:x}(pc),a{reg}`")
        print(f"RUNME bss pc-relative references: {len(BSS_LEAS)} `lea d(pc),aN` ({', '.join(f'${t:x}' for t in BSS_LEAS)}), no others")
    except SystemExit as e:
        print(f"RUNME bss scan: {e}")
        bad += 1
    return bad


def ram_map(sel, fsel=()) -> list[str]:
    """The RAM a selection owns above the trampoline: payload blobs/data (in the image) and `; ram:` reservations (not in the image), sorted by address."""
    rows = []
    for p in sel:
        if p.site is None:
            continue
        for lo, hi, what in footprint(p):
            if what != "site":
                rows.append((lo, hi, p.name, what))
    layouts = build_layouts(False, [p.name for p in fsel])
    out = [f"${lo:05x}-${hi - 1:05x} {hi - lo:6d} B  {name:12s} {what}" + ("  [not in the image]" if what.startswith(("ram", "himem")) else "") for lo, hi, name, what in sorted(rows)]
    out.append("valid layouts for this set: " + ", ".join(layouts) + "; free run(s) " + ", ".join(f"${a:x}-${b - 1:x}" for a, b in FREE_1MB))
    return out


def cmd_list(patches, fpatches=()):
    print(f"{'name':18s} {'default':8s} {'site':8s} {'len':4s} blobs / data / ram")
    for p in patches:
        if p.site is None:
            offs = ",".join(f"{l}+${o:x}" for l, o, _ in p.disk)
            print(f"{p.name:18s} {('yes' if p.default else 'no') + (' (floppy)' if p.media else ''):8s} disk {offs}  (floppy disk patch, "
                  f"{sum(len(b) for _, _, b in p.disk)} B)")
            continue
        blobs = ",".join(f"${o:x}" for o, _ in p.segments if o != p.site) or "-"
        data = ",".join(f"${a:x}+{l}" + (f" ({t})" if t else "") for a, l, t in p.data) or "-"
        seg = [s for s in p.segments if s[0] == p.site]
        ln = len(assemble(p.site, seg[0][1], "\n".join(p.preamble))) if seg else 0
        dflt = ("yes" if p.default else "no") + (f" ({p.media})" if p.media else "") + (" (gate)" if p.gate else "") + (" (stage1)" if p.stage1 else "")
        rams = ",".join(f"${lo:x}-${hi - 1:x}" + (f" ({lb})" if lb else "") for lo, hi, lb in p.ram) or "-"
        print(f"{p.name:18s} {dflt:8s} ${p.site:05x}  {ln:4d} {blobs} / {data} / ram {rams}")
    for p in fpatches:
        offs = ",".join(f"${o:x}" for o, _ in p.edits)
        print(f"{p.name:18s} {'yes' if p.default else 'no':8s} {p.image}+{offs}  (file patch, {sum(len(b) for _, b in p.edits)} B)")
    deps = [p for p in patches if p.requires or p.conflicts]
    if deps:
        print("dependencies (enforced by build/live, default selection and verify):")
        for p in deps:
            print(f"  {p.name:18s}" + (f" requires {' '.join(p.requires)}" if p.requires else "") + (f"  conflicts {' '.join(p.conflicts)}" if p.conflicts else ""))
    print("reserved RAM and payload map (HD default set):")
    for line in ram_map(*default_selection(patches, fpatches, False)):
        print("  " + line)


# ---- RUNME -----------------------------------------------------------------------------------------------------------------------------------
def runme_source() -> bytes:
    src = pp_depack((ORIG / "RUNME.TOS").read_bytes())
    t, d, b = struct.unpack_from(">III", src, 2)
    if (t, d, b) != (TEXT_LEN, 22, 111206):
        raise SystemExit(f"RUNME.TOS unpacks to text ${t:x} data {d} bss {b}, expected ${TEXT_LEN:x} 22 111206")
    return src


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


def check_bss_pcrel_complete(text: bytes):
    """Every d16(pc) operand (ea mode 7/2) whose target is >= OLD_BSS must be listed in BSS_LEAS (or NOT_CODE), else it would silently keep a
    stale displacement when the bss moves."""
    for t in range(0, TEXT_LEN - 3, 2):
        op, d = struct.unpack_from(">Hh", text, t)
        if op & 0x3F == 0x3A and t + 2 + d >= OLD_BSS and t not in BSS_LEAS and t not in NOT_CODE:
            raise SystemExit(f"text ${t:x}: unlisted pc-relative reference to ${t + 2 + d:x} (op {op:04x})")


def copy_routine(img_len: int, s1=()) -> bytes:
    """Appended to RUNME's data (text OLD_BSS): copies the payload (which follows PTRS_LEN bytes of bss pointers) to IB, then (stage-1 patches only)
    verifies and applies their sites in the unpacked stage-1 loader at $78000 (all or nothing, like the trampoline), then continues with the
    `jmp $78000.l` it displaced from text $3b4.  Entered by `jmp copy.l` from the stack-phase block, in supervisor mode, registers and SR preserved.
    s1 = [dict(addr, orig, new)]; without any the routine is byte-identical to the one before stage-1 patches existed."""
    regs = "d0-d2/a0-a2" if s1 else "d0/a0-a1"
    lines = [f"copy:\tmovem.l\t{regs},-(a7)",
             "\tmove.w\tsr,-(a7)",
             "\tlea\tpayload(pc),a0",
             f"\tlea\t${IB:x}.l,a1",
             f"\tmove.w\t#{img_len // 4 - 1},d0",
             ".cp:\tmove.l\t(a0)+,(a1)+",
             "\tdbra\td0,.cp"]
    if s1:
        lines += ["\tlea\ts1tab(pc),a0",
                  ".v:\tmove.l\t(a0)+,d0\t\t\t; pass 1: verify (addr 0 ends the table)",
                  "\tbeq.s\t.apply",
                  "\tmovea.l\td0,a1",
                  "\tmove.w\t(a0)+,d2",
                  "\tmove.w\td2,d1",
                  "\tsubq.w\t#1,d1",
                  ".vc:\tcmpm.b\t(a0)+,(a1)+",
                  "\tbne.s\t.done\t\t\t; mismatch: apply nothing",
                  "\tdbra\td1,.vc",
                  "\tadda.w\td2,a0\t\t\t; skip the new bytes",
                  "\tbra.s\t.v",
                  ".apply:\tlea\ts1tab(pc),a0",
                  ".a:\tmove.l\t(a0)+,d0\t\t\t; pass 2: apply",
                  "\tbeq.s\t.done",
                  "\tmovea.l\td0,a1",
                  "\tmove.w\t(a0)+,d2",
                  "\tadda.w\td2,a0\t\t\t; skip the orig bytes",
                  "\tmove.w\td2,d1",
                  "\tsubq.w\t#1,d1",
                  ".aw:\tmove.b\t(a0)+,(a1)+",
                  "\tdbra\td1,.aw",
                  "\tbra.s\t.a",
                  ".done:"]
    lines += ["\tmove.w\t(a7)+,sr",
              f"\tmovem.l\t(a7)+,{regs}",
              "\tjmp\t$78000.l"]
    if s1:
        lines.append("s1tab:")
        for s in s1:
            lines.append(f"\tdc.l\t${s['addr']:x}")
            lines.append(f"\tdc.w\t{len(s['orig'])}")
            lines.append("\tdc.b\t" + ",".join(f"${b:02x}" for b in s["orig"]))
            lines.append("\tdc.b\t" + ",".join(f"${b:02x}" for b in s["new"]))
        lines += ["\tdc.l\t0", "\teven"]
    lines += [f"\tds.b\t{PTRS_LEN}", "payload:"]
    return assemble(OLD_BSS, lines)


def build_runme(img: bytes, s1=()) -> bytes:
    src = runme_source()
    text = bytearray(src[28:28 + TEXT_LEN])
    data = src[28 + TEXT_LEN:28 + TEXT_LEN + 22]
    rel_off = 28 + TEXT_LEN + 22
    offs, rel_end = decode_reloc(src[rel_off:])
    assert rel_end == len(src) - rel_off
    assert len(img) % 4 == 0 and len(img) // 4 - 1 <= 0xFFFF
    cr = copy_routine(len(img), s1)
    copy_len = len(cr) - PTRS_LEN            # code only; the pointer slots follow it
    n = copy_len + PTRS_LEN + len(img)
    assert bytes(text[STAGE_TXT:STAGE_TXT + 6]) == STAGE_ORIG and bytes(text[TAIL_TXT:TAIL_TXT + 4]) == TAIL_ORIG
    assert bytes(text[TAIL_TXT + 4:TAIL_TXT + 6]) == TAIL_PAD
    # 1. stage hook: `jmp copy.l` (text-relative: the loader relocates it; the copy routine ends in the displaced `jmp $78000.l`)
    text[STAGE_TXT:STAGE_TXT + 6] = struct.pack(">HI", 0x4EF9, OLD_BSS)
    # 2. PP's tail -> `jmp trampoline.l` (absolute RAM address, NOT relocated; the trampoline ends in the displaced `jmp $1000.w`)
    text[TAIL_TXT:TAIL_TXT + 6] = struct.pack(">HI", 0x4EF9, CORE)
    # 3. bss moved by n: pc-relative `lea d(pc),aN` into bss become `movea.l d(pc),aN` from relocated pointer slots
    check_bss_pcrel_complete(bytes(text))
    slot = {tgt: OLD_BSS + copy_len + 4 * i for i, tgt in enumerate(BSS_PTR_TARGETS)}
    for t, (reg, tgt) in BSS_LEAS.items():
        op, d = struct.unpack_from(">Hh", text, t)
        assert op == 0x41FA | reg << 9 and t + 2 + d == tgt, f"text ${t:x} is not lea ${tgt:x}(pc),a{reg}"
        disp = slot[tgt] - (t + 2)
        assert -0x8000 <= disp <= 0x7FFF, f"pointer slot out of reach of text ${t:x}"
        struct.pack_into(">Hh", text, t, 0x207A | reg << 9, disp)      # movea.l d(pc),aN
    for o in offs:
        v = struct.unpack_from(">I", text, o)[0]
        if v >= OLD_BSS:
            struct.pack_into(">I", text, o, v + n)
    ptrs = b"".join(struct.pack(">I", tgt + n) for tgt in BSS_PTR_TARGETS)
    # relocation table: + the stage hook's operand (text $3b6) and the two pointer slots (absolute, relocated by the loader)
    offs = sorted(set(offs) | {STAGE_TXT + 2} | set(slot.values()))
    newdata = data + cr[:copy_len] + ptrs + img
    assert len(newdata) == 22 + n and len(cr) == copy_len + PTRS_LEN
    hdr = bytearray(src[:28])
    struct.pack_into(">I", hdr, 6, len(newdata))
    out = bytes(hdr) + bytes(text) + newdata + encode_reloc(offs)
    o2, e2 = decode_reloc(out[28 + TEXT_LEN + len(newdata):])
    assert o2 == offs and e2 == len(out) - (28 + TEXT_LEN + len(newdata))
    return out



# ---- floppy build: the original STX disks + our payload on blank sectors + a stage-0 loader --------------------------------
# Original release: 2 disks, 82 track-sides in the STX but a standard 80-track drive, 10 sectors x 512 B = 800 KB each
# (work/notes/floppy.md).  Disk A is bootable (custom boot sector, no FAT): it reads tracks 1-5 to $40000, copies 25,600 B to
# $78000 and jumps there; that loader then scatters tracks 0-61 into $1000-$4E600, plays the intro/credits, asks a manual-lookup
# question and only then loads the game (tracks 62-79) and starts it.  Disk B is the raw data disk (MS2's content).
FLOPPY_DIR = ORIG.parent / "floppy"      # originals/floppy/ (the STX images, git-ignored)
FLOPPY_REQUIRED = ("fl_hook",)                # the floppy delivery hook: always part of a floppy build (like the core), even with --only
FLOPPY_STX = {"A": "moonshine_racers_millennium_a.stx", "B": "moonshine_racers_millennium_b.stx"}
FLOPPY_GEO = (80, 2, 10)                      # tracks, sides, sectors/track of the plain .ST images
SECT = 512
LOADER_ORG = 0x78CA                           # free area of the boot sector: $78CA-$79F3 (the original program ends at $78C1, its track/buffer
                                              # descriptor sits at $78C4-$78C9 and is read by the relocated copy, $79F4-$79FF is stale mastering data)
BOOT_ENTRY = 0x7818                           # the original boot program's first instruction `lea.l $7f830.l,a6` (6 B): displaced into the loader
BOOT_ENTRY_ORIG = bytes.fromhex("4df90007f830")
BOOT_PROG = BOOT_ENTRY + 6                    # ... and the loader continues at the next instruction (offsets 0-$17 of the sector stay as shipped: the game
                                              # itself tests the long at offset 2 ('MOON') to recognise disk 1, $d77a)
# Sectors that the boot loader never reads (raw FDC trace of a full pre-question boot, build/logs/floppy_flow.log: 1,127 reads, tracks 0-61) and
# that are blank (0x6DB6 fill) in the original disk A: safe places for the payload.  Runs (track, side, first sector, count), consumed in order;
# 129 sectors = 66,048 B >= IMG_MAX_LEN (61,440 B).
FLOPPY_FREE = [(0, 0, 2, 9)] + [(t, 0, 1, 10) for t in range(50, 62)]
FLOPPY_FREE_SECTORS = sum(r[3] for r in FLOPPY_FREE)


def floppy_runs(need: int):
    """The first `need` sectors of FLOPPY_FREE as runs (the last one truncated)."""
    out = []
    for tr, side, sec, n in FLOPPY_FREE:
        if need <= 0:
            break
        n = min(n, need)
        out.append((tr, side, sec, n))
        need -= n
    return out


def stx_disk(letter: str) -> bytearray:
    """The original disk as a plain .ST image (80x2x10x512), converted from PP's STX with tools/stx2st.py's parser."""
    sys.path.insert(0, str(ROOT / "tools"))
    import stx2st
    d = stx2st.parse(FLOPPY_DIR / FLOPPY_STX[letter])
    t, sides, spt = FLOPPY_GEO
    img = bytearray(t * sides * spt * SECT)
    for tr in d["tracks"]:
        if tr["Track"] >= t or tr["Side"] >= sides:
            continue
        for sec in tr["Sectors"]:
            n = sec["ID_Sector"]
            if 1 <= n <= spt and sec.get("data") and sec["Size"] == SECT:
                off = (((tr["Track"] * sides + tr["Side"]) * spt) + n - 1) * SECT
                img[off:off + SECT] = sec["data"]
    return img


def sec_off(tr: int, side: int, sec: int) -> int:
    t, sides, spt = FLOPPY_GEO
    return (((tr * sides + side) * spt) + sec - 1) * SECT


BLANK_FILL = (b"\x6d\xb6\xdb" * 171)[:SECT]        # 6d b6 db 6d b6 db ... = the "unused sector" fill of PP's disks


def blank_sector(data: bytes) -> bool:
    """A formatted-but-unused sector: the 6d b6 db fill (as in all 130 free sectors of the original disks)."""
    return len(data) == SECT and data == BLANK_FILL


def floppy_loader(runs) -> bytes:
    """Stage-0 loader, assembled at LOADER_ORG (offsets as if the boot sector were at $7800; the code is position independent): reads each run to consecutive addresses from $B2700 with XBIOS
    Floprd and then jumps to the original boot program.  runs = [(track, side, first sector, count), ...]; the descriptor is
    (track.b, side.b, sector.b, count.b) per run, $ff ends it.  Floprd(buf.l, filler.l, devno.w, sectno.w, trackno.w, sideno.w, count.w) = 20 bytes
    of arguments below the opcode word, pushed in reverse (the original call site $784c-$7868 pushes the same layout; the first version of
    this loader pushed longs for the word arguments and overwrote the original's track/buffer descriptor at $78C4)."""
    lines = ["\tlea\tdesc(pc),a2",
             f"\tlea\t${IB:x}.l,a3",
             ".n:\tmoveq\t#0,d0",
             "\tmove.b\t(a2)+,d0\t\t; track",
             "\tcmpi.b\t#$ff,d0",
             "\tbeq.s\t.done",
             "\tmoveq\t#0,d2",
             "\tmove.b\t(a2)+,d2\t\t; side",
             "\tmoveq\t#0,d1",
             "\tmove.b\t(a2)+,d1\t\t; first sector",
             "\tmoveq\t#0,d3",
             "\tmove.b\t(a2)+,d3\t\t; count",
             "\tmovem.l\td0-d3/a2-a3,-(a7)",
             "\tmove.w\td3,-(a7)\t\t; count",
             "\tmove.w\td2,-(a7)\t\t; side",
             "\tmove.w\td0,-(a7)\t\t; track",
             "\tmove.w\td1,-(a7)\t\t; sector",
             "\tclr.w\t-(a7)\t\t\t; dev A:",
             "\tclr.l\t-(a7)\t\t\t; filler",
             "\tmove.l\ta3,-(a7)\t\t; buf",
             "\tmove.w\t#8,-(a7)\t\t; Floprd",
             "\ttrap\t#$e",
             "\tlea\t20(a7),a7",
             "\ttst.l\td0",
             "\tbne.s\t*\t\t\t\t; read error: hang, as the original's own loop does ($7874)",
             "\tmovem.l\t(a7)+,d0-d3/a2-a3",
             "\tlsl.w\t#8,d3",
             "\tadd.w\td3,d3\t\t\t; count * 512",
             "\tadda.w\td3,a3",
             "\tbra.s\t.n",
             f".done:\tmove.l\t$42e.w,${IB + 4:x}.l\t\t; phystop (TOS, valid only until the original stage 1 wipes $400-$66000 at VBL ~99): the gate of core_floppy.s reads it at IB+4",
             "\tlea.l\t$7f830.l,a6\t\t; the displaced first instruction of the original boot program",
             f"\tbra.w\t${BOOT_PROG:x}\t\t; position independent: TOS runs the boot sector at its disk buffer ($185C on TOS 1.62), not at $7800",
             "desc:"]
    for tr, side, sec, n in runs:
        lines.append(f"\tdc.b\t{tr},{side},{sec},{n}")
    lines.append("\tdc.b\t$ff")
    lines.append("\teven")
    lines.append("\tdc.w\t0\t\t\t\t; checksum adjustment word (fix_boot_checksum)")
    return assemble(LOADER_ORG, lines)


def disk_patch_bytes(p: Patch) -> dict[int, bytes]:
    """A floppy disk patch: one `; disk:` line per edit, the segment whose `org` is that disk offset gives the new bytes."""
    segs = {}
    for letter, off, orig in p.disk:
        seg = [o for o, _ in p.segments if o == off]
        if not seg:
            raise SystemExit(f"{p.name}: no segment at disk offset ${off:x}")
        lines = [l for o, ls in p.segments if o == off for l in ls]
        segs[off] = assemble(off, lines, "\n".join(p.preamble))
    return segs


def fix_boot_checksum(sec: bytes, word: int = 255) -> bytes:
    """TOS boots a sector whose 256 words sum to $1234; adjust word `word` (a padding word inside our loader area) to keep that after an edit."""
    import struct as _s
    w = list(_s.unpack(">256H", sec))
    w[word] = (w[word] - (sum(w) - 0x1234)) & 0xFFFF
    out = _s.pack(">256H", *w)
    assert sum(_s.unpack(">256H", out)) & 0xFFFF == 0x1234
    return out


def cmd_build_floppy(patches, fpatches, out: Path, zip_path: Path | None):
    ram = [p for p in patches if p.site is not None]
    if cmd_verify(patches, fpatches):
        raise SystemExit("floppy build aborted: a site's orig does not match the game")
    fm = floppy_site_mismatches(ram)
    if fm:
        raise SystemExit("floppy build aborted: a RAM site does not match the original floppy's game code:\n  " + "\n  ".join(fm))
    table = IB + 0x120                      # the site table sits right after the core in the floppy layout ($B2820)
    img, sites = build_image(ram, table=table, min_end=table + 0x100, floppy=True)
    need = (len(img) + SECT - 1) // SECT
    if need > FLOPPY_FREE_SECTORS:
        raise SystemExit(f"payload needs {need} sectors, only {FLOPPY_FREE_SECTORS} blank ones are allocated ({FLOPPY_FREE})")
    jobs = floppy_runs(need)
    a = stx_disk("A")
    b_disk_pre = stx_disk("B")
    i = 0
    for tr, side, sec0, n in jobs:
        for sec in range(sec0, sec0 + n):
            if not blank_sector(bytes(a[sec_off(tr, side, sec):sec_off(tr, side, sec) + SECT])):
                raise SystemExit(f"disk A track {tr} side {side} sector {sec} is not blank in the original: refusing to use it")
            a[sec_off(tr, side, sec):sec_off(tr, side, sec) + SECT] = img[i * SECT:(i + 1) * SECT].ljust(SECT, b"\0")
            i += 1
    dpat = [p for p in patches if p.disk]
    for p in dpat:
        segs = disk_patch_bytes(p)
        for letter, off, orig in p.disk:
            dim = a if letter == "A" else b_disk_pre
            if bytes(dim[off:off + len(orig)]) != orig:
                raise SystemExit(f"{p.name}: disk {letter} ${off:x} is not the expected original bytes "
                                 f"({bytes(dim[off:off + len(orig)]).hex()})")
            new = segs[off]
            if len(new) != len(orig):
                raise SystemExit(f"{p.name}: disk {letter} ${off:x}: new {len(new)} B vs orig {len(orig)} B")
            dim[off:off + len(new)] = new
            print(f"disk {letter}+${off:04x} {len(orig):3d} {orig.hex()} -> {new.hex()}   [{p.name}]")
    for s in stage1_sites(patches):
        off = stage1_disk_off(s["addr"], len(s["orig"]))
        if bytes(a[off:off + len(s["orig"])]) != s["orig"]:
            raise SystemExit(f"{s['name']}: disk A ${off:x} is not the expected original bytes ({bytes(a[off:off + len(s['orig'])]).hex()})")
        a[off:off + len(s["new"])] = s["new"]
        print(f"disk A+${off:04x} {len(s['orig']):3d} {s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}, stage-1 site ${s['addr']:05x}]")
    boot = bytearray(a[:SECT])
    boot += bytes(SECT - len(boot)) if len(boot) < SECT else b""
    if bytes(boot[:6]) != b"\x60\x04MOON":
        raise SystemExit(f"disk A boot sector does not start with the expected BRA ($60 04) + 'MOON': {bytes(boot[:6]).hex()}")
    loader = floppy_loader(jobs)
    if LOADER_ORG - 0x7800 + len(loader) > 0x1F4:
        raise SystemExit("stage-0 loader does not fit in the boot sector's free area ($78CA-$79F3)")
    o = LOADER_ORG - 0x7800
    if any(boot[o:0x1F4]):
        raise SystemExit("disk A boot sector: the loader area is not zero in the original")
    e = BOOT_ENTRY - 0x7800
    if bytes(boot[e:e + 6]) != BOOT_ENTRY_ORIG:
        raise SystemExit(f"disk A boot sector: unexpected original entry instruction {bytes(boot[e:e + 6]).hex()}")
    boot[e:e + 6] = bytes.fromhex("6000") + struct.pack(">H", o - (e + 2)) + bytes.fromhex("4e71")   # bra.w loader + nop (position independent)
    boot[o:o + len(loader)] = loader
    a[:SECT] = fix_boot_checksum(bytes(boot), (o + len(loader) - 2) // 2)
    b_disk = b_disk_pre
    out.mkdir(parents=True, exist_ok=True)
    (out / "disk_a.st").write_bytes(bytes(a))
    (out / "disk_b.st").write_bytes(bytes(b_disk))
    print(f"floppy: disk A {len(a)} B, disk B {len(b_disk)} B; payload {len(img)} B ({need} sectors) at "
          + ", ".join(f"t{t}.{sd}s{s}x{n}" for t, sd, s, n in jobs[:4]) + ("..." if len(jobs) > 4 else ""))
    for s in sites:
        print(f"${s['addr']:05x}  {len(s['orig']):4d} {s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]")
    for tpl_name, dst in (("README_FLOPPY.TXT", "README.TXT"), ("PATCHES_FLOPPY.TXT", "PATCHES.TXT")):
        if (PATCHDIR / tpl_name).exists():
            (out / dst).write_text(render_doc((PATCHDIR / tpl_name).read_text()))
    if zip_path is not None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.iterdir()):
                if f.is_file():
                    z.write(f, f"MOONSHR_floppy/{f.name}")
        print(f"wrote {zip_path} ({zip_path.stat().st_size} B)")


# ---- build -----------------------------------------------------------------------------------------------------------------------------------
GAME_FILES = ["HAGA", "FMR273.HST", "LMR273.HST", "MR240R.BMP", "LOG.TXT", "README.TXT"]
FILES_DIR = ["MS1", "MS2", "MSR_S1.FIC"]


def cmd_build(patches, out: Path, fpatches=(), zip_path: Path | None = None):
    if cmd_verify(patches, fpatches):
        raise SystemExit("build aborted: a site's orig does not match the game")
    img, sites = build_image(patches, fnames=[p.name for p in fpatches])
    s1 = stage1_sites(patches)
    runme = build_runme(img, s1)
    shutil.rmtree(out, ignore_errors=True)
    (out / "FILES").mkdir(parents=True)
    for f in GAME_FILES:
        shutil.copy(ORIG / f, out / f)
    for f in FILES_DIR:
        shutil.copy(ORIG / "FILES" / f, out / "FILES" / f)
    (out / "RUNME.TOS").write_bytes(runme)
    tpl = PATCHDIR / "PATCHES.TXT"
    if tpl.exists():
        (out / "PATCHES.TXT").write_text(render_doc(tpl.read_text()))
    ut = PATCHDIR / "README_HD.TXT"      # user docs; PP's own README.TXT follows verbatim
    if ut.exists():
        (out / "README.TXT").write_text(render_doc(ut.read_text()) + "\n\n" + "-" * 78 + "\nPP's README.TXT of the original hard-disk conversion (unchanged):\n" + "-" * 78 + "\n"
                                        + (ORIG / "README.TXT").read_text(errors="replace"))
    apply_file_patches(fpatches, out)
    print(f"built {out} with {len(patches)} patch(es) + {len(fpatches)} file patch(es); payload {len(img)} B at ${IB:x}-${IB + len(img) - 1:x}")
    print(f"{'site':8s} {'len':4s} orig -> new")
    for s in sites:
        print(f"${s['addr']:05x}  {len(s['orig']):4d} {s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]")
    for s in s1:
        print(f"${s['addr']:05x}  {len(s['orig']):4d} {s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}, stage-1: applied by RUNME's copy routine before $78000 runs]")
    if zip_path is not None:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(out.rglob("*")):
                if f.is_file():
                    z.write(f, f"MOONSHR/{f.relative_to(out).as_posix()}")
        print(f"wrote {zip_path} ({zip_path.stat().st_size} B)")


def cmd_live(patches, out: Path):
    if cmd_verify(patches):
        raise SystemExit("live aborted: a site's orig does not match the game")
    img, sites = build_image(patches, live=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".img").write_bytes(img)
    js = [{"addr": s["addr"], "orig": s["orig"].hex(), "new": s["new"].hex(), "name": s["name"]} for s in sites]
    out.with_suffix(".json").write_text(json.dumps({"img_base": IB, "core": CORE, "sites": js}, indent=1))
    print(f"wrote {out.with_suffix('.img')} and {out.with_suffix('.json')} ({len(js)} sites)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--only", nargs="*", default=None)
    b.add_argument("--out", default="build/hd")
    b.add_argument("--zip", nargs="?", const="", default=None, help="also write a zip (default dist/MoonshineRacers_hd_v<VERSION>.zip)")
    b.add_argument("--floppy", action="store_true", help="build the two-disk floppy release (original disk A + our payload) instead of the HD folder")
    b.add_argument("--set", action="append", metavar="NAME=VALUE", help=SET_HELP)
    lv = sub.add_parser("live")
    lv.add_argument("--only", nargs="*", default=None)
    lv.add_argument("--out", default="build/live/patches")
    lv.add_argument("--set", action="append", metavar="NAME=VALUE", help=SET_HELP)
    sub.add_parser("list")
    sub.add_parser("verify")
    v = sub.add_parser("version", help="print the release version (patches/VERSION)")
    v.add_argument("--credit", action="store_true", help="print the credit line `v<VERSION> enhanced by dad_prg`")
    rd = sub.add_parser("doc", help="print a doc file with @VERSION@ / {PATCHES} replaced")
    rd.add_argument("file")
    a = ap.parse_args()
    for kv in getattr(a, "set", None) or []:
        name, sep, val = kv.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z_]\w*", name) or not val.strip():
            raise SystemExit(f"--set needs NAME=VALUE (a patch equate, e.g. SAFE=3), got {kv!r}")
        SET_OVERRIDES[name] = val.strip()
    if a.cmd == "version":
        print(credit_line() if a.credit else release_version())
        return
    if a.cmd == "doc":
        sys.stdout.write(render_doc(Path(a.file).read_text()))
        return
    patches = load_patches()
    fpatches = load_file_patches()
    unused = sorted(set(SET_OVERRIDES) - _SET_USED)
    if unused:
        raise SystemExit(f"--set: no patch declares the equate(s) {unused}")
    if a.cmd == "list":
        cmd_list(patches, fpatches)
        return
    if a.cmd == "verify":
        sys.exit(cmd_verify(patches, fpatches))
    floppy = getattr(a, "floppy", False)       # the `live` subparser has no --floppy
    if a.only is None:
        sel = [p for p in patches if p.default and in_build(p, floppy) and (p.site is not None or p.media == "floppy")]
        fsel = [p for p in fpatches if p.default]
    else:
        names = set(a.only)
        unknown = names - {p.name for p in patches} - {p.name for p in fpatches}
        if unknown:
            raise SystemExit(f"unknown patch(es): {sorted(unknown)}")
        wrong = sorted(p.name for p in patches if p.name in names and p.media is not None and p.media != ("floppy" if floppy else "hd"))
        if wrong:
            raise SystemExit(f"{'HD' if floppy else 'floppy'}-only patch(es) {wrong}: " + ("use `build` without --floppy" if floppy else "use `build --floppy` (work/notes/floppy.md)"))
        sel = [p for p in patches if p.name in names or (floppy and p.name in FLOPPY_REQUIRED)]
        fsel = [p for p in fpatches if p.name in names]
    msgs = check_selection(sel + fsel, {p.name for p in patches} | {p.name for p in fpatches})
    if msgs:
        raise SystemExit("invalid patch selection:\n  " + "\n  ".join(msgs))
    if a.cmd == "build":
        zp = None
        if a.zip is not None:
            zp = Path(a.zip) if a.zip else ROOT / "dist" / (f"MoonshineRacers_{'floppy' if floppy else 'hd'}_v{release_version()}.zip")
        if floppy:
            cmd_build_floppy(sel, fsel, ROOT / (a.out if a.out != "build/hd" else "build/floppy"), zp)
        else:
            cmd_build(sel, ROOT / a.out, fsel, zp)
    else:
        if fsel and a.only is not None:
            raise SystemExit("file patches (HAGA) are not applicable to `live`: they are applied at build time")
        cmd_live(sel, ROOT / a.out)


if __name__ == "__main__":
    main()
