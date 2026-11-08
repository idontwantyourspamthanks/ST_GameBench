#!/usr/bin/env python3
"""Midwinter 1 patch delivery tool (ported from games/midwinter2/tools/mw2patch.py).

Patches are vasm sources in patches/ (see patches/README.md for the format and the boot
mechanism).  The tool assembles them, verifies every site's expected ORIGINAL bytes against
the disk images (FILES/MWA: the resident game, loaded from the game's own file system)
cross-checked against work/dumps/ram1mb_options.bin, and produces a patched COPY of the
game in build/game (originals are never touched).

File patches (`; image: HAGA`, `; edit: <offset> <orig hex>`, `org HB+$<offset>`) edit
PP's resident loader service in the build copy's HAGA file.

    python3 tools/mw1patch.py build [--only NAME ...] [--out build/game]
    python3 tools/mw1patch.py build --floppy [--only NAME ...] [--out build/floppy] [--zip [PATH]]
    python3 tools/mw1patch.py list
    python3 tools/mw1patch.py verify
    python3 tools/mw1patch.py files        # the game's own directory tables, checksum-verified
    python3 tools/mw1patch.py live [--only NAME ...] [--out build/live/patches]
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNME_SRC = ROOT / "work" / "dumps" / "RUNME_unpacked.tos"
RAMDUMP = ROOT / "work" / "dumps" / "ram1mb_options.bin"   # 1 MB STE, TOS 1.62, Game Options screen
HAGA_DUMP_BASE = 0xF8000                                    # HAGA RAM base inside that dump (1 MB machine)
PATCHDIR = ROOT / "patches"
VASM = "vasmm68k_mot"
NOT_GAME = {"work", "tools", "build", "dist", "patches", ".omp", "tos", "__pycache__", "FILES"}

# ---- RUNME edit points (offsets into the unpacked image's text) ------------
TEXT_LEN = 0x44BA
STAGE_TXT = 0x3AA          # text offset of 'jmp $d000.l' (stack-phase fallthrough into the boot stub)
STAGE_ORIG = bytes.fromhex("4ef90000d000")
TAIL_TXT = 0x482           # PP's patcher tail: 'jmp $800.w' (game entry) + 2 zero pad bytes
TAIL_ORIG = bytes.fromhex("4ef808000000")
# Payload: $B3000-$BAFFF (32 KB): core + site table + blobs.  It rides in RUNME's data
# segment, so the bss (and every address that points into it) moves up by N.
PAYLOAD_LEN = 0x8000
OLD_BSS = 0x44D0           # text-relative start of the original bss (= end of the original data)
# The copy routine (first thing in the appended data) copies the payload image to
# $B3000, then jumps to the boot stub.  Layout of the appended block:
#   [COPY_ROUTINE 26 B][BSS_PTRS 8 B][payload image PAYLOAD_LEN B]
COPY_LEN, PTRS_LEN = 26, 8
N = COPY_LEN + PTRS_LEN + PAYLOAD_LEN       # bytes appended to the data segment
COPY_ROUTINE = bytes.fromhex(
    "41fa%04x" % (COPY_LEN + PTRS_LEN - 2)   # lea  (routine+34)(pc),a0 -> image
    + "43f9000b3000"                         # lea  $b3000.l,a1
    + "303c%04x" % (PAYLOAD_LEN // 4 - 1) +  # move.w #longs-1,d0
    "22d8"                                   # move.l (a0)+,(a1)+
    "51c8fffc"                               # dbra d0,-4
    "4ef90000d000")                          # jmp  $d000.l      (boot stub)
assert len(COPY_ROUTINE) == COPY_LEN
assert PAYLOAD_LEN % 4 == 0 and PAYLOAD_LEN // 4 - 1 <= 0xFFFF
# The four pc-relative `lea d(pc),aN` in RUNME that address bss: text offset ->
# (register number, text-relative bss target).  A signed 16-bit displacement cannot span
# N = 32 KB+ any more, so each becomes `movea.l d(pc),aN` (same 4 bytes, same registers,
# no flag change) loading a relocated pointer from BSS_PTRS, which sits within +-32 KB of
# every one of them.  A full-text scan (check_bss_pcrel_complete) proves these are the only
# pc-relative operands whose target is >= OLD_BSS (work/notes/loading.md section 7).
BSS_LEAS = {0x98: (1, 0x46F0), 0xBBE: (2, 0x46F0), 0x4184: (2, 0x44D0), 0x4196: (1, 0x44D0)}
BSS_PTR_TARGETS = (0x46F0, 0x44D0)         # BSS_PTRS slot i holds (target + N), relocated by the loader
# d16(pc)-looking words >= OLD_BSS that are NOT instructions: displacement words of
# `move.w $13a(a6),dN` ($506, $5d8), the path string "C:\\GAMEX.." ($706), the address word of
# `move.w #$6004,$bfa.l` ($c86) and $FFFA fill words ($41c4, $438c).
NOT_CODE = {0x506, 0x5D8, 0x706, 0xC86, 0x41C4, 0x438C}

# ---- $B3000 image layout ---------------------------------------------------
IMG_BASE = 0xB3000
ORG_TRAMP, ORG_HOOK, ORG_APPLY = 0xB3000, 0xB3070, 0xB3090
CORE_END = 0xB3100          # trampoline/hookexit/apply occupy $B3000-$B30FF
TABLE, TABLE_END = 0xBA000, 0xBB000   # site table + byte pool: 4 KB at the top of the payload
BLOB_MIN, BLOB_MAX = 0xB3100, TABLE - 1   # blob/data orgs, inclusive last byte
MARKER = 0xB2FF8
HOOK_SITE = 0x10D6C        # sub_010cd2 single success exit: move.w (a7)+,$62b8.l (6-byte splice)
HOOK_ORIG = bytes.fromhex("33df000062b8")
CORE_ORGS = {ORG_TRAMP, ORG_HOOK, ORG_APPLY}

# ---- PP's own boot patches (work/notes/loading.md section 4): RAM = image + these ----
# Applied by PP's patcher block (RUNME text $3b0-$482, running from the stack copy); all
# 12 verified against the Game Options RAM dump.  PP's other writes ($69ec, $3ed06, ...) are
# not in the resident game (see loading.md).
PP_PATCHES = {
    0x64D2: "4ef80392", 0x1011E: "4ef8031c", 0x10172: "4ef80308", 0x101C6: "4ef80308",
    0x1024A: "4ef802fc", 0x10E5C: "4ef8025c", 0x10F86: "4ef8032e", 0x1102E: "4e75",
    0x110FE: "4ef8027c", 0x111A6: "4ef80328", 0x11344: "4e75", 0x12050: "4e75",
}
PP_PATCHES = {a: bytes.fromhex(b) for a, b in PP_PATCHES.items()}

# ---- the game's own file system ----------------------------------------------------
# Disk images are raw 10-sector single-sided dumps: offset = (abs_sector-1)*512 (abs_sector is
# 1-based, linear over tracks).  The boot stub (loaded by the boot sector from MWA sector 2) has
# a one-entry table for the stage-2 program; stage-2 has a 3-entry table (files at $48632)
# of which entry 1 is the whole resident game.  The game then loads everything else through
# its own routine sub_010cd2 using directory tables embedded in the resident game
# ($258a6 = MWA, $2590c = MWB), entries {start.w, nsect.w, length.l, xor16.w} (10 bytes).
SECTOR = 512
STUB_TABLE_OFF = 0x200 + (0xD47E - 0xCFE4)       # stub file offset in MWA + table position (loaded at $CFE4)
STAGE2_RAM = 0x3DF28                              # stage-2 program load address
STAGE2_TABLE = 0x48632                            # its file table
GAME_RAM = 0x7E4                                  # resident game load address (file 1 of stage-2 table)
DIR_TABLES = {"MWA": 0x258A6, "MWB": 0x2590C}     # RAM addresses of the game's directory tables


def img_bytes(name: str) -> bytes:
    return (ROOT / "FILES" / name).read_bytes()


def sector_file(d: bytes, start: int, length: int) -> bytes:
    return d[(start - 1) * SECTOR:(start - 1) * SECTOR + length]


def xor_cksum(b: bytes) -> int:
    """The game's directory checksum (sub_010d80): XOR of the big-endian words."""
    c = 0
    for i in range(0, len(b) - 1, 2):
        c ^= (b[i] << 8) | b[i + 1]
    if len(b) & 1:
        c ^= b[-1] << 8
    return c


_cache: dict = {}


def stages():
    """(stage-2 entry, game entry) as (start, nsect, length) from the images' own tables."""
    if "stages" not in _cache:
        a = img_bytes("MWA")
        s1 = struct.unpack_from(">HHI", a, STUB_TABLE_OFF)                     # stub table entry 0
        stage2 = sector_file(a, s1[0], s1[2])
        t = STAGE2_TABLE - STAGE2_RAM
        ents = [struct.unpack_from(">HHIH", stage2, t + 10 * i) for i in range(3)]
        _cache["stages"] = (s1, ents, stage2)
    return _cache["stages"]


def game_bytes() -> bytes:
    """The resident game exactly as the stage-2 loader reads it (MWA, stage-2 table entry 1)."""
    if "game" not in _cache:
        _, ents, _ = stages()
        s, n, ln, _x = ents[1]
        _cache["game"] = sector_file(img_bytes("MWA"), s, ln)
    return _cache["game"]


def dir_entries(img: str):
    """Entries of the game's directory table for `img`: (idx, start, nsect, length, cksum).
    The table has no terminator: it ends at the first entry whose sector count is not
    ceil(length/512) or that leaves the image."""
    g = game_bytes()
    p = DIR_TABLES[img] - GAME_RAM + 2
    out = []
    for i in range(80):
        s, ns, ln, x = struct.unpack_from(">HHIH", g, p + 10 * i)
        if s == 0 or ln == 0 or ns != (ln + SECTOR - 1) // SECTOR or (s - 1 + ns) * SECTOR > 409600:
            break
        out.append((i, s, ns, ln, x))
    return out


def image_file(img: str, fileno: int) -> bytes:
    key = (img, fileno)
    if key not in _cache:
        e = [e for e in dir_entries(img) if e[0] == fileno]
        if not e:
            raise SystemExit(f"{img} file {fileno} not in the game's directory table")
        _cache[key] = sector_file(img_bytes(img), e[0][1], e[0][3])
    return _cache[key]


def resident_range():
    return GAME_RAM, GAME_RAM + len(game_bytes())


def in_resident(addr: int, ln: int) -> bool:
    lo, hi = resident_range()
    return lo <= addr and addr + ln <= hi


def image_at(addr: int, ln: int, load=None):
    """File bytes at RAM [addr, addr+ln): the resident game, or the declared overlay `load`."""
    if load is None:
        if not in_resident(addr, ln):
            return None
        return game_bytes()[addr - GAME_RAM: addr - GAME_RAM + ln]
    img, fileno, dest = load
    b = image_file(img, fileno)
    if not (dest <= addr and addr + ln <= dest + len(b)):
        return None
    return b[addr - dest: addr - dest + ln]


def expected_ram(addr: int, ln: int, load=None, raw: bool = False):
    """Bytes RAM holds right after the load (image + PP's boot patches for the resident game).
    raw=True: the image bytes only (a floppy boot has none of PP's patches)."""
    b = image_at(addr, ln, load)
    if b is None:
        return None
    b = bytearray(b)
    if load is None and not raw:
        for pa, pb in PP_PATCHES.items():
            if addr < pa + len(pb) and pa < addr + ln:
                for k, v in enumerate(pb):
                    if 0 <= pa + k - addr < ln:
                        b[pa + k - addr] = v
    return bytes(b)


# ---- patch source parsing --------------------------------------------------
ORG_RE = re.compile(r"^\s*org\s+\$?([0-9a-fA-F]+)\s*$", re.I)
HDR_RE = re.compile(r"^;\s*([a-z]+):\s*(.*)$")
# File patches (`; image: HAGA`): `org HB+$<file offset>` segments assembled with HB = the RAM
# address HAGA is relocated to (HAGA_RAM_*), `; edit:` lines give the file offset and the
# expected ORIGINAL bytes.
HB_ORG_RE = re.compile(r"^\s*org\s+HB\s*\+\s*\$([0-9a-fA-F]+)\s*$", re.I)


class Patch:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.default = True
        self.site = None
        self.orig = None          # declared (optional)
        self.phase = None         # None = auto
        self.load = None          # deferred sites: (image, directory file no, RAM dest) of the carrying file
        self.data = []            # (addr, len) reservations
        self.segments = []        # (org, source lines)
        self.preamble = []        # equ lines before the first org
        self.image = None         # file patch: game file (e.g. HAGA) edited in place
        self.media = None         # None = every build; "floppy" = only `build --floppy`
        self.edits = []           # file patch: (file offset, expected original bytes)
        self.fsegments = []       # file patch: (file offset, source lines)
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
                elif k == "site": self.site = int(v.lstrip("$"), 16)
                elif k == "orig": self.orig = bytes.fromhex(v.replace(" ", ""))
                elif k == "phase": self.phase = v.strip().lower()
                elif k == "load":
                    i, f, d = v.split()
                    self.load = (i, int(f, 0), int(d.lstrip("$"), 16))
                elif k == "data":
                    a, l = v.split()
                    self.data.append((int(a.lstrip("$"), 16), int(l, 0)))
                elif k == "image": self.image = v.strip()
                elif k == "media":
                    if v.strip().lower() != "floppy":
                        raise SystemExit(f"{path}: media must be `floppy`")
                    self.media = "floppy"
                elif k == "edit":
                    a, b = v.split(None, 1)
                    self.edits.append((int(a.lstrip("$"), 16), bytes.fromhex(b.replace(" ", ""))))
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
        if self.phase:
            return self.phase
        return "boot" if self.load is None else "deferred"


def load_patches():
    ps = []
    for f in sorted(PATCHDIR.glob("*.s")):
        if f.name == "core.s":
            continue
        p = Patch(f)
        if p.site is not None:
            ps.append(p)
    return ps


def load_file_patches():
    ps = []
    for f in sorted(PATCHDIR.glob("*.s")):
        if f.name == "core.s":
            continue
        p = Patch(f)
        if p.image is not None:
            if p.site is not None:
                raise SystemExit(f"{f.name}: `image:` and `site:` are mutually exclusive")
            ps.append(p)
    return ps


# ---- assembly ---------------------------------------------------------------
def assemble(org: int, lines: list[str], equ: str = "") -> bytes:
    src = equ + f"\n\torg\t${org:x}\n" + "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "seg.s"
        s.write_text(src)
        out = Path(td) / "seg.bin"
        r = subprocess.run([VASM, "-Fbin", "-m68000", "-quiet", "-o", str(out), str(s)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"vasm failed:\n{src}\n{r.stderr}")
        return out.read_bytes()


def core_segments() -> dict[int, bytes]:
    p = Patch(PATCHDIR / "core.s")
    equ = "\n".join(p.preamble)
    segs = {}
    for org, lines in p.segments:
        segs[org] = assemble(org, lines, equ)
    if set(segs) != CORE_ORGS:
        raise SystemExit(f"core.s orgs {sorted(segs)} != {sorted(CORE_ORGS)}")
    return segs


# ---- file patches (HAGA) ---------------------------------------------------------
# PP's resident loader service (the code behind every Fopen/Fread/Fwrite the game does,
# including the grey "loading" palette fades) is NOT in RUNME.TOS: it is the file HAGA, which
# RUNME copies verbatim to the top of RAM (phystop-$8000 on a 1 MB machine: $F8000; 2 MB:
# $1F8000; 4 MB and up: $3F8000), so absolute RAM addresses cannot be patched.  A file patch
# edits HAGA bytes in the build copy instead:
#     ; image: HAGA
#     ; edit: $<file offset> <expected original bytes, hex>      (repeatable)
#             org HB+$<file offset>        ; one segment per edit, same length
# Segments are assembled with HB = each base and must come out byte-identical, i.e. position
# independent.  HAGA is byte-identical to Midwinter 2's (md5 b34607ed...), so MW2's patches
# apply unchanged.  `verify` checks every edit's original bytes against the shipped file AND
# the in-game RAM dump; `build` refuses to apply over different bytes.
HAGA_BASES = (0x3F8000, 0x1F8000, 0xF8000)
FILE_IMAGES = ("HAGA",)


def file_patch_bytes(p: Patch) -> dict[int, bytes]:
    """New bytes per edit offset, assembled at every HAGA base (must agree)."""
    segs = {}
    for off, lines in p.fsegments:
        outs = [assemble(hb + off, lines, f"HB\tequ\t${hb:x}\n" + "\n".join(p.preamble))
                for hb in HAGA_BASES]
        if any(o != outs[0] for o in outs):
            raise SystemExit(f"{p.name}: segment HB+${off:x} is not position independent "
                             f"({[o.hex() for o in outs]} at {[hex(b) for b in HAGA_BASES]})")
        if off in segs:
            raise SystemExit(f"{p.name}: two segments at HB+${off:x}")
        segs[off] = outs[0]
    return segs


def cmd_verify_files(fpatches) -> int:
    bad = 0
    ram = RAMDUMP.read_bytes()
    used = []                                  # (image, start, end, name)
    for p in fpatches:
        print(f"{p.name:18s} image {p.image}  {len(p.edits)} edit(s)")
        if p.image not in FILE_IMAGES:
            raise SystemExit(f"{p.name}: unsupported image {p.image!r} (supported: {FILE_IMAGES})")
        segs = file_patch_bytes(p)
        data = (ROOT / p.image).read_bytes()
        if {o for o, _ in p.edits} != set(segs):
            print(f"    edit offsets ${sorted(o for o, _ in p.edits)} != segment offsets ${sorted(segs)}")
            bad += 1
            continue
        for off, orig in p.edits:
            new = segs[off]
            ib = data[off:off + len(orig)]
            db = ram[HAGA_DUMP_BASE + off:HAGA_DUMP_BASE + off + len(orig)]
            ok = ib == orig and db == orig and len(new) == len(orig)
            print(f"    HB+${off:04x} len {len(orig):2d}  orig {orig.hex()}")
            print(f"        file  {ib.hex()}  ({'match' if ib == orig else 'MISMATCH'})")
            print(f"        dump  {db.hex()}  ({'match' if db == orig else 'MISMATCH'})")
            print(f"        new   {new.hex()}  ({'same length' if len(new) == len(orig) else 'LENGTH MISMATCH'})")
            for img, a, b, n in used:
                if img == p.image and off < b and a < off + len(orig):
                    print(f"        OVERLAP with {n} (${a:x}-${b:x})")
                    ok = False
            used.append((p.image, off, off + len(orig), p.name))
            if not ok:
                bad += 1
    return bad


def apply_file_patches(fpatches, out: Path):
    """Edit the build copy's game files in place (originals are never touched)."""
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


# ---- image build -------------------------------------------------------------
def build_image(patches: list[Patch]):
    core = core_segments()
    for org in (ORG_TRAMP, ORG_HOOK, ORG_APPLY):
        nxt = {ORG_TRAMP: ORG_HOOK, ORG_HOOK: ORG_APPLY, ORG_APPLY: CORE_END}[org]
        if org + len(core[org]) > nxt:
            raise SystemExit(f"core segment ${org:x} overflows (${len(core[org])} B)")
    sites = []
    for p in patches:
        seg = [s for s in p.segments if s[0] == p.site]
        if not seg:
            raise SystemExit(f"{p.name}: no org ${p.site:x} segment")
        new = assemble(p.site, seg[0][1], "\n".join(p.preamble))
        orig = p.orig if p.orig is not None else expected_ram(p.site, len(new), p.load, p.media == "floppy")
        if orig is None:
            raise SystemExit(f"{p.name}: site ${p.site:x} in no known load range "
                             f"(resident ${resident_range()[0]:x}-${resident_range()[1]:x}, or declare `; load:`)")
        if len(new) > len(orig):
            raise SystemExit(f"{p.name}: new bytes longer than orig")
        if len(new) < len(orig):
            new = new + b"\x4e\x71" * ((len(orig) - len(new)) // 2)
        if len(new) != len(orig):
            raise SystemExit(f"{p.name}: size mismatch")
        sites.append(dict(name=p.name, addr=p.site, orig=orig, new=new, phase=p.phase_of(), media=p.media))
    if any(s["phase"] == "deferred" for s in sites):
        sites.append(dict(name="<load-hook>", addr=HOOK_SITE, orig=HOOK_ORIG,
                          # jmp, not jsr: hookexit pops the original exit frame
                          # ($62b8 word, 15 regs) and must see it at (a7).
                          new=bytes.fromhex("4ef9000b3070"), phase="boot"))
    by_addr = sorted(sites, key=lambda s: s["addr"])
    for s, t in zip(by_addr, by_addr[1:]):
        if s["addr"] + len(s["orig"]) > t["addr"]:
            raise SystemExit(f"site overlap: {s['name']} ${s['addr']:x}+{len(s['orig'])} "
                             f"vs {t['name']} ${t['addr']:x}")
    # table + pool
    n = len(sites)
    tbl_len = n * 16 + 4
    pool = bytearray()
    ptrs = []
    for s in sites:
        o = len(pool); pool += s["orig"]
        nw = len(pool); pool += s["new"]
        ptrs.append((TABLE + tbl_len + o, TABLE + tbl_len + nw))
    if TABLE + tbl_len + len(pool) > TABLE_END:
        raise SystemExit("site table + byte pool overflow $BA000-$BAFFF")
    img = bytearray(PAYLOAD_LEN)
    for org, b in core.items():
        img[org - IMG_BASE: org - IMG_BASE + len(b)] = b
    for i, s in enumerate(sites):
        o = TABLE - IMG_BASE + i * 16
        struct.pack_into(">IHHII", img, o, s["addr"], len(s["orig"]),
                         0 if s["phase"] == "boot" else 1, ptrs[i][0], ptrs[i][1])
    img[TABLE - IMG_BASE + n * 16: TABLE - IMG_BASE + n * 16 + 4] = b"\0\0\0\0"
    img[TABLE - IMG_BASE + tbl_len: TABLE - IMG_BASE + tbl_len + len(pool)] = pool
    # blobs + reservations
    placed = [(ORG_TRAMP, ORG_HOOK), (ORG_HOOK, ORG_APPLY), (ORG_APPLY, CORE_END),
              (TABLE, TABLE + tbl_len + len(pool))]
    for p in patches:
        for org, lines in p.segments:
            if org == p.site:
                continue
            if not (BLOB_MIN <= org <= BLOB_MAX):
                raise SystemExit(f"{p.name}: org ${org:x} outside blob area "
                                 f"${BLOB_MIN:x}-${BLOB_MAX:x}")
            b = assemble(org, lines, "\n".join(p.preamble))
            if org + len(b) > BLOB_MAX + 1:
                raise SystemExit(f"{p.name}: blob overflows image")
            placed.append((org, org + len(b)))
            img[org - IMG_BASE: org - IMG_BASE + len(b)] = b
        for a, l in p.data:
            placed.append((a, a + l))
    placed.sort()
    for (a0, a1), (b0, b1) in zip(placed, placed[1:]):
        if a1 > b0:
            raise SystemExit(f"image overlap: ${a0:x}-${a1:x} vs ${b0:x}-${b1:x}")
    return bytes(img), sites


# ---- verification ------------------------------------------------------------
def check_site(addr: int, orig: bytes, load=None, raw: bool = False):
    """Return (ok, image_ok, dump_ok, image_bytes, dump_bytes).  The RAM dump is the Game
    Options screen of an unpatched 1 MB boot: every boot site and every site of a file loaded
    before that screen is in it (a deferred site of a later file reads the dump's zeros/old data:
    reported as `not loaded yet`)."""
    ib = image_at(addr, len(orig), load)
    exp = expected_ram(addr, len(orig), load, raw)
    ram = RAMDUMP.read_bytes()
    db = ram[addr:addr + len(orig)]
    if raw:                      # floppy-only site: the HD dump carries PP's patches, so it is not comparable
        return ib == orig, ib == orig, True, ib, db
    return ib == orig and exp == orig and db == orig, ib == orig, db == exp, ib, db


def cmd_verify(patches, fpatches=()):
    bad = 0
    for p in patches:
        seg = [s for s in p.segments if s[0] == p.site]
        new = assemble(p.site, seg[0][1], "\n".join(p.preamble)) if seg else b""
        raw = p.media == "floppy"
        orig = p.orig if p.orig is not None else (
            expected_ram(p.site, len(new), p.load, raw) if new else b"")
        ok, iok, dok, ib, db = check_site(p.site, orig, p.load, raw)
        where = "resident game (MWA file 1)" if p.load is None else \
            f"{p.load[0]} file {p.load[1]} @ ${p.load[2]:x}"
        print(f"{p.name:18s} site ${p.site:05x} phase {p.phase_of():8s} src {where} len {len(orig)}")
        print(f"    declared orig : {orig.hex()}")
        print(f"    image  bytes  : {ib.hex() if ib is not None else None}  ({'match' if iok else 'MISMATCH'})")
        print(f"    ramdump bytes : {db.hex()}  ({'n/a: floppy-only site, the dump is an HD boot' if raw else 'match' if dok else 'MISMATCH'})")
        if not ok:
            bad += 1
    bad += cmd_verify_files(fpatches)
    print("verify:", "ALL OK" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


def cmd_list(patches, fpatches=()):
    print(f"{'name':18s} {'default':8s} {'site':8s} {'phase':9s} {'len':4s} blobs/data")
    for p in patches:
        blobs = ",".join(f"${o:x}" for o, _ in p.segments if o != p.site) or "-"
        data = ",".join(f"${a:x}+{l}" for a, l in p.data) or "-"
        seg = [s for s in p.segments if s[0] == p.site]
        ln = len(assemble(p.site, seg[0][1], "\n".join(p.preamble))) if seg else 0
        dflt = ("yes" if p.default else "no") + (" (floppy)" if p.media else "")
        print(f"{p.name:18s} {dflt:8s} ${p.site:05x}  "
              f"{p.phase_of():9s} {ln:4d} {blobs} / {data}")
    for p in fpatches:
        offs = ",".join(f"${o:x}" for o, _ in p.edits)
        print(f"{p.name:18s} {'yes' if p.default else 'no':8s} {p.image}+{offs}  "
              f"(file patch, {sum(len(b) for _, b in p.edits)} B)")


def cmd_files():
    """Print the stage tables and the game's directory tables with checksums verified."""
    s1, ents, stage2 = stages()
    print(f"boot stub table (MWA ${STUB_TABLE_OFF:x}): entry 0 start sector {s1[0]} nsect {s1[1]} length {s1[2]:#x} -> stage-2 @ ${STAGE2_RAM:x}")
    for i, e in enumerate(ents):
        print(f"stage-2 table ${STAGE2_TABLE:x}[{i}]: start {e[0]} nsect {e[1]} length {e[2]:#x} word {e[3]:#x}")
    lo, hi = resident_range()
    print(f"resident game: MWA sectors {ents[1][0]}.. -> RAM ${lo:x}-${hi:x}")
    for img in ("MWA", "MWB"):
        d = img_bytes(img)
        es = dir_entries(img)
        ok = sum(1 for _, s, ns, ln, x in es if xor_cksum(sector_file(d, s, ln)) == x)
        print(f"{img} directory table ${DIR_TABLES[img]:x}: {len(es)} entries, xor checksums matching the raw image bytes: {ok}")
        for i, s, ns, ln, x in es:
            c = xor_cksum(sector_file(d, s, ln))
            print(f"  {i:3d} start {s:4d} nsect {ns:3d} len {ln:6d} img offset {(s - 1) * SECTOR:#08x} cksum {x:04x} "
                  f"{'ok' if c == x else f'DIFF (raw {c:04x})'}")


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


def build_runme(img: bytes) -> bytes:
    src = RUNME_SRC.read_bytes()
    text_len, data_len, bss_len = struct.unpack_from(">III", src, 2)
    assert (text_len, data_len) == (TEXT_LEN, 22), (hex(text_len), data_len)
    text = bytearray(src[28:28 + TEXT_LEN])
    data = src[28 + TEXT_LEN:28 + TEXT_LEN + 22]
    rel_off = 28 + TEXT_LEN + 22
    offs, rel_end = decode_reloc(src[rel_off:])
    assert rel_end == len(src) - rel_off
    assert encode_reloc(offs) == src[rel_off:], "reloc table does not round-trip"
    # 1. staging: jmp to the copy routine at the head of the appended data
    assert bytes(text[STAGE_TXT:STAGE_TXT + 6]) == STAGE_ORIG, "RUNME text: unexpected bytes at the staging site"
    struct.pack_into(">HI", text, STAGE_TXT, 0x4EF9, TEXT_LEN + 22)
    # 2. patcher tail (jmp $800.w + 2 zero pad bytes) -> trampoline
    assert bytes(text[TAIL_TXT:TAIL_TXT + 6]) == TAIL_ORIG, "RUNME text: unexpected bytes at PP's patcher tail"
    text[TAIL_TXT:TAIL_TXT + 6] = bytes.fromhex("4ef9000b3000")
    # 3. bss moved by N.  pc-relative `lea d(pc),aN` into bss cannot reach any more:
    #    each becomes `movea.l d(pc),aN` from a relocated pointer slot (BSS_PTRS).
    check_bss_pcrel_complete(text)
    slot = {tgt: TEXT_LEN + 22 + COPY_LEN + 4 * i for i, tgt in enumerate(BSS_PTR_TARGETS)}
    for t, (reg, tgt) in BSS_LEAS.items():
        op, d = struct.unpack_from(">Hh", text, t)
        assert op == 0x41FA | reg << 9 and t + 2 + d == tgt, f"text ${t:x} is not lea ${tgt:x}(pc),a{reg}"
        disp = slot[tgt] - (t + 2)
        assert 0 <= disp <= 0x7FFF, f"pointer slot out of reach of text ${t:x}"
        struct.pack_into(">Hh", text, t, 0x207A | reg << 9, disp)    # movea.l d(pc),aN
    for o in offs:
        v = struct.unpack_from(">I", text, o)[0]
        if v >= OLD_BSS:
            struct.pack_into(">I", text, o, v + N)
    ptrs = b"".join(struct.pack(">I", tgt + N) for tgt in BSS_PTR_TARGETS)
    assert len(ptrs) == PTRS_LEN
    offs.append(STAGE_TXT + 2)      # the staging jmp operand (value = data start)
    offs.extend(slot.values())      # the bss pointers are absolute: the loader relocates them
    offs.sort()
    newdata = data + COPY_ROUTINE + ptrs + img
    assert len(newdata) == 22 + N
    hdr = bytearray(src[:28])
    struct.pack_into(">I", hdr, 6, len(newdata))
    return bytes(hdr) + bytes(text) + newdata + encode_reloc(offs)


def check_bss_pcrel_complete(text: bytes):
    """Every d16(pc) operand (ea mode 7/2) whose target is >= OLD_BSS must be listed in
    BSS_LEAS (or be a known non-instruction word), else it would silently keep a stale
    displacement when the bss moves.  d8(pc,Xn) (mode 7/3) is scanned too."""
    for t in range(0, TEXT_LEN - 3, 2):
        op, d = struct.unpack_from(">Hh", text, t)
        if op & 0x3F == 0x3A and t + 2 + d >= OLD_BSS and t not in BSS_LEAS and t not in NOT_CODE:
            raise SystemExit(f"RUNME text ${t:x}: unlisted pc-relative reference to ${t + 2 + d:x} (op {op:04x})")
        if op & 0x3F == 0x3B and not (d & 0x100):
            d8 = d & 0xFF
            d8 -= 256 if d8 > 127 else 0
            if t + 2 + d8 >= OLD_BSS and t not in NOT_CODE:
                raise SystemExit(f"RUNME text ${t:x}: unlisted d8(pc,Xn) reference to ${t + 2 + d8:x} (op {op:04x})")


# ---- build -------------------------------------------------------------------
def cmd_build(patches, out: Path, fpatches=()):
    if cmd_verify(patches, fpatches):
        raise SystemExit("build aborted: a site's orig does not match the game")
    img, sites = build_image(patches)
    runme = build_runme(img)
    out.mkdir(parents=True, exist_ok=True)
    for f in ROOT.iterdir():
        if f.name in NOT_GAME or f.is_dir() or f.suffix.lower() in (".md", ".zip", ".py"):
            continue
        shutil.copy(f, out / f.name)
    shutil.copytree(ROOT / "FILES", out / "FILES", dirs_exist_ok=True)
    (out / "RUNME.TOS").write_bytes(bytes(runme))
    apply_file_patches(fpatches, out)
    print(f"built {out} with {len(patches)} patch(es) + {len(fpatches)} file patch(es); "
          f"payload {len(img)} B at $B3000")
    print(f"{'site':8s} {'phase':9s} {'len':4s} orig -> new")
    for s in sites:
        print(f"${s['addr']:05x}  {s['phase']:9s} {len(s['orig']):4d} "
              f"{s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]")


def cmd_live(patches, out: Path):
    """Write what the boot installer would put in RAM, for applying a patch set to a running
    snapshot: the payload image (`<out>.img`, load at $B3000) and the site bytes (`<out>.json`).
    The load hook is omitted: in a snapshot every overlay is already loaded."""
    if cmd_verify(patches):
        raise SystemExit("live aborted: a site's orig does not match the game")
    img, sites = build_image(patches)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".img").write_bytes(bytes(img))
    js = [{"addr": s["addr"], "orig": s["orig"].hex(), "new": s["new"].hex(), "name": s["name"]}
          for s in sites if s["name"] != "<load-hook>"]
    out.with_suffix(".json").write_text(json.dumps({"img_base": IMG_BASE, "sites": js}, indent=1))
    print(f"wrote {out.with_suffix('.img')} and {out.with_suffix('.json')} ({len(js)} sites)")


# ---- floppy build ------------------------------------------------------------
# FILES/MWA is a working floppy image.  Boot sector (word sum $1234, "midwint.blk") loads 12
# sectors from sector 2 to $CFE4 (the boot stub: a TOS-header-prefixed program whose code
# starts at $D000) and jumps to $D000.  The stub's own FDC code loads the stage-2 program (75566 B,
# sector 558) to $3DF28 and runs it at $3DF44; stage-2 loads the title pictures and the whole
# resident game (its table entry 1) to $7E4 with its own FDC code and ends in `jmp $800.l` at
# $3E1AA.  PP's RUNME, his patcher ($3b0-$482) and the HAGA service are not involved, so none of
# PP_PATCHES exist in RAM on floppy (work/notes/floppy.md): the game runs its original FDC driver.
#
# Injection: the payload ($B3000 image) is stored in 64 free sectors of MWA (706..769; sectors
# 706..800 are format filler $E5).  A 44-byte stage 1, written over two dead stage-2 routines
# ($3EE3C-$3EE73, 56 bytes, referenced by nothing in the program), fills in stage-2's file-table
# entry 2 (the second title picture, already shown by then) with {start 706, 64 sectors, $8000 B},
# calls stage-2's own loader (sub_03ec9e: file number in $14(a6), destination in $1a(a6),
# a6 = $48650) and jumps to $B3000.  Stage-2's final `jmp $800.l` becomes `jmp $3EE3C.l`.  The
# trampoline (core.s) verifies and applies the boot sites exactly as in the HD build and ends in
# `jmp $800.w`.  Neither the stub nor stage-2 checksums the stage-2 program.
FLOPPY_JMP_SITE = 0x3E1AA                       # stage-2: jmp $800.l
FLOPPY_JMP_ORIG = bytes.fromhex("4ef900000800")
STAGE1_SITE = 0x3EE3C                           # two dead FDC helpers, 56 B
STAGE1_ORIG = bytes.fromhex(
    "33fc008400ff8606610000b2024000ff3d40000e33fc008000ff86064e75"
    "33fc008200ff860661000094024000ff33fc008000ff86064e75")
STAGE1_SRC = ["\tmove.l\t#$02c20040,$48646.l",   # stage-2 table entry 2: start sector 706, 64 sectors
              "\tmove.l\t#$8000,$4864a.l",       # byte length
              "\tmove.w\t#2,$14(a6)",            # file 2
              "\tmove.l\t#$b3000,$1a(a6)",       # destination
              "\tbsr.w\t$3ec9e",                 # stage-2's own loader (retries until the FDC says OK)
              "\tjmp\t$b3000.l"]
PAYLOAD_SECTOR = 706                             # 1-based absolute sector of the payload file
FLOPPY_LAST_SECTOR = 800                         # last sector of the image
FLOPPY_DISKS = [("MWA", "MWA.st"), ("MWB", "MWB.st"), ("MWC", "MWC.st")]


def floppy_conflicts(sites):
    """Sites whose original bytes would differ on floppy: those overlapping PP's RAM patches."""
    bad = []
    for s in sites:
        if s.get("media") == "floppy":
            continue                     # designed against the raw image (orig = image bytes)
        for pa, pb in PP_PATCHES.items():
            if s["addr"] < pa + len(pb) and pa < s["addr"] + len(s["orig"]):
                bad.append(f"{s['name']} ${s['addr']:x}+{len(s['orig'])} overlaps PP patch ${pa:x}")
    return bad


def floppy_mwa(payload: bytes) -> bytes:
    """MWA with the stage-1 loader (inside the stage-2 program) and the payload on free sectors."""
    mwa = bytearray(img_bytes("MWA"))
    if len(mwa) != 409600 or sum(struct.unpack(">256H", mwa[:512])) & 0xFFFF != 0x1234:
        raise SystemExit("MWA: not a 400K image with a bootable ($1234) boot sector")
    s1, _, _stage2 = stages()
    s2_off = (s1[0] - 1) * SECTOR

    def soff(a):
        return s2_off + a - STAGE2_RAM
    if bytes(mwa[soff(FLOPPY_JMP_SITE):soff(FLOPPY_JMP_SITE) + 6]) != FLOPPY_JMP_ORIG:
        raise SystemExit("stage-2: unexpected bytes at its final jmp")
    if bytes(mwa[soff(STAGE1_SITE):soff(STAGE1_SITE) + len(STAGE1_ORIG)]) != STAGE1_ORIG:
        raise SystemExit("stage-2: the dead routines at $3EE3C are not as expected")
    st1 = assemble(STAGE1_SITE, STAGE1_SRC)
    if len(st1) > len(STAGE1_ORIG):
        raise SystemExit(f"stage 1 is {len(st1)} B, only {len(STAGE1_ORIG)} B of dead code")
    n_sec = (len(payload) + SECTOR - 1) // SECTOR
    if n_sec != 64 or PAYLOAD_SECTOR + n_sec - 1 > FLOPPY_LAST_SECTOR:
        raise SystemExit(f"payload needs {n_sec} sectors (stage 1 is written for 64): free are "
                         f"{PAYLOAD_SECTOR}..{FLOPPY_LAST_SECTOR}")
    lo = (PAYLOAD_SECTOR - 1) * SECTOR
    if set(mwa[lo:FLOPPY_LAST_SECTOR * SECTOR]) != {0xE5}:
        raise SystemExit("MWA sectors 706..800 are not all $E5 filler")
    mwa[soff(STAGE1_SITE):soff(STAGE1_SITE) + len(st1)] = st1
    jmp = assemble(FLOPPY_JMP_SITE, [f"\tjmp\t${STAGE1_SITE:x}.l"])
    assert len(jmp) == 6
    mwa[soff(FLOPPY_JMP_SITE):soff(FLOPPY_JMP_SITE) + 6] = jmp
    mwa[lo:lo + len(payload)] = payload
    out = bytes(mwa)
    assert sector_file(out, PAYLOAD_SECTOR, len(payload)) == payload
    assert sum(struct.unpack(">256H", out[:512])) & 0xFFFF == 0x1234
    return out


def cmd_build_floppy(patches, out: Path, zip_path: Path | None = None, fpatches=()):
    if cmd_verify(patches):
        raise SystemExit("build aborted: a site's orig does not match the game")
    img, sites = build_image(patches)
    bad = floppy_conflicts(sites)
    if bad:
        raise SystemExit("build aborted: site differs on floppy:\n  " + "\n  ".join(bad))
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for src, name in FLOPPY_DISKS:
        data = floppy_mwa(img) if src == "MWA" else img_bytes(src)
        (out / name).write_bytes(data)
        files[name] = data
    import datetime
    import hashlib
    names = ", ".join(p.name for p in patches) or "(none)"
    md5s = "\n".join(f"  {hashlib.md5(files[n]).hexdigest()}  {n}" for _, n in FLOPPY_DISKS)
    tpl = PATCHDIR / "FLOPPY.TXT"
    txt = (tpl.read_text().replace("{DATE}", datetime.date.today().isoformat())
           .replace("{PATCHES}", names).replace("{MD5}", md5s)) if tpl.exists() else ""
    if txt:
        (out / "README.TXT").write_text(txt)
    print(f"built floppy set in {out}: {', '.join(n for _, n in FLOPPY_DISKS)}; "
          f"{len(patches)} patch(es); payload {len(img)} B = MWA sectors {PAYLOAD_SECTOR}.. -> $B3000")
    for fp in fpatches:
        print(f"skipped file patch {fp.name}: needs PP's HAGA service, which is not on floppy")
    print(f"{'site':8s} {'phase':9s} {'len':4s} orig -> new")
    for s in sites:
        print(f"${s['addr']:05x}  {s['phase']:9s} {len(s['orig']):4d} "
              f"{s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]")
    if zip_path:
        import zipfile
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for _, n in FLOPPY_DISKS:
                z.write(out / n, n)
            if txt:
                z.write(out / "README.TXT", "README.TXT")
        print(f"wrote {zip_path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--only", nargs="*", default=None)
    b.add_argument("--out", default=None, help="default build/game, or build/floppy with --floppy")
    b.add_argument("--floppy", action="store_true", help="build patched MWA/MWB/MWC floppy images")
    b.add_argument("--zip", nargs="?", const="", default=None, metavar="PATH",
                   help="with --floppy: also write dist/Midwinter1_patched_floppies_<date>.zip")
    lv = sub.add_parser("live")
    lv.add_argument("--only", nargs="*", default=None)
    lv.add_argument("--out", default="build/live/patches")
    lv.add_argument("--floppy", action="store_true", help="include the floppy-only patches (media: floppy)")
    sub.add_parser("list")
    sub.add_parser("verify")
    sub.add_parser("files")
    a = ap.parse_args()
    patches = load_patches()
    fpatches = load_file_patches()
    if a.cmd == "list":
        cmd_list(patches, fpatches)
    elif a.cmd == "files":
        cmd_files()
    elif a.cmd == "verify":
        sys.exit(cmd_verify(patches, fpatches))
    else:
        floppy = a.floppy
        ok_media = (None, "floppy") if floppy else (None,)
        if a.only is None:
            sel = [p for p in patches if p.default and p.media in ok_media]
            fsel = [p for p in fpatches if p.default]
        else:
            names = set(a.only)
            unknown = names - {p.name for p in patches} - {p.name for p in fpatches}
            if unknown:
                raise SystemExit(f"unknown patch(es): {sorted(unknown)}")
            wrong = sorted(p.name for p in patches if p.name in names and p.media not in ok_media)
            if wrong:
                raise SystemExit(f"floppy-only patch(es) {wrong}: use `build --floppy`")
            sel = [p for p in patches if p.name in names]
            fsel = [p for p in fpatches if p.name in names]
        if a.cmd == "build" and a.floppy:
            if fsel and a.only is not None:
                raise SystemExit("file patches (HAGA) are not applicable to --floppy: "
                                 "there is no HAGA service on floppy")
            import datetime
            zp = None if a.zip is None else ROOT / (
                a.zip or f"dist/Midwinter1_patched_floppies_{datetime.date.today().isoformat()}.zip")
            cmd_build_floppy(sel, ROOT / (a.out or "build/floppy"), zp, fsel)
        elif a.cmd == "build":
            if a.zip is not None:
                raise SystemExit("--zip needs --floppy")
            cmd_build(sel, ROOT / (a.out or "build/game"), fsel)
        else:
            if fsel and a.only is not None:
                raise SystemExit("file patches (HAGA) are not applicable to `live`: "
                                 "they are applied at build time, not in RAM")
            cmd_live(sel, ROOT / a.out)


if __name__ == "__main__":
    main()
