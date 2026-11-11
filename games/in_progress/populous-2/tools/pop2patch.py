#!/usr/bin/env python3
"""Populous 2 patch delivery tool (design copied from Midwinter 2's mw2patch.py).

Patches are vasm sources in patches/ (format and boot mechanism: patches/README.md).
The tool assembles them, verifies every site's expected ORIGINAL bytes against the
game as the game itself builds it (FILES/P2M.FIC unpacked to $1770 with RUNME's own
LZ, plus PP's four RAM patches) cross-checked against work/dumps/game_start.bin, and
writes a patched COPY of the game; the originals are never touched.

    python3 tools/pop2patch.py list | verify | version
    python3 tools/pop2patch.py build [--hd | --floppy] [--only NAME ...] [--out DIR] [--zip [PATH]]
    python3 tools/pop2patch.py live  [--only NAME ...] [--out build/live/patches]
    python3 tools/pop2patch.py doc FILE            # a doc with @VERSION@ replaced

build --hd (default): a game folder for a hard disk / GEMDOS drive (patched RUNME.TOS + HAGA, original FILES).
build --floppy: a bootable 720K .st with the same RUNME in AUTO\\RUNME.PRG plus HAGA, FILES\\ and the
pictures (the game fits one disk), see patches/README.md.
live: <out>.img (the payload, load at PB) + <out>.json (site bytes) for snapshots; see
stharness.Hatari.capture_frames(live=...).
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
from pp_depack import depack as pp_depack  # noqa: E402

ORIG = ROOT / "originals" / "POPUL2"
RAMDUMP = ROOT / "work" / "dumps" / "game_start.bin"      # 2 MB STE, unpatched, game running (cross-check of code bytes)
PATCHDIR = ROOT / "patches"
VASM = "vasmm68k_mot"

# ---- the game image: what RUNME's stage block builds in RAM ----------------
# FILES/P2M.FIC: 32-byte header ('C3', packed length, unpacked length $79c10, ...) then PP's LZ
# stream, unpacked by the stage block (text $386-$392 of RUNME) to $1770 (= `lea $1770.w,a4`).
GAME_BASE, GAME_LEN = 0x1770, 0x79C10
# PP's RAM patches applied by the stage block right after the unpack (RUNME text $3b0-$3d6):
PP_PATCHES = {0x36EFC: "4ef80140", 0x2CC98: "4ef80206", 0x14A88: "6002", 0x1CF8: "4ef802ac"}
PP_PATCHES = {a: bytes.fromhex(b) for a, b in PP_PATCHES.items()}


def lz_unpack(src: bytes) -> bytes:
    """RUNME's LZ ($600 in the stage block): 0 = end, 1..$7F = literal run, $80|n = n+3 bytes from a
    1-byte distance, $C0|n = n+4 bytes from a 2-byte distance (same format as pp_depack)."""
    out = bytearray()
    i = 0
    while True:
        c = src[i]; i += 1
        if c == 0:
            return bytes(out)
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


_game = None
def game_image() -> bytearray:
    """The game as RAM holds it at the moment PP's tail runs (unpacked + PP's patches)."""
    global _game
    if _game is None:
        raw = (ORIG / "FILES" / "P2M.FIC").read_bytes()
        img = lz_unpack(raw[0x20:])
        if len(img) != GAME_LEN:
            raise SystemExit(f"P2M.FIC unpacks to {len(img):#x} bytes, expected {GAME_LEN:#x}")
        img = bytearray(img)
        for a, b in PP_PATCHES.items():
            img[a - GAME_BASE:a - GAME_BASE + len(b)] = b
        _game = img
    return _game


# PP's low-RAM stub block: the stage block copies 700 bytes from RUNME text $3f8 to $140 (RUNME text $39a-$3a6,
# `lea $3f8(pc),a1 / lea $140.l,a2 / move.w #$ae,d2`).  Its code bytes are what RUNME ships; a few words of it are
# variables the stub modifies while it runs ($148 the file number, $296/$29a the cache window, $2aa the whole-file flag).
STUB_RAM, STUB_TXT, STUB_LEN = 0x140, 0x3F8, 0x2BC


def expected_ram(addr: int, ln: int):
    if STUB_RAM <= addr and addr + ln <= STUB_RAM + STUB_LEN:
        o = STUB_TXT + addr - STUB_RAM
        return bytes(runme_source()[28 + o:28 + o + ln])
    if addr < GAME_BASE or addr + ln > GAME_BASE + GAME_LEN:
        return None
    return bytes(game_image()[addr - GAME_BASE:addr - GAME_BASE + ln])


def dump_bytes(addr: int, ln: int) -> bytes:
    with RAMDUMP.open("rb") as f:
        f.seek(addr)
        return f.read(ln)


# ---- RUNME edit points (offsets into the unpacked image = text-relative) ---
TEXT_LEN = 0x440E
OLD_BSS = TEXT_LEN + 22               # end of the original data = start of the original bss
STAGE_TXT = 0x318                     # `move.w #$2700,sr` (4 B) before the stage block is copied; becomes `bsr.w copy`
STAGE_ORIG = bytes.fromhex("46fc2700")
TAIL_TXT = 0x3DA                      # PP's tail inside the stack-phase block: `move.l #$1c42,$118.w` + `jmp $1770.w` (12 B)
TAIL_ORIG = bytes.fromhex("21fc00001c420118" "4ef81770")

# Payload: PAYLOAD_LEN bytes at PB, copied there by `copy` (appended to RUNME's data segment) while
# RUNME's own memory is still intact; the game unpack that follows overwrites RUNME's TPA.
PB = 0x80000
PAYLOAD_LEN = 0x8000
MARKER = PB - 8
CORE_END = PB + 0x100                 # trampoline: PB .. PB+$FF
TABLE, TABLE_END = PB + 0x7000, PB + 0x8000        # site table + orig/new byte pool: 4 KB at the top
BLOB_MIN, BLOB_MAX = CORE_END, TABLE - 1            # blob/data orgs, inclusive last byte
PTRS_LEN = 8

# The pc-relative `lea d(pc),aN` in RUNME that address bss: text offset -> (register, text-relative target).
# The bss moves up by N when the data segment grows, and a signed 16-bit displacement cannot span the payload,
# so each becomes `movea.l d(pc),aN` (same 4 bytes, same register, no flag change) loading a relocated pointer
# from PTRS.  Found by a scan of the whole text for d16(pc) operands whose target is >= OLD_BSS (the other
# hits of that scan, NOT_CODE, are displacement words / data that merely look like one; checked against m68dis).
BSS_LEAS = {0xB6: (1, 0x4644), 0xB12: (2, 0x4644), 0x40D8: (2, 0x4424), 0x40EA: (1, 0x4424)}
BSS_PTR_TARGETS = (0x4644, 0x4424)
NOT_CODE = {0x270, 0x43C, 0x57E, 0x64A, 0x4118, 0x413C, 0x42E0, 0x4322}


# ---- patch source parsing --------------------------------------------------
ORG_RE = re.compile(r"^\s*org\s+(\S+)\s*$", re.I)
HDR_RE = re.compile(r"^;\s*([a-z]+):\s*(.*)$")
HB_ORG_RE = re.compile(r"^\s*org\s+HB\s*\+\s*\$([0-9a-fA-F]+)\s*$", re.I)
VERSION_TAG = "@VERSION@"
CREDIT = "enhanced by dad_prg"
CORE_FILES = ("core.s",)


def addr_expr(s: str) -> int:
    """`$80100`, `PB+$100` -> absolute address."""
    s = s.strip()
    m = re.fullmatch(r"PB\s*(?:\+\s*\$([0-9a-fA-F]+))?", s)
    if m:
        return PB + (int(m.group(1), 16) if m.group(1) else 0)
    m = re.fullmatch(r"\$([0-9a-fA-F]+)", s)
    if m:
        return int(m.group(1), 16)
    raise SystemExit(f"bad address expression {s!r}")


def release_version() -> str:
    """The release version: the `; version:` header of patches/pop2_credit.s, the single place it is defined."""
    for f in sorted(PATCHDIR.glob("*.s")):
        m = re.search(r"^;\s*version:\s*(\S+)\s*$", f.read_text(), re.M)
        if m:
            return m.group(1)
    raise SystemExit("no `; version:` header in patches/*.s")


def render_doc(text: str) -> str:
    text = text.replace(VERSION_TAG, release_version())
    if "{PATCHES}" in text:
        lines = []
        for p in load_patches():
            if not p.default:
                continue
            note = p.doc or next((n for n in p.notes if n.strip()), "")
            if len(note) > 150:
                note = note[:150].rsplit(" ", 1)[0] + " ..."
            lines.append(f"- {p.name}: {note}")
        text = text.replace("{PATCHES}", "\n".join(lines) if lines else "- (none: the unpatched game + the marker)")
    return text


class Patch:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.default = True
        self.site = None
        self.orig = None          # declared (optional)
        self.data = []            # (addr, len) reservations
        self.segments = []        # (org, source lines)
        self.preamble = []        # equ lines before the first org
        self.image = None         # file patch: game file (HAGA) edited in place
        self.media = None         # None = every build; "floppy" = only `build --floppy`
        self.edits = []           # file patch: (file offset, expected original bytes)
        self.fsegments = []       # file patch: (file offset, source lines)
        self.notes = []
        self.doc = None
        cur = None
        text = path.read_text()
        vm = re.search(r"^;\s*version:\s*(\S+)\s*$", text, re.M)
        self.version = vm.group(1) if vm else None
        if self.version:
            text = text.replace(VERSION_TAG, self.version)       # the one place the release version is defined
        for line in text.splitlines():
            if cur is None and re.match(r"^\s*\w+\s+equ\s+", line):
                self.preamble.append(line)
                continue
            m = HDR_RE.match(line)
            if m and cur is None:
                k, v = m.group(1), m.group(2).strip()
                if k == "name": self.name = v
                elif k == "default": self.default = v.split(";")[0].strip().lower() not in ("no", "false", "0")
                elif k == "site": self.site = addr_expr(v.split(";")[0])
                elif k == "orig": self.orig = bytes.fromhex(v.split(";")[0].replace(" ", ""))
                elif k == "data":
                    a, l = v.split(";")[0].split()
                    self.data.append((addr_expr(a), int(l, 0)))
                elif k == "image": self.image = v.strip()
                elif k == "media":
                    if v.strip().lower() != "floppy":
                        raise SystemExit(f"{path}: media must be `floppy`")
                    self.media = "floppy"
                elif k == "edit":
                    a, b = v.split(None, 1)
                    self.edits.append((int(a.lstrip("$"), 16), bytes.fromhex(b.split(";")[0].replace(" ", ""))))
                elif k == "note":
                    self.notes.append(v)
                elif k == "doc":
                    self.doc = v
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
    ps = [Patch(f) for f in _patch_files()]
    return [p for p in ps if p.site is not None]


def load_file_patches():
    out = []
    for f in _patch_files():
        p = Patch(f)
        if p.image is not None:
            if p.site is not None:
                raise SystemExit(f"{f.name}: `image:` and `site:` are mutually exclusive")
            out.append(p)
    return out


# ---- assembly ---------------------------------------------------------------
def equ_preamble(p_preamble=()):
    return "\n".join([f"PB\tequ\t${PB:x}"] + list(p_preamble))


def assemble(org: int, lines: list[str], equ: str = "") -> bytes:
    src = equ_preamble() + "\n" + equ + f"\n\torg\t${org:x}\n" + "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "seg.s"
        s.write_text(src)
        out = Path(td) / "seg.bin"
        r = subprocess.run([VASM, "-Fbin", "-m68000", "-quiet", "-o", str(out), str(s)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"vasm failed:\n{src}\n{r.stderr}")
        return out.read_bytes()


def core_segment() -> bytes:
    p = Patch(PATCHDIR / "core.s")
    if len(p.segments) != 1 or p.segments[0][0] != PB:
        raise SystemExit("core.s must hold exactly one segment, org PB")
    b = assemble(PB, p.segments[0][1], "\n".join(p.preamble))
    if PB + len(b) > CORE_END:
        raise SystemExit(f"core overflows (${len(b):x} B)")
    return b


# ---- file patches (HAGA) ---------------------------------------------------------
# HAGA is copied by RUNME to phystop-$8000: $1F8000 (2 MB), $3F8000 (4 MB), $F8000 (1 MB, not supported by
# Populous 2).  A file patch edits HAGA bytes in the build copy, and must assemble to identical bytes at
# every base (position independent).
HAGA_RAM = (0x1F8000, 0x3F8000, 0xF8000)
FILE_IMAGES = ("HAGA",)


def file_patch_bytes(p: Patch) -> dict[int, bytes]:
    segs = {}
    for off, lines in p.fsegments:
        outs = [assemble(hb + off, lines, f"HB\tequ\t${hb:x}\n" + "\n".join(p.preamble)) for hb in HAGA_RAM]
        if any(o != outs[0] for o in outs):
            raise SystemExit(f"{p.name}: segment HB+${off:x} is not position independent "
                             f"({[o.hex() for o in outs]})")
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
            db = dump_bytes(HAGA_RAM[0] + off, len(orig))
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
def site_bytes(p: Patch):
    seg = [s for s in p.segments if s[0] == p.site]
    if not seg:
        raise SystemExit(f"{p.name}: no org ${p.site:x} segment")
    new = assemble(p.site, seg[0][1], "\n".join(p.preamble))
    orig = p.orig if p.orig is not None else expected_ram(p.site, len(new))
    if orig is None:
        raise SystemExit(f"{p.name}: site ${p.site:x} is outside the game image ${GAME_BASE:x}-${GAME_BASE + GAME_LEN:x} and PP's stub block ${STUB_RAM:x}-${STUB_RAM + STUB_LEN:x}")
    if len(new) > len(orig):
        raise SystemExit(f"{p.name}: new bytes longer than orig")
    if len(new) < len(orig):
        new = new + b"\x4e\x71" * ((len(orig) - len(new)) // 2)
    if len(new) != len(orig):
        raise SystemExit(f"{p.name}: size mismatch")
    return orig, new


def build_image(patches: list[Patch]):
    core = core_segment()
    sites = []
    for p in patches:
        orig, new = site_bytes(p)
        sites.append(dict(name=p.name, addr=p.site, orig=orig, new=new))
    by_addr = sorted(sites, key=lambda s: s["addr"])
    for s, t in zip(by_addr, by_addr[1:]):
        if s["addr"] + len(s["orig"]) > t["addr"]:
            raise SystemExit(f"site overlap: {s['name']} ${s['addr']:x}+{len(s['orig'])} vs {t['name']} ${t['addr']:x}")
    for s in sites:
        for a, b in PP_PATCHES.items():
            if s["addr"] < a + len(b) and a < s["addr"] + len(s["orig"]):
                raise SystemExit(f"{s['name']}: site overlaps PP's patch at ${a:x}")
    n = len(sites)
    tbl_len = n * 16 + 4
    pool = bytearray()
    ptrs = []
    for s in sites:
        o = len(pool); pool += s["orig"]
        nw = len(pool); pool += s["new"]
        ptrs.append((TABLE + tbl_len + o, TABLE + tbl_len + nw))
    if TABLE + tbl_len + len(pool) > TABLE_END:
        raise SystemExit(f"site table + byte pool overflow ${TABLE:x}-${TABLE_END - 1:x}")
    img = bytearray(PAYLOAD_LEN)
    img[:len(core)] = core
    for i, s in enumerate(sites):
        struct.pack_into(">IHHII", img, TABLE - PB + i * 16, s["addr"], len(s["orig"]), 0, ptrs[i][0], ptrs[i][1])
    img[TABLE - PB + tbl_len: TABLE - PB + tbl_len + len(pool)] = pool
    placed = [(PB, PB + len(core)), (TABLE, TABLE + tbl_len + len(pool))]
    for p in patches:
        for org, lines in p.segments:
            if org == p.site:
                continue
            if not (BLOB_MIN <= org <= BLOB_MAX):
                raise SystemExit(f"{p.name}: org ${org:x} outside blob area ${BLOB_MIN:x}-${BLOB_MAX:x}")
            b = assemble(org, lines, "\n".join(p.preamble))
            if org + len(b) > BLOB_MAX + 1:
                raise SystemExit(f"{p.name}: blob overflows image")
            placed.append((org, org + len(b)))
            img[org - PB: org - PB + len(b)] = b
        for a, l in p.data:
            placed.append((a, a + l))
    placed.sort()
    for (a0, a1), (b0, b1) in zip(placed, placed[1:]):
        if a1 > b0:
            raise SystemExit(f"image overlap: ${a0:x}-${a1:x} vs ${b0:x}-${b1:x}")
    return bytes(img), sites


# ---- verification ------------------------------------------------------------
def cmd_verify(patches, fpatches=()):
    bad = 0
    for p in patches:
        seg = [s for s in p.segments if s[0] == p.site]
        new = assemble(p.site, seg[0][1], "\n".join(p.preamble)) if seg else b""
        orig = p.orig if p.orig is not None else (expected_ram(p.site, len(new)) if new else b"")
        if orig is None:
            orig = b""
        ib = expected_ram(p.site, len(orig)) or b""
        db = dump_bytes(p.site, len(orig))
        iok = ib == orig and len(orig) > 0
        dok = db == ib
        where = ("PP's stub block (RUNME text $3f8)" if STUB_RAM <= p.site < STUB_RAM + STUB_LEN
                 else "P2M.FIC unpacked + PP's patches")
        print(f"{p.name:18s} site ${p.site:05x} len {len(orig)}   [{where}]")
        print(f"    declared orig : {orig.hex()}")
        print(f"    expected      : {ib.hex()}  ({'match' if iok else 'MISMATCH'})")
        print(f"    ram dump      : {db.hex()}  ({'match' if dok else 'MISMATCH'})   [work/dumps/game_start.bin]")
        if not (iok and dok):
            bad += 1
    bad += cmd_verify_runme()
    bad += cmd_verify_files(fpatches)
    print("verify:", "ALL OK" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


def cmd_verify_runme() -> int:
    """RUNME's two edit points and the bss pc-relative scan."""
    src = runme_source()
    text = src[28:28 + TEXT_LEN]
    bad = 0
    for name, off, orig in (("stage hook", STAGE_TXT, STAGE_ORIG), ("PP tail", TAIL_TXT, TAIL_ORIG)):
        got = bytes(text[off:off + len(orig)])
        ok = got == orig
        print(f"RUNME {name:11s} text ${off:04x}: {got.hex()}  ({'match' if ok else 'MISMATCH'})")
        bad += not ok
    try:
        check_bss_pcrel_complete(text)
        for t, (reg, tgt) in BSS_LEAS.items():
            op, d = struct.unpack_from(">Hh", text, t)
            if op != 0x41FA | reg << 9 or t + 2 + d != tgt:
                raise SystemExit(f"text ${t:x} is not `lea ${tgt:x}(pc),a{reg}`")
        print(f"RUNME bss pc-relative references: {len(BSS_LEAS)} `lea d(pc),aN`, no others")
    except SystemExit as e:
        print(f"RUNME bss scan: {e}")
        bad += 1
    return bad


def cmd_list(patches, fpatches=()):
    print(f"{'name':18s} {'default':8s} {'site':8s} {'len':4s} blobs/data")
    for p in patches:
        blobs = ",".join(f"${o:x}" for o, _ in p.segments if o != p.site) or "-"
        data = ",".join(f"${a:x}+{l}" for a, l in p.data) or "-"
        seg = [s for s in p.segments if s[0] == p.site]
        ln = len(assemble(p.site, seg[0][1], "\n".join(p.preamble))) if seg else 0
        dflt = ("yes" if p.default else "no") + (" (floppy)" if p.media else "")
        print(f"{p.name:18s} {dflt:8s} ${p.site:05x}  {ln:4d} {blobs} / {data}")
    for p in fpatches:
        offs = ",".join(f"${o:x}" for o, _ in p.edits)
        print(f"{p.name:18s} {'yes' if p.default else 'no':8s} {p.image}+{offs}  "
              f"(file patch, {sum(len(b) for _, b in p.edits)} B)")


# ---- RUNME -------------------------------------------------------------------
def runme_source() -> bytes:
    src = pp_depack(( ORIG / "RUNME.TOS").read_bytes())
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
    """Every d16(pc) operand (ea mode 7/2) whose target is >= OLD_BSS must be listed in BSS_LEAS, else it
    would silently keep a stale displacement when the bss moves."""
    for t in range(0, TEXT_LEN - 3, 2):
        op, d = struct.unpack_from(">Hh", text, t)
        if op & 0x3F == 0x3A and t + 2 + d >= OLD_BSS and t not in BSS_LEAS and t not in NOT_CODE:
            raise SystemExit(f"text ${t:x}: unlisted pc-relative reference to ${t + 2 + d:x} (op {op:04x})")


def copy_routine(n_after: int) -> bytes:
    """Appended to RUNME's data: copies the payload (which follows PTRS_LEN bytes of bss pointers) to PB, then replays
    the `move.w #$2700,sr` it displaced from text $318.  Runs in supervisor mode, before the stage block is copied."""
    lines = ["copy:\tmovem.l\td0/a0-a1,-(a7)",
             "\tlea\tpayload(pc),a0",
             f"\tlea\t${PB:x}.l,a1",
             f"\tmove.w\t#{PAYLOAD_LEN // 4 - 1},d0",
             ".cp:\tmove.l\t(a0)+,(a1)+",
             "\tdbra\td0,.cp",
             "\tmovem.l\t(a7)+,d0/a0-a1",
             "\tmove.w\t#$2700,sr",
             "\trts",
             f"\tds.b\t{PTRS_LEN}",
             "payload:"]
    return assemble(OLD_BSS, lines)


def build_runme(img: bytes) -> bytes:
    src = runme_source()
    text = bytearray(src[28:28 + TEXT_LEN])
    data = src[28 + TEXT_LEN:28 + TEXT_LEN + 22]
    rel_off = 28 + TEXT_LEN + 22
    offs, rel_end = decode_reloc(src[rel_off:])
    assert rel_end == len(src) - rel_off
    cr = copy_routine(0)
    copy_len = len(cr) - PTRS_LEN            # code only; the pointer slots follow it
    n = copy_len + PTRS_LEN + PAYLOAD_LEN
    assert bytes(text[STAGE_TXT:STAGE_TXT + 4]) == STAGE_ORIG and bytes(text[TAIL_TXT:TAIL_TXT + 12]) == TAIL_ORIG
    # 1. stage hook: `bsr.w copy` (the copy routine replays the displaced `move.w #$2700,sr`)
    struct.pack_into(">Hh", text, STAGE_TXT, 0x6100, OLD_BSS - (STAGE_TXT + 2))
    # 2. PP's tail -> `jmp trampoline.l` (the trampoline replays `move.l #$1c42,$118.w`, ends in `jmp $1770.w`)
    text[TAIL_TXT:TAIL_TXT + 12] = struct.pack(">HI", 0x4EF9, PB) + b"\x4e\x71" * 3
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
    offs = sorted(offs + list(slot.values()))     # the pointer slots are absolute: the loader relocates them
    newdata = data + cr[:copy_len] + ptrs + img
    assert len(newdata) == 22 + n and len(cr) == copy_len + PTRS_LEN
    hdr = bytearray(src[:28])
    struct.pack_into(">I", hdr, 6, len(newdata))
    out = bytes(hdr) + bytes(text) + newdata + encode_reloc(offs)
    # round trip
    o2, e2 = decode_reloc(out[28 + TEXT_LEN + len(newdata):])
    assert o2 == offs
    return out


# ---- build -------------------------------------------------------------------
GAME_FILES = ["HAGA", "FP2273.HST", "LP2273.HST", "P2240R.BMP", "LOG.TXT", "README.TXT", "MANUAL.TXT"]
FILES_DIR = ["P2CR.TOS", "P2D", "P2M.FIC"]


def cmd_build(patches, out: Path, fpatches=()):
    if cmd_verify(patches, fpatches):
        raise SystemExit("build aborted: a site's orig does not match the game")
    img, sites = build_image(patches)
    runme = build_runme(img)
    shutil.rmtree(out, ignore_errors=True)
    (out / "FILES").mkdir(parents=True)
    for f in GAME_FILES:
        shutil.copy(ORIG / f, out / f)
    for f in FILES_DIR:
        shutil.copy(ORIG / "FILES" / f, out / "FILES" / f)
    (out / "RUNME.TOS").write_bytes(runme)
    apply_file_patches(fpatches, out)
    print(f"built {out} with {len(patches)} patch(es) + {len(fpatches)} file patch(es); payload {len(img)} B at ${PB:x}")
    print(f"{'site':8s} {'len':4s} orig -> new")
    for s in sites:
        print(f"${s['addr']:05x}  {len(s['orig']):4d} {s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]")


def cmd_live(patches, out: Path):
    if cmd_verify(patches):
        raise SystemExit("live aborted: a site's orig does not match the game")
    img, sites = build_image(patches)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".img").write_bytes(img)
    js = [{"addr": s["addr"], "orig": s["orig"].hex(), "new": s["new"].hex(), "name": s["name"]} for s in sites]
    out.with_suffix(".json").write_text(json.dumps({"img_base": PB, "sites": js}, indent=1))
    print(f"wrote {out.with_suffix('.img')} and {out.with_suffix('.json')} ({len(js)} sites)")


# ---- floppy build ------------------------------------------------------------
# A bootable 720K TOS floppy (9 sectors, 2 sides, 80 tracks, FAT12) holding the HD game folder: TOS runs
# AUTO\RUNME.PRG at boot (the patched RUNME), which finds HAGA, FP2273.HST and FILES\ through its
# relative file names exactly as on a hard disk.  The game fits one disk; only the STE cover picture
# fits with it (LP2273.HST for a plain ST and P2240R.BMP for TT/Falcon do not: RUNME simply skips a picture
# it cannot open, work/notes/delivery.md).  Needs mtools (mformat, mmd, mcopy).
FLOPPY_FILES = ["HAGA", "FP2273.HST"]
FLOPPY_LABEL = "POPULOUS2"


def mtools(*args, img=None):
    cmd = [args[0]] + (["-i", str(img)] if img else []) + list(args[1:])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"{' '.join(cmd)} failed: {r.stdout}{r.stderr}")
    return r.stdout


def cmd_build_floppy(patches, out: Path, fpatches=()):
    if shutil.which("mformat") is None:
        raise SystemExit("build --floppy needs mtools (mformat, mmd, mcopy)")
    if cmd_verify(patches, fpatches):
        raise SystemExit("build aborted: a site's orig does not match the game")
    img, sites = build_image(patches)
    runme = build_runme(img)
    shutil.rmtree(out, ignore_errors=True)
    stage = out / "stage"
    (stage / "AUTO").mkdir(parents=True)
    (stage / "FILES").mkdir()
    (stage / "AUTO" / "RUNME.PRG").write_bytes(runme)
    for f in FLOPPY_FILES:
        shutil.copy(ORIG / f, stage / f)
    for f in FILES_DIR:
        shutil.copy(ORIG / "FILES" / f, stage / "FILES" / f)
    apply_file_patches(fpatches, stage)
    disk = out / "Populous2_boot.st"
    mtools("mformat", "-C", "-f", "720", "-v", FLOPPY_LABEL, "-i", str(disk), "::")
    mtools("mmd", "::AUTO", "::FILES", img=disk)
    mtools("mcopy", "-m", str(stage / "AUTO" / "RUNME.PRG"), "::AUTO/RUNME.PRG", img=disk)
    for f in FLOPPY_FILES:
        mtools("mcopy", "-m", str(stage / f), f"::{f}", img=disk)
    for f in FILES_DIR:
        mtools("mcopy", "-m", str(stage / "FILES" / f), f"::FILES/{f}", img=disk)
    free = mtools("mdir", "::", img=disk).strip().splitlines()[-1]
    shutil.rmtree(stage)
    print(f"built {disk} ({disk.stat().st_size} B) with {len(patches)} patch(es) + {len(fpatches)} file patch(es); "
          f"payload {len(img)} B at ${PB:x}; {free.strip()}")
    for s in sites:
        print(f"${s['addr']:05x}  {len(s['orig']):4d} {s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]")




def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--only", nargs="*", default=None)
    b.add_argument("--out", default=None, help="default build/hd, or build/floppy with --floppy")
    g = b.add_mutually_exclusive_group()
    g.add_argument("--hd", action="store_true", help="hard-disk game folder (the default)")
    g.add_argument("--floppy", action="store_true", help="bootable 720K floppy image")
    lv = sub.add_parser("live")
    lv.add_argument("--only", nargs="*", default=None)
    lv.add_argument("--out", default="build/live/patches")
    sub.add_parser("list")
    sub.add_parser("verify")
    sub.add_parser("version", help="print the release version (the `; version:` header of patches/pop2_credit.s)")
    rd = sub.add_parser("doc", help="print a doc file with @VERSION@ replaced")
    rd.add_argument("file")
    a = ap.parse_args()
    if a.cmd == "version":
        print(release_version())
        return
    if a.cmd == "doc":
        sys.stdout.write(render_doc(Path(a.file).read_text()))
        return
    patches = load_patches()
    fpatches = load_file_patches()
    if a.cmd == "list":
        cmd_list(patches, fpatches)
        return
    if a.cmd == "verify":
        sys.exit(cmd_verify(patches, fpatches))
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
    if a.cmd == "build":
        if floppy:
            cmd_build_floppy(sel, ROOT / (a.out or "build/floppy"), fsel)
        else:
            cmd_build(sel, ROOT / (a.out or "build/hd"), fsel)
    else:
        if fsel and a.only is not None:
            raise SystemExit("file patches (HAGA) are not applicable to `live`: they are applied at build time")
        cmd_live(sel, ROOT / a.out)


if __name__ == "__main__":
    main()
