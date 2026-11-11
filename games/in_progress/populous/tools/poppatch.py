#!/usr/bin/env python3
"""Populous patch delivery tool (PP's HAGA conversion; design copied from Midwinter 2's mw2patch.py).

Patches are vasm sources in patches/ (format and mechanism: patches/README.md).  The tool assembles them,
verifies every site's expected ORIGINAL bytes against the game (POPULOUS.TOS / DEMO.TOS read out of the
disk image FILES/POP, relocated at the text base $AD96 they have in play, plus PP's three run-time patches),
cross-checked against work/dumps/g0.bin when that RAM dump exists, and produces a patched COPY of the game
in build/ (the originals are never touched).

    python3 tools/poppatch.py verify
    python3 tools/poppatch.py list
    python3 tools/poppatch.py build [--hd | --floppy] [--only NAME ...] [--out DIR] [--zip [PATH]]
    python3 tools/poppatch.py live  [--only NAME ...] [--out build/live/patches]
    python3 tools/poppatch.py version
    python3 tools/poppatch.py doc FILE
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
GAMEDIR = ROOT / "originals" / "POPULOUS"
PATCHDIR = ROOT / "patches"
RAMDUMP = ROOT / "work" / "dumps" / "g0.bin"            # 1 MB STE, in play, PP's patches applied (optional cross-check)
VASM = "vasmm68k_mot"
sys.path.insert(0, str(ROOT.parent.parent.parent / "tools"))
from pp_depack import depack as pp_depack  # noqa: E402

# ---- where things are in RAM ---------------------------------------------------------------------
TNOM = 0xAD96                   # text base of DEMO.TOS / POPULOUS.TOS in PP's layout (loader.s keeps it)
IMG_BASE = 0xB3000              # payload image: header, core, site table, blobs
IMG_LIMIT = 0xC8000             # blobs must end below this ($C0000-$C7FFF is the land-score code's)
ORG_HDR, ORG_APPLY, ORG_CORE2, ORG_CORE2B = 0xB3000, 0xB3010, 0xB3E00, 0xB3F00
META = 0xB3100                 # relocation list pointer.l, delta already applied.l, 2 spare longs
TABLE, TABLE_END = 0xB3110, 0xB3E00
BLOB_MIN, BLOB_MAX = 0xB4000, IMG_LIMIT - 1
MARKER = 0xB3004
# Words of POPULOUS.TOS text that change at run time (g0.bin vs the relocated image): a site must not touch them.
RUNTIME_TEXT = [(0x16D2C, 0x16D2E), (0x16F13, 0x16F16), (0x20063, 0x20066)]
# PP's own patches of the game, applied by his disk hook (POLA) while POPULOUS.TOS is read: RAM address -> bytes.
PP_PATCHES_POP = {0x1DC4A: "4ef86890", 0x1E11C: "4ef868a2", 0x2006C: "4eb86132"}
PP_PATCHES_DEMO: dict[int, str] = {}
PROGRAMS = {"demo": (0, "DEMO.TOS"), "populous": (1, "POPULOUS.TOS")}

# ---- the disk image FILES/POP (FAT12, 512-byte sectors, 2 sectors per cluster) ------------------------
class Fat12:
    def __init__(self, data: bytes):
        self.d = bytearray(data)
        (self.bps, self.spc, self.res, self.nfat, self.ndir, self.nsect, self.media, self.spf,
         self.spt, self.nsides) = struct.unpack_from("<HBHBHHBHHH", self.d, 0x0B)
        self.fat0 = self.res * self.bps
        self.root = (self.res + self.nfat * self.spf) * self.bps
        self.data0 = self.root + self.ndir * 32
        self.csz = self.spc * self.bps

    def coff(self, c: int) -> int:
        return self.data0 + (c - 2) * self.csz

    def get(self, c: int) -> int:
        o = self.fat0 + c * 3 // 2
        v = self.d[o] | (self.d[o + 1] << 8)
        return (v >> 4) if c & 1 else v & 0xFFF

    def chain(self, c: int):
        out = []
        while 2 <= c < 0xFF0:
            out.append(c)
            c = self.get(c)
        return out

    def _scan(self, raw: bytes):
        for i in range(len(raw) // 32):
            e = raw[i * 32:i * 32 + 32]
            if e[0] == 0:
                break
            if e[0] == 0xE5 or e[11] & 0x08:
                continue
            name = (e[:8].decode("latin1").rstrip() + "." + e[8:11].decode("latin1").rstrip()).rstrip(".")
            yield i, name, e[11], struct.unpack_from("<H", e, 26)[0], struct.unpack_from("<I", e, 28)[0]

    def dir_raw(self, cl: int = 0) -> bytes:
        if cl == 0:
            return bytes(self.d[self.root:self.data0])
        return b"".join(bytes(self.d[self.coff(c):self.coff(c) + self.csz]) for c in self.chain(cl))

    def entries(self, cl: int = 0):
        """(index, name, first cluster, size) of the files (not directories) in a directory."""
        for i, name, attr, c, size in self._scan(self.dir_raw(cl)):
            if not attr & 0x10:
                yield i, name, c, size

    def read(self, name: str) -> bytes:
        """`NAME.EXT` in the root, or `DIR/NAME.EXT` one level down."""
        cl = 0
        if "/" in name:
            d, name = name.split("/")
            cl = next(c for _, n, attr, c, _s in self._scan(self.dir_raw()) if n == d and attr & 0x10)
        for _, n, c, size in self.entries(cl):
            if n == name:
                return b"".join(bytes(self.d[self.coff(x):self.coff(x) + self.csz]) for x in self.chain(c))[:size]
        raise SystemExit(f"{name} not in the disk image")


    def replace(self, name: str, data: bytes):
        """Overwrite the content of an existing file (`DIR/NAME.EXT` as in read) in place; the size may shrink or grow
        within its clusters."""
        cl = 0
        if "/" in name:
            d, name = name.split("/")
            cl = next(c for _, n, attr, c, _s in self._scan(self.dir_raw()) if n == d and attr & 0x10)
        for i, n, c, size in self.entries(cl):
            if n != name:
                continue
            chain = self.chain(c)
            if len(data) > len(chain) * self.csz:
                raise SystemExit(f"{name}: {len(data)} bytes do not fit its {len(chain)} cluster(s)")
            base = (self.root if cl == 0 else self.coff(cl)) + i * 32
            for k, x in enumerate(chain):
                chunk = data[k * self.csz:(k + 1) * self.csz]
                self.d[self.coff(x):self.coff(x) + self.csz] = chunk + bytes(self.csz - len(chunk))
            struct.pack_into("<I", self.d, base + 28, len(data))
            return
        raise SystemExit(f"{name} not in the disk image")


_fat = None
def pop_disk() -> Fat12:
    global _fat
    if _fat is None:
        _fat = Fat12((GAMEDIR / "FILES" / "POP").read_bytes())
    return _fat


def prg_relocs(prg: bytes):
    tl, dl, _bl, sl = struct.unpack_from(">IIII", prg, 2)
    rel = prg[28 + tl + dl + sl:]
    off = struct.unpack_from(">I", rel, 0)[0]
    offs = []
    if off:
        offs.append(off)
        p = 4
        while True:
            x = rel[p]; p += 1
            if x == 0:
                break
            if x == 1:
                off += 254
            else:
                off += x
                offs.append(off)
    return offs


def reloc_image(prg: bytes, base: int):
    """text + data of a GEMDOS program as TOS leaves it after Pexec(3): relocated to `base`."""
    tl, dl, _bl, _sl = struct.unpack_from(">IIII", prg, 2)
    img = bytearray(prg[28:28 + tl + dl])
    offs = prg_relocs(prg)
    for o in offs:
        struct.pack_into(">I", img, o, struct.unpack_from(">I", img, o)[0] + base)
    return bytes(img), tl, dl, offs


_progs = {}
def program(prog: int):
    """(relocated image, text length, data length, reloc offsets) of DEMO.TOS (0) / POPULOUS.TOS (1)."""
    if prog not in _progs:
        name = {v[0]: v[1] for v in PROGRAMS.values()}[prog]
        _progs[prog] = reloc_image(pop_disk().read(name), TNOM)
    return _progs[prog]


def expected_ram(addr: int, ln: int, prog: int = 1):
    """What RAM holds between Pexec(3) and Pexec(4): the relocated image + PP's patches; None outside it."""
    img, tl, dl, _ = program(prog)
    if addr < TNOM or addr + ln > TNOM + tl + dl:
        return None
    b = bytearray(img[addr - TNOM:addr - TNOM + ln])
    for pa, pb in (PP_PATCHES_POP if prog == 1 else PP_PATCHES_DEMO).items():
        pbb = bytes.fromhex(pb)
        for i, x in enumerate(pbb):
            if addr <= pa + i < addr + ln:
                b[pa + i - addr] = x
    return bytes(b)


# ---- patch source parsing --------------------------------------------------------------------------
ORG_RE = re.compile(r"^\s*org\s+\$?([0-9a-fA-F]+)\s*$", re.I)
HB_ORG_RE = re.compile(r"^\s*org\s+HB\s*\+\s*\$([0-9a-fA-F]+)\s*$", re.I)
HDR_RE = re.compile(r"^;\s*([a-z]+):\s*(.*)$")
VERSION_TAG = "@VERSION@"
SPECIAL = ("core.s", "loader.s")


def release_version() -> str:
    """The release version: the `; version:` header of patches/pop_credit.s, the single place it is defined."""
    for f in sorted(PATCHDIR.glob("*.s")):
        m = re.search(r"^;\s*version:\s*(\S+)\s*$", f.read_text(), re.M)
        if m:
            return m.group(1)
    raise SystemExit("no `; version:` header in patches/*.s")


def render_doc(text: str) -> str:
    return text.replace(VERSION_TAG, release_version())


class Patch:
    def __init__(self, path: Path):
        self.path = path
        self.name = path.stem
        self.default = True
        self.site = None
        self.orig = None
        self.prog = 1
        self.mask = 0                    # machine classes the site applies to (bit 0 ST, 1 STE/Mega STE, 2 TT, 3 Falcon); 0 = all
        self.data = []
        self.segments = []
        self.preamble = []
        self.image = None
        self.media = None
        self.edits = []
        self.fsegments = []
        cur = None
        text = path.read_text()
        vm = re.search(r"^;\s*version:\s*(\S+)\s*$", text, re.M)
        self.version = vm.group(1) if vm else None
        if self.version:
            text = text.replace(VERSION_TAG, self.version)
        for line in text.splitlines():
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
                elif k == "prog":
                    if v.lower() not in PROGRAMS:
                        raise SystemExit(f"{path}: prog must be one of {sorted(PROGRAMS)}")
                    self.prog = PROGRAMS[v.lower()][0]
                elif k == "phase":
                    pass                      # MW2 header, meaningless here: every site is applied between Pexec(3) and Pexec(4)
                elif k == "data":
                    a, l = v.split()
                    self.data.append((int(a.lstrip("$"), 16), int(l, 0)))
                elif k == "image": self.image = v.strip()
                elif k == "media":
                    if v.strip().lower() not in ("floppy", "hd"):
                        raise SystemExit(f"{path}: media must be `floppy` or `hd`")
                    self.media = v.strip().lower()
                elif k == "machine":
                    self.mask = 0
                    for w in re.split(r"[,\s]+", v.lower()):
                        if w not in MACHINES:
                            raise SystemExit(f"{path}: machine must be a list of {sorted(MACHINES)}")
                        self.mask |= 1 << MACHINES[w]
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


def _load(pred):
    ps = []
    for f in sorted(PATCHDIR.glob("*.s")):
        if f.name in SPECIAL:
            continue
        p = Patch(f)
        if pred(p):
            ps.append(p)
    return ps


def load_patches():
    return _load(lambda p: p.site is not None)


def load_file_patches():
    ps = _load(lambda p: p.image is not None)
    for p in ps:
        if p.site is not None:
            raise SystemExit(f"{p.path.name}: `image:` and `site:` are mutually exclusive")
    return ps


# ---- assembly ----------------------------------------------------------------------------------------
MACHINES = {"st": 0, "ste": 1, "megaste": 1, "tt": 2, "falcon": 3}
# Where the game's own bytes end (text base + text + data + bss) per program: a literal address in [TNOM, end) in a
# patch source is an address of the game and moves with the program's load address (core.s `apply` adds the delta).
PROG_END = {0: TNOM + 23896 + 916 + 266978, 1: TNOM + 91916 + 7916 + 107008}
GD = 0x10000                    # the shift of the second assembly that finds the relocatable longs (reloc_assemble)
LIT_RE = re.compile(r"(?<![\w$])(#?)\$([0-9a-fA-F]{4,8})\b(?!\s*\()")
DC_SMALL_RE = re.compile(r"^\s*(?:\.?\w+:?\s+)?dc\.[bw]\b", re.I)


def _split_comment(line: str):
    q = None
    for i, c in enumerate(line):
        if q:
            if c == q:
                q = None
        elif c in "'\"":
            q = c
        elif c == ";":
            return line[:i], line[i:]
    return line, ""


def shift_game_literals(lines: list[str], lo: int, hi: int) -> list[str]:
    """The source with every hex literal in [lo, hi) written as ($lit+GD).  Not shifted: a `#$xxxx` of exactly four digits
    (a 16-bit immediate; write a long immediate game address with five or more digits, `#$0b6f4`), a `$xxxx(An)` displacement,
    the operands of dc.b / dc.w."""
    def rep(m):
        v = int(m.group(2), 16)
        if m.group(1) and len(m.group(2)) == 4:
            return m.group(0)
        return f"{m.group(1)}(${m.group(2)}+GD)" if lo <= v < hi else m.group(0)
    out = []
    for ln in lines:
        code, cm = _split_comment(ln)
        out.append((code if DC_SMALL_RE.match(code) else LIT_RE.sub(rep, code)) + cm)
    return out


def reloc_assemble(org: int, lines: list[str], preamble: list[str], prog: int, what: str):
    """(bytes, [offsets of the longs that hold game addresses]).  The bytes are those of a plain assembly.  A second
    assembly with every in-range literal shifted by GD = $10000 shows which longs follow the game's load address: they
    differ by exactly GD.  Any other difference (a 16-bit field, a pc-relative reach across the shift) is an error."""
    a = assemble(org, lines, "\n".join(preamble))
    hi = PROG_END[prog]
    org_b = org + GD if TNOM <= org < hi else org
    b = assemble(org_b, shift_game_literals(lines, TNOM, hi), "GD equ $%x\n" % GD + "\n".join(shift_game_literals(preamble, TNOM, hi)))
    if len(a) != len(b):
        raise SystemExit(f"{what}: the shifted assembly has a different length (a game address in a size-dependent operand?)")
    offs, i = [], 0
    while i < len(a):
        if a[i] == b[i]:
            i += 1
            continue
        s = i - (org + i) % 2                    # the long's first byte: the carry may leave its top byte alone
        la = a[s:s + 4]
        lb = b[s:s + 4]
        if s < 0 or len(la) < 4 or int.from_bytes(lb, "big") - int.from_bytes(la, "big") != GD:
            raise SystemExit(f"{what}: byte +${i:x} depends on a game address but is not a 32-bit absolute (pc-relative or 16-bit use?)")
        offs.append(s)
        i = s + 4
    return a, offs


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
    segs = {org: assemble(org, lines, "\n".join(p.preamble)) for org, lines in p.segments}
    if set(segs) != {ORG_HDR, ORG_APPLY, ORG_CORE2, ORG_CORE2B}:
        raise SystemExit(f"core.s orgs {sorted(map(hex, segs))} != header + apply + core2 + core2b")
    if ORG_APPLY + len(segs[ORG_APPLY]) > META:
        raise SystemExit("core.s apply overflows into the meta words")
    if ORG_CORE2 + len(segs[ORG_CORE2]) > ORG_CORE2B:
        raise SystemExit("core.s core2 overflows into core2b")
    if ORG_CORE2B + len(segs[ORG_CORE2B]) > BLOB_MIN:
        raise SystemExit("core.s core2b overflows into the blob area")
    return segs


# ---- HAGA file patches ---------------------------------------------------------------------------------
# PP's resident disk service is the file HAGA (identical in every PP conversion, md5 b34607ed...).  RUNME
# copies it to phystop - $8000: $F8000 on a 1 MB machine, $1F8000 on 2-3 MB.  A file patch edits HAGA bytes
# in the build copy with position independent code (`org HB+$off`, `; edit: $off <original bytes>`).
HAGA_RAM_2MB, HAGA_RAM_1MB = 0x1F8000, 0xF8000
FILE_IMAGES = ("HAGA",)


def file_patch_bytes(p: Patch) -> dict[int, bytes]:
    segs = {}
    for off, lines in p.fsegments:
        outs = [assemble(hb + off, lines, f"HB\tequ\t${hb:x}\n" + "\n".join(p.preamble))
                for hb in (HAGA_RAM_2MB, HAGA_RAM_1MB)]
        if outs[0] != outs[1]:
            raise SystemExit(f"{p.name}: segment HB+${off:x} is not position independent")
        if off in segs:
            raise SystemExit(f"{p.name}: two segments at HB+${off:x}")
        segs[off] = outs[0]
    return segs


def cmd_verify_files(fpatches) -> int:
    bad = 0
    ram = RAMDUMP.read_bytes() if RAMDUMP.exists() else None
    used = []
    for p in fpatches:
        print(f"{p.name:18s} image {p.image}  {len(p.edits)} edit(s)")
        if p.image not in FILE_IMAGES:
            raise SystemExit(f"{p.name}: unsupported image {p.image!r}")
        segs = file_patch_bytes(p)
        data = (GAMEDIR / p.image).read_bytes()
        if {o for o, _ in p.edits} != set(segs):
            print(f"    edit offsets {sorted(o for o, _ in p.edits)} != segment offsets {sorted(segs)}")
            bad += 1
            continue
        for off, orig in p.edits:
            new = segs[off]
            ib = data[off:off + len(orig)]
            db = ram[HAGA_RAM_1MB + off:HAGA_RAM_1MB + off + len(orig)] if ram else orig
            ok = ib == orig and db == orig and len(new) == len(orig)
            print(f"    HB+${off:04x} len {len(orig):2d}  orig {orig.hex()}")
            print(f"        file  {ib.hex()}  ({'match' if ib == orig else 'MISMATCH'})")
            print(f"        dump  {db.hex()}  ({'match' if db == orig else 'MISMATCH'}{'' if ram else ', no dump: skipped'})")
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


# ---- the payload image --------------------------------------------------------------------------------
RELOC_STATS: dict = {}


def site_seg(p: Patch):
    seg = [s for s in p.segments if s[0] == p.site]
    if not seg:
        raise SystemExit(f"{p.name}: no org ${p.site:x} segment")
    return seg[0][1]


def site_new(p: Patch):
    return assemble(p.site, site_seg(p), "\n".join(p.preamble))


def orig_relocs(addr: int, ln: int, prog: int, what: str):
    """Offsets in [addr, addr+ln) of the longs that TOS's relocation of the program made game addresses."""
    out = []
    for o in program(prog)[3]:
        ram = TNOM + o
        if ram < addr + ln and addr < ram + 4:
            if not (addr <= ram and ram + 4 <= addr + ln):
                raise SystemExit(f"{what}: the site cuts through a relocated long at ${ram:x}")
            if ram % 2:
                raise SystemExit(f"{what}: relocated long at odd address ${ram:x}")
            out.append(ram - addr)
    return out


def build_image(patches: list[Patch]):
    core = core_segments()
    sites = []
    for p in patches:
        new, nrel = reloc_assemble(p.site, site_seg(p), p.preamble, p.prog, f"{p.name} site ${p.site:x}")
        orig = p.orig if p.orig is not None else expected_ram(p.site, len(new), p.prog)
        if orig is None:
            raise SystemExit(f"{p.name}: site ${p.site:x} is outside the program's text/data")
        if len(new) > len(orig):
            raise SystemExit(f"{p.name}: new bytes longer than orig")
        if len(new) < len(orig):
            if (len(orig) - len(new)) % 2:
                raise SystemExit(f"{p.name}: odd nop padding")
            new = new + b"\x4e\x71" * ((len(orig) - len(new)) // 2)
        sites.append(dict(name=p.name, addr=p.site, orig=orig, new=new, prog=p.prog, mask=p.mask, nrel=nrel,
                          orel=orig_relocs(p.site, len(orig), p.prog, f"{p.name} site ${p.site:x}")))
    by_addr = sorted(sites, key=lambda s: (s["prog"], s["addr"]))
    for s, t in zip(by_addr, by_addr[1:]):
        if s["prog"] == t["prog"] and s["addr"] + len(s["orig"]) > t["addr"]:
            raise SystemExit(f"site overlap: {s['name']} ${s['addr']:x}+{len(s['orig'])} vs {t['name']} ${t['addr']:x}")
    n = len(sites)
    tbl_len = n * 16 + 4
    pool = bytearray()
    ptrs = []
    relocs = []                                  # addresses (in the payload) of longs that hold game addresses
    for i, s in enumerate(sites):
        relocs.append(TABLE + i * 16)            # the site's own address
        if len(pool) % 2:
            pool += b"\0"
        o = len(pool); pool += s["orig"]
        if len(pool) % 2:
            pool += b"\0"
        nw = len(pool); pool += s["new"]
        ptrs.append((TABLE + tbl_len + o, TABLE + tbl_len + nw))
        relocs += [TABLE + tbl_len + o + k for k in s["orel"]]
        relocs += [TABLE + tbl_len + nw + k for k in s["nrel"]]
    n_site = len(relocs)
    if TABLE + tbl_len + len(pool) > TABLE_END:
        raise SystemExit(f"site table + byte pool overflow ${TABLE:x}-${TABLE_END - 1:x}")
    placed = [(ORG_HDR, ORG_HDR + len(core[ORG_HDR])), (ORG_APPLY, ORG_APPLY + len(core[ORG_APPLY])),
              (ORG_CORE2, ORG_CORE2 + len(core[ORG_CORE2])), (ORG_CORE2B, ORG_CORE2B + len(core[ORG_CORE2B])),
              (META, META + 16), (TABLE, TABLE + tbl_len + len(pool))]
    blobs = []
    for p in patches:
        for org, lines in p.segments:
            if org == p.site:
                continue
            if not (BLOB_MIN <= org <= BLOB_MAX):
                raise SystemExit(f"{p.name}: org ${org:x} outside the blob area ${BLOB_MIN:x}-${BLOB_MAX:x}")
            b, brel = reloc_assemble(org, lines, p.preamble, p.prog, f"{p.name} blob ${org:x}")
            if org + len(b) > BLOB_MAX + 1:
                raise SystemExit(f"{p.name}: blob overflows the image (ends ${org + len(b) - 1:x})")
            placed.append((org, org + len(b)))
            blobs.append((org, b))
            relocs += [org + k for k in brel]
        for a, l in p.data:
            placed.append((a, a + l))
    placed.sort()
    for (a0, a1), (b0, b1) in zip(placed, placed[1:]):
        if a1 > b0:
            raise SystemExit(f"image overlap: ${a0:x}-${a1:x} vs ${b0:x}-${b1:x}")
    relocs = sorted(set(relocs))
    reloc_at = (max(e for _, e in placed) + 3) & ~3
    if reloc_at + 4 * (len(relocs) + 1) > 0xCFC37:
        raise SystemExit(f"the relocation list ends past $CFC36, the end of the proven free RAM (${reloc_at + 4 * (len(relocs) + 1):x})")
    placed.append((reloc_at, reloc_at + 4 * (len(relocs) + 1)))
    top = max(e for _, e in placed)
    img = bytearray(((top - IMG_BASE) + 3) & ~3)
    for org, b in core.items():
        img[org - IMG_BASE:org - IMG_BASE + len(b)] = b
    for i, s in enumerate(sites):
        struct.pack_into(">IHHII", img, TABLE - IMG_BASE + i * 16, s["addr"], len(s["orig"]), (s["mask"] << 8) | s["prog"], *ptrs[i])
    img[TABLE - IMG_BASE + tbl_len:TABLE - IMG_BASE + tbl_len + len(pool)] = pool
    for org, b in blobs:
        img[org - IMG_BASE:org - IMG_BASE + len(b)] = b
    struct.pack_into(">II", img, META - IMG_BASE, reloc_at, 0)
    for i, a in enumerate(relocs):
        struct.pack_into(">I", img, reloc_at - IMG_BASE + 4 * i, a)
    RELOC_STATS.update(total=len(relocs), sites=n_site, blobs=len(relocs) - n_site, at=reloc_at)
    return bytes(img), sites, [(a, e) for a, e in placed]


# ---- verification --------------------------------------------------------------------------------------
def check_site(addr: int, orig: bytes, prog: int):
    """(ok, image_ok, dump_ok, image bytes, dump bytes, why)"""
    ib = expected_ram(addr, len(orig), prog)
    why = ""
    if ib is None:
        return False, False, False, b"", b"", "outside the program's text/data"
    if prog == 1:
        for a, b in RUNTIME_TEXT:
            if addr < b and a < addr + len(orig):
                why = f"overlaps the run-time-changed text bytes ${a:x}-${b - 1:x}"
    dump_ok, db = True, b""
    if prog == 1 and RAMDUMP.exists():
        db = RAMDUMP.read_bytes()[addr:addr + len(orig)]
        dump_ok = db == ib
    return ib == orig and dump_ok and not why, ib == orig, dump_ok, ib, db, why


def mask_str(m: int) -> str:
    return ",".join(n for n in ("st", "ste", "tt", "falcon") if m & (1 << MACHINES[n]))


def cmd_verify(patches, fpatches=()):
    bad = 0
    for p in patches:
        new = site_new(p)
        orig = p.orig if p.orig is not None else expected_ram(p.site, len(new), p.prog) or b""
        ok, iok, dok, ib, db, why = check_site(p.site, orig, p.prog)
        pname = {v[0]: v[1] for v in PROGRAMS.values()}[p.prog]
        print(f"{p.name:18s} site ${p.site:05x} {pname} len {len(orig)}"
              + (f"  new {new.hex()}" if len(new) <= 16 else f"  new {len(new)} B"))
        print(f"    declared orig : {orig.hex()}")
        print(f"    image  bytes  : {ib.hex()}  ({'match' if iok else 'MISMATCH'})")
        if p.prog == 1:
            print(f"    ramdump bytes : {db.hex()}  ({'match' if dok else 'MISMATCH'}{'' if RAMDUMP.exists() else ', no dump: skipped'})")
        if why:
            print(f"    {why}")
        if not ok:
            bad += 1
    for p in patches:
        try:
            build_image([p])
        except SystemExit as e:
            print(f"{p.name}: build check FAILED: {e}")
            bad += 1
        else:
            print(f"{p.name:18s} relocation: {RELOC_STATS['sites'] - 1} long(s) in the site bytes, {RELOC_STATS['blobs']} in the blobs"
                  + (f"; machines {mask_str(p.mask)}" if p.mask else ""))
    bad += cmd_verify_files(fpatches)
    bad += cmd_verify_delivery()
    print("verify:", "ALL OK" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


def cmd_list(patches, fpatches=()):
    print(f"{'name':18s} {'default':8s} {'program':9s} {'site':8s} {'len':4s} blobs/data")
    for p in patches:
        blobs = ",".join(f"${o:x}" for o, _ in p.segments if o != p.site) or "-"
        data = ",".join(f"${a:x}+{l}" for a, l in p.data) or "-"
        ln = len(site_new(p))
        dflt = ("yes" if p.default else "no") + (f" ({p.media})" if p.media else "") + (f" [{mask_str(p.mask)}]" if p.mask else "")
        pname = {v[0]: v[1] for v in PROGRAMS.values()}[p.prog]
        print(f"{p.name:18s} {dflt:8s} {pname:9s} ${p.site:05x}  {ln:4d} {blobs} / {data}")
    for p in fpatches:
        offs = ",".join(f"${o:x}" for o, _ in p.edits)
        print(f"{p.name:18s} {'yes' if p.default else 'no':8s} {'HAGA':9s} +{offs}  "
              f"(file patch, {sum(len(b) for _, b in p.edits)} B)")


# ---- RUNME.TOS (HD staging of the payload, MW2 design) -----------------------------------------------------
# RUNME's unpacked image gains the payload in its data segment; a `jmp` at text $360 (the last move before PP's
# loader hands over to HAGA at $388) runs a copy routine that puts the image at $B3000 and replays the displaced
# `move.l $40e(pc),$60c.w`.  The bss moves up by N bytes, so the four pc-relative `lea d(pc),aN` that reach it
# become `movea.l d(pc),aN` loads from two relocated pointer slots, and every relocated long that points into the
# bss is adjusted (build_runme).
TEXT_LEN, DATA_LEN = 0x404E, 22
OLD_BSS = TEXT_LEN + DATA_LEN
STAGE_TXT = 0x360
STAGE_ORIG = bytes.fromhex("21fa00ac060c")             # move.l $40e(pc),$60c.w
RESUME_TXT = 0x366
BSS_LEAS = {0x9A: (1, 0x4284), 0x752: (2, 0x4284), 0x3D18: (2, 0x4064), 0x3D2A: (1, 0x4064)}
BSS_PTR_TARGETS = (0x4284, 0x4064)
# d16(pc)-looking words that are not operands: branch displacements and halves of absolute addresses
NOT_CODE = {0x3D58, 0x3D7C, 0x3F20, 0x3F62}
RUNME_MD5 = None


def runme_unpacked() -> bytes:
    return pp_depack((GAMEDIR / "RUNME.TOS").read_bytes())


def stage_code(nlongs: int):
    """The copy routine, assembled at text offset OLD_BSS; returns (bytes, offset of its `jmp` long in the bytes)."""
    src = [f"\torg\t${OLD_BSS:x}",
           "\tmovem.l\td0/a0-a1,-(a7)",
           "\tlea\timg(pc),a0",
           f"\tlea\t${IMG_BASE:x}.l,a1",
           f"\tmove.w\t#{nlongs - 1},d0",
           ".l:\tmove.l\t(a0)+,(a1)+",
           "\tdbra\td0,.l",
           "\tmovem.l\t(a7)+,d0/a0-a1",
           f"\tmove.l\t${STAGE_ORIG_TARGET:x}(pc),$60c.w",
           f"\tjmp\t${RESUME_TXT:x}.l",
           "\tcnop\t0,2",
           "ptrs:\tdc.l\t0,0",
           "img:"]
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "st.s"
        s.write_text("\n".join(src) + "\n")
        out = Path(td) / "st.bin"
        r = subprocess.run([VASM, "-Fbin", "-m68000", "-quiet", "-o", str(out), str(s)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"vasm failed (stage):\n{r.stderr}")
        b = out.read_bytes()
    return b


STAGE_ORIG_TARGET = STAGE_TXT + 2 + struct.unpack_from(">h", STAGE_ORIG, 2)[0]       # $40e


def build_runme(img: bytes) -> bytes:
    src = runme_unpacked()
    text_len, data_len, bss_len = struct.unpack_from(">III", src, 2)
    if (text_len, data_len) != (TEXT_LEN, DATA_LEN):
        raise SystemExit("RUNME.TOS is not the expected build (text $404e, data 22)")
    text = bytearray(src[28:28 + TEXT_LEN])
    data = src[28 + TEXT_LEN:28 + TEXT_LEN + DATA_LEN]
    offs = prg_relocs(src)
    if bytes(text[STAGE_TXT:STAGE_TXT + 6]) != STAGE_ORIG:
        raise SystemExit("RUNME text $360 is not the expected `move.l $40e(pc),$60c.w`")
    nlongs = len(img) // 4
    assert len(img) % 4 == 0 and nlongs - 1 <= 0xFFFF
    stage = stage_code(nlongs)
    ptrs_off = len(stage) - 8                              # the `dc.l 0,0` pointer slots end the routine; the image follows
    assert stage[ptrs_off - 6:ptrs_off - 4] == b"\x4e\xf9" and stage[ptrs_off:] == bytes(8)
    n = len(stage) + len(img)
    # 1. stage hook
    struct.pack_into(">HI", text, STAGE_TXT, 0x4EF9, OLD_BSS)
    # 2. bss moved by n
    check_bss_pcrel_complete(text)
    slot = {tgt: OLD_BSS + ptrs_off + 4 * i for i, tgt in enumerate(BSS_PTR_TARGETS)}
    for t, (reg, tgt) in BSS_LEAS.items():
        op, d = struct.unpack_from(">Hh", text, t)
        if op != (0x41FA | reg << 9) or t + 2 + d != tgt:
            raise SystemExit(f"RUNME text ${t:x} is not lea ${tgt:x}(pc),a{reg}")
        disp = slot[tgt] - (t + 2)
        assert 0 <= disp <= 0x7FFF, f"pointer slot out of reach of text ${t:x}"
        struct.pack_into(">Hh", text, t, 0x207A | reg << 9, disp)
    for o in offs:
        v = struct.unpack_from(">I", text, o)[0]
        if v >= OLD_BSS:
            struct.pack_into(">I", text, o, v + n)
    stage = bytearray(stage)
    for i, tgt in enumerate(BSS_PTR_TARGETS):
        struct.pack_into(">I", stage, ptrs_off + 4 * i, tgt + n)
    offs = list(offs)
    offs.append(STAGE_TXT + 2)                                  # the jmp into the stage routine
    offs.append(OLD_BSS + ptrs_off - 4)                         # the `jmp $366.l` operand at the end of the routine
    offs.extend(slot.values())                                  # the pointer slots are absolute: the loader relocates them
    offs = sorted(set(offs))
    newdata = data + bytes(stage) + img
    assert len(newdata) == DATA_LEN + n
    hdr = bytearray(src[:28])
    struct.pack_into(">I", hdr, 6, len(newdata))
    return bytes(hdr) + bytes(text) + newdata + encode_reloc(offs)


def check_bss_pcrel_complete(text: bytes):
    """Every d16(pc) operand whose target is in the bss must be in BSS_LEAS (else its displacement would go stale)."""
    for t in range(0, TEXT_LEN - 3, 2):
        op, d = struct.unpack_from(">Hh", text, t)
        if op & 0x3F == 0x3A and t + 2 + d >= OLD_BSS and t not in BSS_LEAS and t not in NOT_CODE:
            raise SystemExit(f"RUNME text ${t:x}: unlisted pc-relative reference to ${t + 2 + d:x} (op {op:04x})")


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


def decode_reloc(prg: bytes):
    return prg_relocs(prg)


# ---- POLA (PP's launcher program, FILES\POLA) -------------------------------------------------------------------
# POLA is a plain GEMDOS program: text $518 (its disk hook and loader of the game), data $D2 = a $20-byte header
# + the original AUTO\LOADER.PRG LZ-packed (178 -> 616 bytes) + padding.  Its code copies that data to $44000,
# unpacks the program over RUNME's text (at base page + $E4) and runs it as the process.  We replace the data with
# our loader.s program (same text size $240, no relocations).
POLA_TEXT, POLA_DATA = 0x518, 0xD2
POLA_END_OPERAND = 0x66           # text offset of the long in `lea $205ea.l,a2` (end of the data, text-relative)
POLA_HDR = 0x20


def lz_pack(data: bytes) -> bytes:
    """Greedy LZ in PP's format: 1..$7f literals; $80|n 1-byte offset (n+3 bytes); $C0|n 2-byte offset (n+4); 0 ends."""
    out = bytearray()
    lit = bytearray()

    def flush():
        while lit:
            chunk = lit[:127]
            del lit[:127]
            out.append(len(chunk))
            out.extend(chunk)

    i = 0
    n = len(data)
    while i < n:
        best_len, best_off = 0, 0
        for off in range(1, min(i, 65535) + 1):
            ln = 0
            while ln < 67 and i + ln < n and data[i + ln] == data[i + ln - off]:
                ln += 1
            cand = (min(ln, 66) if min(ln, 66) >= 3 else 0) if off <= 255 else (ln if ln >= 4 else 0)
            if cand > best_len:
                best_len, best_off = cand, off
        if best_len:
            flush()
            if best_off <= 255:
                out.append(0x80 | (best_len - 3))
                out.append(best_off)
            else:
                out.append(0xC0 | (best_len - 4))
                out += struct.pack(">H", best_off)
            i += best_len
        else:
            lit.append(data[i])
            i += 1
    flush()
    out.append(0)
    return bytes(out)


def lz_unpack(src: bytes) -> bytes:
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
            cnt += 4; off = (src[i] << 8) | src[i + 1]; i += 2
        else:
            cnt += 3; off = src[i]; i += 1
        for _ in range(cnt):
            out.append(out[-off])


def loader_prg(floppy: bool = False, pspan: int = 0) -> bytes:
    """patches/loader.s as a relocation-free GEMDOS program: 28-byte header, text, no symbols, one zero long.
    The HD variant is exactly $240 bytes of text (the stock footprint); the floppy variant is as long as it is."""
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "l.tos"
        cmd = [VASM, "-Ftos", "-m68000", "-quiet", "-o", str(out)]
        if floppy:
            cmd += ["-DFLOPPY=1", f"-DPSPAN={pspan}"]
        r = subprocess.run(cmd + [str(PATCHDIR / "loader.s")], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"vasm failed (loader):\n{r.stderr}")
        d = out.read_bytes()
    tl, dl, bl, sl = struct.unpack_from(">IIII", d, 2)
    if (dl, bl) != (0, 0) or (not floppy and tl != 0x240) or tl % 2:
        raise SystemExit(f"loader.s: text {tl:#x} data {dl} bss {bl}")
    rel = d[28 + tl + dl + sl:]
    if rel != b"\0\0\0\0":
        raise SystemExit("loader.s must be position independent (it has relocations)")
    hdr = bytearray(28)
    struct.pack_into(">HIIIIIIH", hdr, 0, 0x601A, tl, 0, 0, 0, 0, 0, 0)
    return bytes(hdr) + d[28:28 + tl] + b"\0\0\0\0"


def pola_orig() -> bytes:
    return (GAMEDIR / "FILES" / "POLA").read_bytes()


def pola_parts(pola: bytes):
    tl, dl, bl, sl = struct.unpack_from(">IIII", pola, 2)
    if (tl, dl, bl, sl) != (POLA_TEXT, POLA_DATA, 0, 0):
        raise SystemExit("FILES/POLA is not the expected build")
    text = pola[28:28 + tl]
    data = pola[28 + tl:28 + tl + dl]
    rel = pola[28 + tl + dl:]
    return text, data, rel


def original_loader() -> bytes:
    text, data, rel = pola_parts(pola_orig())
    return lz_unpack(data[POLA_HDR:])


def build_pola(floppy: bool = False) -> bytes:
    pola = pola_orig()
    text, data, rel = pola_parts(pola)
    if struct.unpack_from(">I", text, POLA_END_OPERAND)[0] != POLA_TEXT + POLA_DATA:
        raise SystemExit("POLA: `lea end-of-data` operand is not the expected value")
    prg = loader_prg(floppy)
    packed = lz_pack(prg)
    assert lz_unpack(packed) == prg
    hdr = bytearray(data[:POLA_HDR])
    struct.pack_into(">I", hdr, 2, len(packed))
    struct.pack_into(">I", hdr, 6, len(prg))
    nd = bytes(hdr) + packed
    nd += b"\0" * (-len(nd) % 4)
    text = bytearray(text)
    struct.pack_into(">I", text, POLA_END_OPERAND, POLA_TEXT + len(nd))
    h = bytearray(pola[:28])
    struct.pack_into(">I", h, 6, len(nd))
    return bytes(h) + bytes(text) + nd + rel


def cmd_verify_delivery() -> int:
    """The edit points of the delivery mechanism itself: RUNME, POLA."""
    bad = 0
    print("delivery: RUNME.TOS / POLA / loader")
    src = runme_unpacked()
    t = src[28:28 + TEXT_LEN]
    ok = bytes(t[STAGE_TXT:STAGE_TXT + 6]) == STAGE_ORIG
    print(f"    RUNME text ${STAGE_TXT:x}: {bytes(t[STAGE_TXT:STAGE_TXT + 6]).hex()}  ({'match' if ok else 'MISMATCH'}) move.l $40e(pc),$60c.w")
    bad += not ok
    for a, (reg, tgt) in BSS_LEAS.items():
        op, d = struct.unpack_from(">Hh", t, a)
        ok = op == (0x41FA | reg << 9) and a + 2 + d == tgt
        print(f"    RUNME text ${a:x}: lea ${tgt:x}(pc),a{reg}  ({'match' if ok else 'MISMATCH'})")
        bad += not ok
    try:
        check_bss_pcrel_complete(bytearray(t))
        print("    RUNME: no other pc-relative reference into the bss")
    except SystemExit as e:
        print(f"    {e}")
        bad += 1
    ok = original_loader()[:28] == bytes.fromhex("601a0000024000000000000000000000000000000000000000000000") and len(original_loader()) == 616
    print(f"    POLA: embedded original LOADER.PRG unpacks to 616 bytes  ({'match' if ok else 'MISMATCH'})")
    bad += not ok
    p = pop_disk().read("AUTO/LOADER.PRG")
    ok = p == original_loader()
    print(f"    POLA's embedded loader == AUTO\\LOADER.PRG of the disk image  ({'match' if ok else 'MISMATCH'})")
    bad += not ok
    bp = build_pola()
    print(f"    new POLA {len(bp)} bytes (limit 5000: RUNME reads 5000)")
    bad += len(bp) > 5000
    return bad


# ---- build (HD) ----------------------------------------------------------------------------------------------------
def cmd_build(patches, out: Path, fpatches=()):
    if cmd_verify(patches, fpatches):
        raise SystemExit("build aborted: a site's orig does not match the game")
    img, sites, _ = build_image(patches)
    runme = build_runme(img)
    shutil.rmtree(out, ignore_errors=True)
    shutil.copytree(GAMEDIR, out)
    (out / "RUNME.TOS").write_bytes(runme)
    (out / "FILES" / "POLA").write_bytes(build_pola())
    apply_file_patches(fpatches, out)
    print(f"built {out} with {len(patches)} patch(es) + {len(fpatches)} file patch(es); payload {len(img)} B at ${IMG_BASE:x}")
    print(f"{'site':8s} {'prog':8s} {'len':4s} orig -> new")
    print(f"relocation list: {RELOC_STATS['total']} longs at ${RELOC_STATS['at']:x}")
    for s in sites:
        print(f"${s['addr']:05x}  {'pop' if s['prog'] else 'demo':8s} {len(s['orig']):4d} "
              f"{s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]" + (f" machines {mask_str(s['mask'])}" if s["mask"] else ""))


def cmd_live(patches, out: Path):
    """What the HD boot would leave in RAM, for applying a patch set to a running snapshot: the payload image
    (`<out>.img`, load at $B3000) and the site bytes (`<out>.json`)."""
    if cmd_verify(patches):
        raise SystemExit("live aborted: a site's orig does not match the game")
    img, sites, _ = build_image(patches)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".img").write_bytes(img)
    js = [{"addr": s["addr"], "orig": s["orig"].hex(), "new": s["new"].hex(), "name": s["name"]}
          for s in sites if s["prog"] == 1 and (s["mask"] == 0 or s["mask"] & 2)]    # live = STE snapshots
    out.with_suffix(".json").write_text(json.dumps({"img_base": IMG_BASE, "sites": js}, indent=1))
    print(f"wrote {out.with_suffix('.img')} and {out.with_suffix('.json')} ({len(js)} sites)")


# ---- floppy build ---------------------------------------------------------------------------------------------
# FILES/POP is the game's disk A as a FAT12 volume (1 reserved sector, 2 x 5 FAT sectors, 7 directory sectors, 2
# sectors per cluster, AUTO\LOADER.PRG, DEMO.TOS, POPULOUS.TOS, data files; the clusters in use end at sector 779) padded
# with 224 zero sectors (room for PP's in-game saves; the BPB says 1024 sectors, 10 per track, 1 side).  FILES/POM is
# side 1 of the original double-sided disk, raw: DEMO.TOS reads track 0 sector 1 of side 1 (first byte $39 = "double
# sided disk"), then loads side 1 tracks 0-38 (200 KB of title music) with XBIOS Floprd; sectors 392-399 and 520-779
# (tracks 52-77) are formatted-empty ($E5).
# The floppy is therefore the physical 80 x 10 x 2 disk again: side 0 = POP's first 800 sectors (BPB set to 800), side 1 =
# POM, tracks interleaved.  The BPB keeps `1 side`, so TOS reaches the file system on side 0 only, as on the original
# disk.  AUTO\LOADER.PRG is replaced by patches/loader.s (FLOPPY) and the payload goes into POM's empty tracks 52-77.
PAYLOAD_TRACK0, PAYLOAD_TRACK_END = 52, 78          # side 1 track-sides 52..77 are $E5 filler in POM
SAVE_SERIAL = bytes.fromhex("504f5053")


def floppy_conflicts(sites):
    """Sites whose original bytes would differ on floppy: those overlapping PP's run-time patches of the game."""
    bad = []
    for s in sites:
        if s["prog"] != 1:
            continue
        for pa, pb in PP_PATCHES_POP.items():
            if s["addr"] < pa + len(pb) // 2 and pa < s["addr"] + len(s["orig"]):
                bad.append(f"{s['name']} ${s['addr']:x}+{len(s['orig'])} overlaps PP patch ${pa:x}")
    return bad


def payload_segments(img: bytes, ranges):
    """The used parts of the payload image as [(dest, bytes)], neighbours closer than 1 KB merged."""
    rs = []
    for a, e in sorted(ranges):
        if rs and a - rs[-1][1] < 1024:
            rs[-1][1] = max(rs[-1][1], e)
        else:
            rs.append([a, e])
    return [(a, img[a - IMG_BASE:e - IMG_BASE]) for a, e in rs]


def floppy_pom(segs) -> bytes:
    """POM with the payload directory + segments written into its empty side-1 tracks."""
    pom = bytearray((GAMEDIR / "FILES" / "POM").read_bytes())
    if len(pom) != 409600:
        raise SystemExit("POM is not 80 x 10 x 512 bytes")
    nt = 1 + sum((len(b) + 5119) // 5120 for _, b in segs)
    if PAYLOAD_TRACK0 + nt > PAYLOAD_TRACK_END:
        raise SystemExit(f"payload needs {nt} track-sides, POM has {PAYLOAD_TRACK_END - PAYLOAD_TRACK0} empty ones")
    if len(segs) > 50:
        raise SystemExit("too many payload segments")
    for t in range(PAYLOAD_TRACK0, PAYLOAD_TRACK0 + nt):
        if set(pom[t * 5120:(t + 1) * 5120]) != {0xE5}:
            raise SystemExit(f"POM track-side {t} is not empty")
    hdr = bytearray(b"POPD" + struct.pack(">H", len(segs)))
    t = PAYLOAD_TRACK0 + 1
    body = []
    for dest, b in segs:
        hdr += struct.pack(">IIH", dest, len(b), t)
        body.append((t, b))
        t += (len(b) + 5119) // 5120
    pom[PAYLOAD_TRACK0 * 5120:PAYLOAD_TRACK0 * 5120 + 512] = bytes(hdr) + bytes(512 - len(hdr))
    for tt, b in body:
        pom[tt * 5120:tt * 5120 + len(b)] = b
        pad = (-len(b)) % 5120
        pom[tt * 5120 + len(b):tt * 5120 + len(b) + pad] = bytes(pad)         # the loader reads whole track-sides: zero tail
    return bytes(pom)


def floppy_pop(pspan: int) -> bytes:
    """The 800-sector FAT volume of side 0: POP's first 800 sectors, BPB sectors = 800, our AUTO\\LOADER.PRG."""
    fat = Fat12((GAMEDIR / "FILES" / "POP").read_bytes())
    last = max(c for _, _, cl, _ in fat.entries() for c in fat.chain(cl))
    top = 18 + (last - 1) * 2
    if top > 800:
        raise SystemExit("the volume's clusters do not fit 800 sectors")
    struct.pack_into("<H", fat.d, 0x13, 800)
    fat.replace("AUTO/LOADER.PRG", loader_prg(True, pspan))
    return bytes(fat.d[:800 * 512])


def save_disk() -> bytes:
    """A blank, TOS-formatted 720 KB disk (80 x 9 x 2) for the game's save files."""
    d = bytearray(1440 * 512)
    d[0:3] = b"\xeb\x34\x90"
    d[3:11] = b"POPSAVE "
    d[8:11] = SAVE_SERIAL[:3]                       # the serial TOS uses to notice a disk change
    struct.pack_into("<HBHBHHBHHHH", d, 0x0B, 512, 2, 1, 2, 112, 1440, 0xF9, 3, 9, 2, 0)
    for off in (512, 512 + 3 * 512):
        d[off:off + 3] = bytes([0xF9, 0xFF, 0xFF])
    return bytes(d)


def interleave(side0: bytes, side1: bytes) -> bytes:
    out = bytearray()
    for t in range(80):
        out += side0[t * 5120:(t + 1) * 5120] + side1[t * 5120:(t + 1) * 5120]
    return bytes(out)


FLOPPY_FILES = ("Populous_boot.st", "Populous_save.st")


def cmd_build_floppy(patches, out: Path, fpatches=()):
    if cmd_verify(patches, ()):
        raise SystemExit("build aborted: a site's orig does not match the game")
    img, sites, ranges = build_image(patches)
    bad = floppy_conflicts(sites)
    if bad:
        raise SystemExit("build aborted: site differs on floppy:\n  " + "\n  ".join(bad))
    segs = payload_segments(img, ranges)
    pspan = max(d + ((len(b) + 5119) // 5120) * 5120 for d, b in segs) - IMG_BASE + 512
    game = interleave(floppy_pop(pspan), floppy_pom(segs))
    assert len(game) == 819200
    out.mkdir(parents=True, exist_ok=True)
    (out / FLOPPY_FILES[0]).write_bytes(game)
    (out / FLOPPY_FILES[1]).write_bytes(save_disk())
    print(f"built floppy set in {out}: {', '.join(FLOPPY_FILES)}; {len(patches)} patch(es); payload {len(img)} B span, "
          f"{sum(len(b) for _, b in segs)} B in {len(segs)} segment(s) on side 1 tracks {PAYLOAD_TRACK0}-"
          f"{PAYLOAD_TRACK0 + sum((len(b) + 5119) // 5120 for _, b in segs)}")
    for fp in fpatches:
        print(f"skipped file patch {fp.name}: needs PP's HAGA service, which is not on floppy")
    print(f"{'site':8s} {'prog':8s} {'len':4s} orig -> new")
    print(f"relocation list: {RELOC_STATS['total']} longs at ${RELOC_STATS['at']:x}")
    for s in sites:
        print(f"${s['addr']:05x}  {'pop' if s['prog'] else 'demo':8s} {len(s['orig']):4d} "
              f"{s['orig'].hex()} -> {s['new'].hex()}   [{s['name']}]" + (f" machines {mask_str(s['mask'])}" if s["mask"] else ""))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--only", nargs="*", default=None)
    b.add_argument("--out", default=None, help="default build/hd, or build/floppy with --floppy")
    g = b.add_mutually_exclusive_group()
    g.add_argument("--hd", action="store_true", help="the hard-disk build (default)")
    g.add_argument("--floppy", action="store_true", help="the bootable floppy image set")
    b.add_argument("--zip", nargs="?", const="", default=None, metavar="PATH")
    lv = sub.add_parser("live")
    lv.add_argument("--only", nargs="*", default=None)
    lv.add_argument("--out", default="build/live/patches")
    sub.add_parser("list")
    sub.add_parser("verify")
    sub.add_parser("version", help="print the release version (the `; version:` header of patches/pop_credit.s)")
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
    ok_media = (None, "floppy") if floppy else (None, "hd")
    if a.only is None:
        sel = [p for p in patches if p.default and p.media in ok_media]
        fsel = [p for p in fpatches if p.default]
    else:
        names = set(a.only)
        unknown = names - {p.name for p in patches} - {p.name for p in fpatches}
        if unknown:
            raise SystemExit(f"unknown patch(es): {sorted(unknown)}")
        sel = [p for p in patches if p.name in names]
        wrong = sorted(p.name for p in sel if p.media not in ok_media)
        if wrong:
            raise SystemExit(f"patch(es) {wrong} are for the other medium")
        fsel = [p for p in fpatches if p.name in names]
    if a.cmd == "live":
        if fsel and a.only is not None:
            raise SystemExit("file patches (HAGA) are not applicable to `live`: they are applied at build time")
        cmd_live(sel, ROOT / a.out)
    elif floppy:
        if fsel and a.only is not None:
            raise SystemExit("file patches (HAGA) are not applicable to --floppy: there is no HAGA service on floppy")
        cmd_build_floppy(sel, ROOT / (a.out or "build/floppy"), fsel)
    else:
        if a.zip is not None:
            raise SystemExit("--zip is written by tools/package.sh")
        cmd_build(sel, ROOT / (a.out or "build/hd"), fsel)


if __name__ == "__main__":
    main()
