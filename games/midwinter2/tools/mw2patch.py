#!/usr/bin/env python3
"""Midwinter 2 patch delivery tool.

Patches are vasm sources in patches/ (see patches/README.md for the format and
the boot mechanism).  The tool assembles them, verifies every site's expected
ORIGINAL bytes against the disk images (FILES/FFA file 8/9, FILES/FFB file 1)
cross-checked against work/dumps/ram_ingame_lobos.bin, and produces a patched
COPY of the game in build/game (originals are never touched).

File patches (`; image: HAGA`, `; edit: <offset> <orig hex>`, `org HB+$<offset>`)
edit PP's resident loader service in the build copy's HAGA file; see the
"file patches" section of this tool and patches/README.md.

    python3 tools/mw2patch.py build [--only NAME ...] [--out build/game]
    python3 tools/mw2patch.py build --floppy [--only NAME ...] [--out build/floppy] [--zip [PATH]]
    python3 tools/mw2patch.py list
    python3 tools/mw2patch.py verify
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
RAMDUMP = ROOT / "work" / "dumps" / "ram_ingame_lobos.bin"
PATCHDIR = ROOT / "patches"
VASM = "vasmm68k_mot"

# ---- RUNME edit points (offsets into the unpacked image) -------------------
TEXT_LEN = 0x4520
STAGE_TXT = 0x3A8          # text offset of 'jmp $4d9a6.l' (stack-phase fallthrough)
TAIL_TXT = 0x754           # RAM $594: PP's last patch + 'jmp $3104.w' (12 B)
# Payload: $B3000-$BAFFF (32 KB): core + site table + blobs.  It rides in RUNME's data
# segment, so the bss (and every address that points into it) moves up by N.
PAYLOAD_LEN = 0x8000
OLD_BSS = 0x4536           # text-relative start of the original bss (= end of the original data)
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
    "4ef90004d9a6")                          # jmp  $4d9a6.l     (boot stub)
assert len(COPY_ROUTINE) == COPY_LEN
assert PAYLOAD_LEN % 4 == 0 and PAYLOAD_LEN // 4 - 1 <= 0xFFFF
# The four pc-relative `lea d(pc),aN` in RUNME that address bss: text offset ->
# (register number, text-relative bss target).  A signed 16-bit displacement cannot
# span N = 32 KB+ any more, so each becomes `movea.l d(pc),aN` (same 4 bytes, same
# registers, no flag change) loading a relocated pointer from BSS_PTRS, which sits
# within +-32 KB of every one of them.  Verified from a full-text scan of RUNME:
# these are the only pc-relative operands whose target is >= OLD_BSS (work/notes/payload32k.md).
BSS_LEAS = {0x98: (1, 0x4756), 0xC24: (2, 0x4756), 0x41EA: (2, 0x4536), 0x41FC: (1, 0x4536)}
BSS_PTR_TARGETS = (0x4756, 0x4536)         # BSS_PTRS slot i holds (target + N), relocated by the loader

# ---- $B3000 image layout ---------------------------------------------------
IMG_BASE = 0xB3000
ORG_TRAMP, ORG_HOOK, ORG_APPLY = 0xB3000, 0xB3070, 0xB3090
CORE_END = 0xB3100          # trampoline/hookexit/apply occupy $B3000-$B30FF
TABLE, TABLE_END = 0xBA000, 0xBB000   # site table + byte pool: 4 KB at the top of the payload
BLOB_MIN, BLOB_MAX = 0xB3100, TABLE - 1   # blob/data orgs, inclusive last byte
MARKER = 0xB2FF8
HOOK_SITE = 0x2789A        # sub_2783E single success exit (6-byte splice)
HOOK_ORIG = bytes.fromhex("46df31df62f2")
CORE_ORGS = {ORG_TRAMP, ORG_HOOK, ORG_APPLY}

# ---- PP's own boot patches (loading.md 6): RAM = image + these -------------
PP_PATCHES = {
    0x27AC4: "4ef80200", 0x1F5EA: "4eb900000314", 0x27CFC: "4e75",
    0x27A38: "4e75", 0x27A4E: "4e75", 0x27CAA: "4e75", 0x27A86: "4e75",
    0x27C4A: "4e75", 0x27B12: "4ef8034a", 0x2798A: "4ef80380",
    0x1ACC8: "4ef80322", 0x1AA14: "4ef80336", 0x2C542: "601c",
    0x2C574: "6002", 0x1F636: "4e71", 0x26A24: "4ef803ea",
}
PP_PATCHES = {a: bytes.fromhex(b) for a, b in PP_PATCHES.items()}

# ---- resident load ranges: RAM range -> (image file, dir base, file no) ----
def _f_off(s):
    return (s % 80) * 9216 + (s // 80) * 4608

def _extract(d, off, side, ln):
    out = bytearray(); s = side; pos = off
    while ln > 0:
        base = _f_off(s); n = min(ln, 4608 - pos)
        out += d[base + pos: base + pos + n]; ln -= n; s += 1; pos = 0
    return bytes(out)

def _dirents(d, base):
    for i in range(191):
        p = base + 8 + i * 8
        w0, w2 = struct.unpack_from(">HH", d, p)
        ln = int.from_bytes(d[p + 5:p + 8], "big")
        if ln:
            yield i, w0, w2, d[p + 4], ln

_cache = {}
def image_bytes(img: str, fileno: int) -> bytes:
    key = (img, fileno)
    if key not in _cache:
        d = (ROOT / "FILES" / img).read_bytes()
        base = 9216 if img == "FFA" else 0
        ent = [e for e in _dirents(d, base) if e[0] == fileno]
        if not ent:
            raise SystemExit(f"{img} file {fileno} not in directory")
        _, _, off, side, ln = ent[0]
        _cache[key] = _extract(d, off, side, ln)
    return _cache[key]

# RAM ranges loaded once from the images, in load order
LOAD_RANGES = [
    (0x806,   0x806 + len(image_bytes("FFA", 8)),  "FFA", 8),
    (0x3104,  0x3104 + len(image_bytes("FFA", 9)), "FFA", 9),
    (0x18D96, 0x18D96 + len(image_bytes("FFB", 1)), "FFB", 1),
]

def source_of(addr: int, ln: int):
    """(img, fileno) whose load range covers [addr, addr+ln), else None."""
    for lo, hi, img, fn in LOAD_RANGES:
        if lo <= addr and addr + ln <= hi:
            return img, fn
    return None

def source_of(addr: int, ln: int, phase: str | None = None):
    """Load range covering [addr, addr+ln).  Overlay (non-FFA) ranges win for
    auto/deferred; boot sites come from the boot-resident FFA images."""
    hits = [r for r in LOAD_RANGES if r[0] <= addr and addr + ln <= r[1]]
    if not hits:
        return None
    ffa = [r for r in hits if r[2] == "FFA"]
    ovl = [r for r in hits if r[2] != "FFA"]
    if phase == "boot":
        return (ffa[0][2], ffa[0][3]) if ffa else None
    if phase == "deferred":
        return (ovl[-1][2], ovl[-1][3]) if ovl else None
    r = (ovl[-1] if ovl else ffa[0]) if (ovl or ffa) else None
    return (r[2], r[3]) if r else None

BASES = {("FFA", 8): 0x806, ("FFA", 9): 0x3104, ("FFB", 1): 0x18D96}

def image_at(addr: int, ln: int, phase: str | None = None):
    src = source_of(addr, ln, phase)
    if src is None:
        return None
    b = image_bytes(*src)
    return b[addr - BASES[src]: addr - BASES[src] + ln]

def expected_ram(addr: int, ln: int, phase: str | None = None):
    """Bytes RAM holds right after the load (image + PP's boot patches)."""
    b = bytearray(image_at(addr, ln, phase))
    if source_of(addr, ln, phase or "boot") and \
       source_of(addr, ln, phase or "boot")[0] != "FFA":
        return bytes(b)
    for pa, pb in PP_PATCHES.items():
        if addr <= pa < addr + ln:
            o = pa - addr
            b[o:o + len(pb)] = pb
    return bytes(b)

# ---- patch source parsing --------------------------------------------------
ORG_RE = re.compile(r"^\s*org\s+\$?([0-9a-fA-F]+)\s*$", re.I)
HDR_RE = re.compile(r"^;\s*([a-z]+):\s*(.*)$")
# File patches (`; image: HAGA`): `org HB+$<file offset>` segments assembled with
# HB = the RAM address HAGA is relocated to (see HAGA_RAM_*), `; edit:` lines
# give the file offset and the expected ORIGINAL bytes.
HB_ORG_RE = re.compile(r"^\s*org\s+HB\s*\+\s*\$([0-9a-fA-F]+)\s*$", re.I)

class Patch:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.default = True
        self.site = None
        self.orig = None          # declared (optional)
        self.phase = None         # None = auto
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
        src = source_of(self.site, 1)
        return "boot" if src and src[0] == "FFA" else "deferred"

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

def core_segments(floppy: bool = False) -> dict[int, bytes]:
    p = Patch(PATCHDIR / "core.s")
    # FLOPPY drops the replay of PP's displaced $2c574 patch (PP's patcher never runs
    # on floppy, and that patch is PP's skip of the game's security check)
    equ = "\n".join(p.preamble + (["FLOPPY equ 1"] if floppy else []))
    segs = {}
    for org, lines in p.segments:
        segs[org] = assemble(org, lines, equ)
    if set(segs) != CORE_ORGS:
        raise SystemExit(f"core.s orgs {sorted(segs)} != {sorted(CORE_ORGS)}")
    return segs

# ---- file patches (HAGA) ---------------------------------------------------------
# PP's resident loader service (the code behind every Fopen/Fread/Fwrite the game
# does, including the grey "loading" palette fades) is NOT in RUNME.TOS: it is the
# file HAGA, which RUNME copies verbatim to the top of RAM.  HAGA file offset 0 is
# RAM $1F8000 on a 2 MB machine (work/dumps/ram_ingame_lobos.bin) and $F8000 on a
# 1 MB machine (phystop-$8000), so absolute RAM addresses cannot be patched.  A file
# patch edits HAGA bytes in the build copy instead:
#     ; image: HAGA
#     ; edit: $<file offset> <expected original bytes, hex>      (repeatable)
#             org HB+$<file offset>        ; one segment per edit, same length
# Segments are assembled with HB = the 2 MB base and again with the 1 MB base and
# must come out byte-identical, i.e. position independent (pc-relative references
# to HB+.. only).  `verify` checks every edit's original bytes against the shipped
# file AND the in-game RAM dump; `build` refuses to apply over different bytes.
HAGA_RAM_2MB, HAGA_RAM_1MB = 0x1F8000, 0xF8000
FILE_IMAGES = ("HAGA",)

def file_patch_bytes(p: Patch) -> dict[int, bytes]:
    """New bytes per edit offset, assembled at both HAGA bases (must agree)."""
    segs = {}
    for off, lines in p.fsegments:
        outs = [assemble(hb + off, lines, f"HB\tequ\t${hb:x}\n" + "\n".join(p.preamble))
                for hb in (HAGA_RAM_2MB, HAGA_RAM_1MB)]
        if outs[0] != outs[1]:
            raise SystemExit(f"{p.name}: segment HB+${off:x} is not position independent "
                             f"({outs[0].hex()} at $1F8000 vs {outs[1].hex()} at $F8000)")
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
            db = ram[HAGA_RAM_2MB + off:HAGA_RAM_2MB + off + len(orig)]
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
def build_image(patches: list[Patch], floppy: bool = False):
    core = core_segments(floppy)
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
        orig = p.orig if p.orig is not None else expected_ram(p.site, len(new), p.phase)
        if orig is None:
            raise SystemExit(f"{p.name}: site ${p.site:x} in no known load range")
        if len(new) > len(orig):
            raise SystemExit(f"{p.name}: new bytes longer than orig")
        if len(new) < len(orig):
            new = new + b"\x4e\x71" * (len(orig) - len(new))
        if len(new) != len(orig):
            raise SystemExit(f"{p.name}: size mismatch")
        sites.append(dict(name=p.name, addr=p.site, orig=orig, new=new,
                          phase=p.phase_of()))
    if any(s["phase"] == "deferred" for s in sites):
        sites.append(dict(name="<load-hook>", addr=HOOK_SITE, orig=HOOK_ORIG,
                          # jmp, not jsr: hookexit pops the original exit frame
                          # (sr, $62f2, 15 regs) and must see it at (a7).
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
def check_site(addr: int, orig: bytes, phase: str | None = None):
    """Return (ok, image_ok, dump_ok, image_bytes, dump_bytes)."""
    ib = image_at(addr, len(orig), phase)
    exp = expected_ram(addr, len(orig), phase)
    ram = RAMDUMP.read_bytes()
    db = ram[addr:addr + len(orig)]
    return ib == orig and exp == orig and db == orig, ib == orig, db == exp, ib, db

def cmd_verify(patches, fpatches=()):
    bad = 0
    for p in patches:
        seg = [s for s in p.segments if s[0] == p.site]
        new = assemble(p.site, seg[0][1], "\n".join(p.preamble)) if seg else b""
        orig = p.orig if p.orig is not None else (
            expected_ram(p.site, len(new), p.phase) if new else b"")
        ok, iok, dok, ib, db = check_site(p.site, orig, p.phase)
        src = source_of(p.site, len(orig), p.phase)
        print(f"{p.name:18s} site ${p.site:05x} phase {p.phase_of():8s} "
              f"src {src[0]} f{src[1]} len {len(orig)}")
        print(f"    declared orig : {orig.hex()}")
        print(f"    image  bytes  : {ib.hex()}  ({'match' if iok else 'MISMATCH'})")
        print(f"    ramdump bytes : {db.hex()}  ({'match' if dok else 'MISMATCH'})")
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
    assert (text_len, data_len) == (TEXT_LEN, 22)
    text = bytearray(src[28:28 + TEXT_LEN])
    data = src[28 + TEXT_LEN:28 + TEXT_LEN + 22]
    rel_off = 28 + TEXT_LEN + 22
    offs, rel_end = decode_reloc(src[rel_off:])
    assert rel_end == len(src) - rel_off
    # 1. staging: jmp to the copy routine at the head of the appended data
    struct.pack_into(">HI", text, STAGE_TXT, 0x4EF9, TEXT_LEN + 22)
    # 2. patcher tail -> trampoline
    text[TAIL_TXT:TAIL_TXT + 12] = bytes.fromhex("4ef9000b3000" + "4e71" * 3)
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

# d16(pc) operands whose "target" lands in or beyond the bss but that are not code: data
# words inside PP's stack-block / HAGA data area ($76c) and $FFFA fill words ($422a, $43f2).
NOT_CODE = {0x76C, 0x422A, 0x43F2}

def check_bss_pcrel_complete(text: bytes):
    """Every d16(pc) operand (ea mode 7/2) whose target is >= OLD_BSS must be listed in
    BSS_LEAS, else it would silently keep a stale displacement when the bss moves."""
    for t in range(0, TEXT_LEN - 3, 2):
        op, d = struct.unpack_from(">Hh", text, t)
        if op & 0x3F == 0x3A and t + 2 + d >= OLD_BSS and t not in BSS_LEAS and t not in NOT_CODE:
            raise SystemExit(f"RUNME text ${t:x}: unlisted pc-relative reference to ${t + 2 + d:x} (op {op:04x})")

# ---- build -------------------------------------------------------------------
GAME_FILES = ["HAGA", "FF240R.BMP", "FFF273.HST", "LFF273.HST", "LOG.TXT",
              "README.TXT", "SOLUTION.TXT"]

def cmd_build(patches, out: Path, fpatches=()):
    if cmd_verify(patches, fpatches):
        raise SystemExit("build aborted: a site's orig does not match the game")
    img, sites = build_image(patches)
    runme = build_runme(img)
    out.mkdir(parents=True, exist_ok=True)
    for f in GAME_FILES:
        shutil.copy(ROOT / f, out / f)
    shutil.copytree(ROOT / "FILES", out / "FILES", dirs_exist_ok=True)
    (out / "work").mkdir(exist_ok=True)
    shutil.copytree(ROOT / "work" / "disk_overlay", out / "work" / "disk_overlay",
                    dirs_exist_ok=True)
    (out / "RUNME.TOS").write_bytes(bytes(runme))
    apply_file_patches(fpatches, out)
    print(f"built {out} with {len(patches)} patch(es) + {len(fpatches)} file patch(es); "
          f"payload {len(img)} B at $B3000")
    print(f"{'site':8s} {'phase':9s} {'len':4s} orig -> new")
    for s in sites:
        print(f"${s['addr']:05x}  {s['phase']:9s} {len(s['orig']):4d} "
              f"{s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]")

def cmd_live(patches, out: Path):
    """Write what the boot installer would put in RAM, for applying a patch set
    to a running snapshot (tools/mw2harness.py Hatari.apply_live): the payload
    image (`<out>.img`, load at $B3000) and the site bytes (`<out>.json`).
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
# FILES/FFA..FFC are working floppy images.  Boot sector (word sum $1234) loads FFA
# file 1, the boot stub (4096 B at image offset $200), to $4D9A6; the stub loads FFA
# file 8 ($806) and file 9 ($3104) with its own FDC code and ends in `jmp $3104.w`
# at $4DAA0.  PP's RUNME, his patcher ($4BC-$59C) and the HAGA service are not
# involved, so none of PP_PATCHES exist in RAM on floppy (work/notes/floppy.md).
#
# Injection: a new FFA file 10 (the $B3000 payload, directory entry + free
# track-sides 72-79) is loaded by the stub's own loader (sub_04db52, a6 = $4e9d8)
# from a 32-byte stage-1 placed in unreferenced stub code ($4DDAA-$4DDE9, 64 B), and
# the stub's final jmp becomes `bra.w stage1`.  Stage 1 ends in `jmp $B3000.l`, the
# floppy variant of the trampoline (core.s FLOPPY), which ends in `jmp $3104.w`.
FFA_DIR_OFF = 9216              # FFA directory = track-side 1 (one 512 B sector, 63 entries)
STUB_RAM, STUB_FOFF = 0x4D9A6, 0x200
STUB_JMP_SITE = 0x4DAA0
STUB_JMP_ORIG = bytes.fromhex("4ef83104")                     # jmp $3104.w
STAGE1_SITE = 0x4DDAA
STAGE1_ORIG = bytes.fromhex(                                  # dead code, 64 B, no xref
    "303c018051c8fffe0839000500fffa01670000281d7900ff8609000f1d7900ff860b0010"
    "1d7900ff860d0011222e000eb2ae00126dd26100ff126100ff6e4e75")
STAGE1_SRC = ["\tlea\t$4e9d8.l,a6",                 # the stub's parameter block
              "\tmove.l\t#$b3000,$4e9ac.l",         # load destination
              "\tmove.w\t#10,$16(a6)",              # file number
              "\tbsr.w\t$4db52",                    # stub loader (checks the dir checksum)
              "\tjmp\t$b3000.l"]
PAYLOAD_FILE, PAYLOAD_TS = 10, 72
FFA_BLANK_END = 80             # FFA track-sides 72-79 are blank ($F6); track-side 80 (side 1, track 0) holds data
FLOPPY_DISKS = [("FFA", "FFA_boot.st"), ("FFB", "FFB_graphics.st"),
                ("FFC", "FFC_missions.st"), ("FFD", "FFD_campaign_blank.st")]

def xor_cksum(b: bytes) -> int:
    """The game's directory checksum (sub_27A14 / stub sub_04dc90): XOR of BE words."""
    c = 0
    for i in range(0, len(b) - 1, 2):
        c ^= (b[i] << 8) | b[i + 1]
    if len(b) & 1:
        c ^= b[-1] << 8
    return c

def floppy_conflicts(sites):
    """Sites whose original bytes would differ on floppy: those overlapping PP's RAM patches."""
    bad = []
    for s in sites:
        for pa, pb in PP_PATCHES.items():
            if s["addr"] < pa + len(pb) and pa < s["addr"] + len(s["orig"]):
                bad.append(f"{s['name']} ${s['addr']:x}+{len(s['orig'])} overlaps PP patch ${pa:x}")
    return bad

def floppy_ffa(payload: bytes) -> bytes:
    """FFA with the stage-1 loader, directory entry and data of file 10 (the payload)."""
    ffa = bytearray((ROOT / "FILES" / "FFA").read_bytes())
    if len(ffa) != 737280 or sum(struct.unpack(">256H", ffa[:512])) & 0xFFFF != 0x1234:
        raise SystemExit("FFA: not a 720K image with a bootable ($1234) boot sector")

    def soff(a):
        return STUB_FOFF + a - STUB_RAM
    for site, orig in ((STUB_JMP_SITE, STUB_JMP_ORIG), (STAGE1_SITE, STAGE1_ORIG)):
        if bytes(ffa[soff(site):soff(site) + len(orig)]) != orig:
            raise SystemExit(f"FFA stub: unexpected bytes at ${site:x}")
    ent = FFA_DIR_OFF + 8 + PAYLOAD_FILE * 8
    if any(ffa[ent:ent + 8]):
        raise SystemExit(f"FFA directory entry {PAYLOAD_FILE} is in use")
    n_ts = (len(payload) + 4607) // 4608
    if PAYLOAD_TS + n_ts > FFA_BLANK_END:
        raise SystemExit(f"payload needs {n_ts} track-sides: FFA has only track-sides "
                         f"{PAYLOAD_TS}-{FFA_BLANK_END - 1} free (track-side {FFA_BLANK_END} holds data)")
    for ts in range(PAYLOAD_TS, PAYLOAD_TS + n_ts):
        seg = ffa[_f_off(ts):_f_off(ts) + 4608]
        if set(seg) - {0xF6}:
            raise SystemExit(f"FFA track-side {ts} is not blank")
    if any(e[3] + (e[2] + e[4] - 1) // 4608 >= PAYLOAD_TS for e in _dirents(bytes(ffa), FFA_DIR_OFF)
           if e[0] < 63):
        raise SystemExit("a FFA file reaches the payload's track-sides")
    # stage 1 + the stub's final jump
    st1 = assemble(STAGE1_SITE, STAGE1_SRC)
    assert len(st1) == 32, len(st1)
    ffa[soff(STAGE1_SITE):soff(STAGE1_SITE) + len(st1)] = st1
    bra = assemble(STUB_JMP_SITE, [f"\tbra.w\t${STAGE1_SITE:x}"])
    assert len(bra) == 4
    ffa[soff(STUB_JMP_SITE):soff(STUB_JMP_SITE) + 4] = bra
    # file 10: directory entry [cksum.w][offset.w = 0][track-side.b][len.u24], data
    struct.pack_into(">HHBBH", ffa, ent, xor_cksum(payload), 0, PAYLOAD_TS,
                     len(payload) >> 16, len(payload) & 0xFFFF)
    for i in range(n_ts):
        chunk = payload[i * 4608:(i + 1) * 4608]
        o = _f_off(PAYLOAD_TS + i)
        ffa[o:o + len(chunk)] = chunk
    out = bytes(ffa)
    # self-check: read file 10 back through the directory exactly as the stub does
    e = [e for e in _dirents(out, FFA_DIR_OFF) if e[0] == PAYLOAD_FILE][0]
    back = _extract(out, e[2], e[3], e[4])
    assert back == payload and xor_cksum(back) == e[1]
    assert sum(struct.unpack(">256H", out[:512])) & 0xFFFF == 0x1234
    return out

def cmd_build_floppy(patches, out: Path, zip_path: Path | None = None, fpatches=()):
    if cmd_verify(patches):
        raise SystemExit("build aborted: a site's orig does not match the game")
    img, sites = build_image(patches, floppy=True)
    bad = floppy_conflicts(sites)
    if bad:
        raise SystemExit("build aborted: site differs on floppy:\n  " + "\n  ".join(bad))
    out.mkdir(parents=True, exist_ok=True)
    files = {}
    for src, name in FLOPPY_DISKS:
        data = floppy_ffa(img) if src == "FFA" else (ROOT / "FILES" / src).read_bytes()
        (out / name).write_bytes(data)
        files[name] = data
    import datetime
    import hashlib
    names = ", ".join(p.name for p in patches)
    md5s = "\n".join(f"  {hashlib.md5(files[n]).hexdigest()}  {n}" for _, n in FLOPPY_DISKS)
    txt = ((PATCHDIR / "FLOPPY.TXT").read_text()
           .replace("{DATE}", datetime.date.today().isoformat())
           .replace("{PATCHES}", names).replace("{MD5}", md5s))
    (out / "README.TXT").write_text(txt)
    print(f"built floppy set in {out}: {', '.join(n for _, n in FLOPPY_DISKS)} + README.TXT; "
          f"{len(patches)} patch(es); payload {len(img)} B = FFA file {PAYLOAD_FILE} -> $B3000")
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
            z.write(out / "README.TXT", "README.TXT")
        print(f"wrote {zip_path}")

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--only", nargs="*", default=None)
    b.add_argument("--out", default=None, help="default build/game, or build/floppy with --floppy")
    b.add_argument("--floppy", action="store_true",
                   help="build three floppy images (FFA with the payload as file 10, FFB, FFC) "
                        "plus a blank campaign disk instead of the HD game directory")
    b.add_argument("--zip", nargs="?", const="", default=None, metavar="PATH",
                   help="with --floppy: also write dist/Midwinter2_patched_floppies_<date>.zip")
    lv = sub.add_parser("live")
    lv.add_argument("--only", nargs="*", default=None)
    lv.add_argument("--out", default="build/live/patches")
    sub.add_parser("list")
    sub.add_parser("verify")
    a = ap.parse_args()
    patches = load_patches()
    fpatches = load_file_patches()
    if a.cmd == "list":
        cmd_list(patches, fpatches)
    elif a.cmd == "verify":
        sys.exit(cmd_verify(patches, fpatches))
    else:
        floppy = a.cmd == "build" and a.floppy
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
                a.zip or f"dist/Midwinter2_patched_floppies_{datetime.date.today().isoformat()}.zip")
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
