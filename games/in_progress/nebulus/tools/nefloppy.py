#!/usr/bin/env python3
r"""Nebulus (Tower Toppler) FLOPPY delivery: patches the user's original floppy image (alt/floppy/*.st).  Evidence: work/notes/floppy.md.

The floppy's own loader (AUTO\TOWERTOP.PRG, Atomik-packed) raw-reads TOPPLER.JMP to $33B00 and jumps there; TOPPLER.JMP is the GEMDOS image of the
same game as PP's NEBEXE.FIC (same code base, different build: 60 Hz only, a few displaced blocks).  There is no START.TOS / Gamex, so the HD
delivery (nepatch: runtime stub + NEPATCH.BIN) does not apply.  Instead the FILE is patched statically (the disk is the release):
  1. TOPPLER.JMP is RELOCATED at build time ($33B1C, the only address it ever runs at) and its header's absolute flag word (`cmpi.w #-1,$1a(a2)` in the
     file's own relocator) is set, so the relocator just jumps; the relocation table (2495 B) is dropped;
  2. the patch sites of patches/*.nep are written at their floppy addresses (same code, shifted by -36/-24/-12/-8 bytes after text offsets $4c46, $8406,
     $8436, $850a; original bytes of every site are compared with PP's, instruction by instruction, before anything is written);
  3. blobs (editor, trainers, latch, credit line) are assembled from the SAME sources as the HD build with the 25 game addresses mapped, and sit at the
     same RAM addresses as in the HD build ($75720..$77EC0 = where the table used to be + zero gap): the file grows by 8.7 KB (loader reads whole
     sectors by the directory size);
  4. the file's final `jmp` goes to a 40-byte stub at $77EC0 (marker 'NEPO'; on a 512 KB machine it takes the editor's title hook out again because the
     editor needs RAM above $80000) that jumps to the game entry $38624;
  5. the FAT12 image is rewritten in place (TOPPLER.JMP grows, TOPPLER.NEO moves up; boot sector, AUTO\, PLANE.NEO untouched).
Commands:  verify | build [--only P..] [--out DIR] [--corrupt] | selftest | campaign OUT.st
"""
from __future__ import annotations

import argparse, hashlib, re, struct, subprocess, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent
sys.path.insert(0, str(HERE))
import nepatch  # noqa: E402

SRC_IMG = GAME / "alt/floppy/Nebulus (1988)(Hewson)[cr Atari Legend].st"
SRC_MD5 = "32469782608f012a88dfa6a50de1e10f"          # whole image
JMP_MD5 = "8c9a62a4a2261a46d5c3a2d54639819b"          # TOPPLER.JMP inside it
VASM = "vasmm68k_mot"
PATCHES = GAME / "patches"

BASE = 0x33B00            # the loader reads TOPPLER.JMP here and jumps here
RB = 0x33B1C              # = BASE + 28: the image's own relocation base (text start)
ZONE_LO = 0x75720         # end of text+data = where the relocation table was (same value as 0x75728 - 8 of PP's build)
ZONE_HI = 0x77EC0         # patch RAM ends here (same limit as the HD build)
STUB = 0x77EC0            # entry stub + marker
FILE_END = 0x77F00        # = 546 sectors = 273 clusters of the file
ENTRY = 0x38624           # game entry (`lea $800,a7 / jmp $3db62`); the original relocator's jmp operand is $4b08 + RB
PP_TEXT, PP_DATA = 0xA866, 0x373A6
FL_TEXT, FL_DATA = 0xA85E, 0x373A6
# floppy text offset = PP text offset - delta for PP text offsets in [lo, hi)   (hi of the last = end of text; the data segment is shifted by 8)
SEG = [(0, 0x4C46, 0), (0x4C78, 0x8406, 36), (0x8406, 0x8436, 24), (0x8436, 0x850A, 12), (0x850A, PP_TEXT, 8)]
TITLE_SITE = 0x3D6C4      # ed_overlay's title-poll site (PP address): restored by the stub on a 512 KB machine
CREDIT_ADDR = 0x77A00
NT_ADDR = 0x76C00
NEO_CLUSTER = 342         # TOPPLER.NEO moves here (was 309): JMP grows to 43..315 and cluster 341 stays untouched (its first sector, log. 696 = track 69 sector 7,
                          # holds a hidden 448-byte program that the loader's GEMDOS calls read; the new NEO position must not overwrite it)
MSG_NODISK = "Kept in RAM (no disk)"


# ------------------------------------------------------------------ address mapping (PP build -> floppy build)
def map_off(o: int):
    for lo, hi, d in SEG:
        if lo <= o < hi:
            return o - d
    return None


def map_addr(a: int) -> int:
    """PP absolute address -> floppy absolute address (identity outside the relocated image)."""
    o = a - RB
    if o < 0 or a >= ZONE_LO + 8:
        return a
    if o < PP_TEXT:
        r = map_off(o)
        if r is None:
            raise SystemExit(f"address ${a:x} lies in a block that differs between the builds (text offset ${o:x}); no mapping")
        return RB + r
    return a - 8


def remap_source(text: str) -> str:
    """Replace every `$xxxxx` literal in code (not in strings, not in comments) that points into PP's relocated image by the floppy address."""
    out = []
    for line in text.split("\n"):
        code, sc, comment = line.partition(";")
        parts = re.split(r"('[^']*')", code)
        for i in range(0, len(parts), 2):
            parts[i] = re.sub(r"\$([0-9a-fA-F]{5,6})\b", lambda m: _rm(m), parts[i])
        out.append("".join(parts) + sc + comment)
    return "\n".join(out)


def _rm(m):
    v = int(m.group(1), 16)
    if RB <= v < ZONE_LO + 8:
        n = map_addr(v)
        t = "%x" % n
        return "$" + (t.upper() if any(ch in "ABCDEF" for ch in m.group(1)) else t)
    return m.group(0)


# ------------------------------------------------------------------ GEMDOS images
def parse_gemdos(g: bytes):
    ts, ds, bss, sym = struct.unpack(">LLLL", g[2:18])
    assert g[:2] == b"\x60\x1a" and bss == 0 and sym == 0
    return ts, ds, nepatch.reloc_offsets(g)


def relocated(g: bytes) -> bytearray:
    ts, ds, offs = parse_gemdos(g)
    b = bytearray(g[28:28 + ts + ds])
    for o in offs:
        b[o:o + 4] = struct.pack(">L", (struct.unpack(">L", b[o:o + 4])[0] + RB) & 0xFFFFFFFF)
    return b


# ------------------------------------------------------------------ FAT12 floppy image
class Disk:
    def __init__(self, img: bytes):
        self.b = bytearray(img)
        b = self.b
        self.bps, self.spc, self.res, self.nfat, self.ndir, self.nsec, _, self.spf = struct.unpack("<HBHBHHBH", bytes(b[11:24]))
        assert (self.bps, self.spc, self.nfat, self.spf, self.ndir) == (512, 2, 2, 5, 112), "unexpected BPB"
        self.fat0 = self.res * 512
        self.dir0 = (self.res + self.nfat * self.spf) * 512
        self.data0 = self.dir0 + self.ndir * 32
        self.ncl = (self.nsec * 512 - self.data0) // (self.spc * 512)

    def fat(self, n):
        o = self.fat0 + n * 3 // 2
        v = self.b[o] | self.b[o + 1] << 8
        return (v >> 4) if n & 1 else (v & 0xFFF)

    def set_fat(self, n, val):
        for k in range(self.nfat):
            o = self.fat0 + k * self.spf * 512 + n * 3 // 2
            v = self.b[o] | self.b[o + 1] << 8
            v = (v & 0x000F) | (val << 4) if n & 1 else (v & 0xF000) | val
            self.b[o], self.b[o + 1] = v & 0xFF, v >> 8

    def chain(self, c):
        out = []
        while 2 <= c < 0xFF8:
            out.append(c); c = self.fat(c)
        return out

    def entries(self):
        for i in range(self.ndir):
            o = self.dir0 + i * 32
            if self.b[o] in (0, 0xE5):
                continue
            yield i, o, bytes(self.b[o:o + 11])

    def find(self, name11: bytes):
        for i, o, n in self.entries():
            if n == name11:
                return o
        raise KeyError(name11)

    def cl_off(self, c):
        return self.data0 + (c - 2) * self.spc * 512

    def read(self, o):
        size = struct.unpack("<L", self.b[o + 28:o + 32])[0]
        data = b"".join(bytes(self.b[self.cl_off(c):self.cl_off(c) + self.spc * 512]) for c in self.chain(struct.unpack("<H", self.b[o + 26:o + 28])[0]))
        return data[:size]

    def rewrite(self, files):
        """files = [(dir offset, data, first cluster)]: free the old chains of all of them first, then write each as a contiguous chain."""
        cs = self.spc * 512
        for o, _, _ in files:
            for c in self.chain(struct.unpack("<H", self.b[o + 26:o + 28])[0]):
                self.set_fat(c, 0)
        for o, data, first in files:
            n = (len(data) + cs - 1) // cs
            assert first + n - 1 < self.ncl + 2, "disk full"
            for k in range(n):
                c = first + k
                self.set_fat(c, c + 1 if k < n - 1 else 0xFFF)
                self.b[self.cl_off(c):self.cl_off(c) + cs] = data[k * cs:(k + 1) * cs].ljust(cs, b"\0")
            struct.pack_into("<H", self.b, o + 26, first)
            struct.pack_into("<L", self.b, o + 28, len(data))


# ------------------------------------------------------------------ sources -> blobs
def vasm_bin(src: str) -> bytes:
    with tempfile.TemporaryDirectory() as d:
        s, o = Path(d) / "a.s", Path(d) / "a.bin"
        s.write_text(src)
        r = subprocess.run([VASM, "-Fbin", "-m68000", "-no-opt", "-o", str(o), str(s)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"vasm failed:\n{r.stdout}\n{r.stderr}")
        return o.read_bytes()


def gen_credit(remap: bool):
    import nebrelease
    text = f"v{nebrelease.version()} enhanced by dad_prg"
    src = (PATCHES / "cr_credit.s").read_text().replace("@TEXT@", text)
    if remap:
        src = remap_source(src)
    return [(CREDIT_ADDR, nepatch.asm(CREDIT_ADDR, src))], {}


def gen_latch(remap: bool):
    src = (PATCHES / "ni_latch.s").read_text()
    if remap:
        src = remap_source(src)
    return [(0x76D00, vasm_bin(src))], {}


def gen_trainers(remap: bool):
    src = (PATCHES / "nt_keys.s").read_text().splitlines()
    i = next(n for n, l in enumerate(src) if re.match(r"\s*org\s+NT\s*$", l))
    body = "\n".join(src[i:])
    if remap:
        body = remap_source(body)
    return [(NT_ADDR, vasm_bin(f"NT equ ${NT_ADDR:x}\n{body}\n"))], {}


def _asm_editor(txt: str):
    """gen_ed.py's assembly: -> (segments [(addr, bytes)] of the S-records, symbols {name: addr}, equates)."""
    eq = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"^(\w+)\s+equ\s+\$([0-9a-f]+)", txt, re.M)}
    txt2 = re.sub(r"\b(bra|bsr|b(?:eq|ne|cc|cs|hs|lo|hi|ls|mi|pl|ge|lt|gt|le|vc|vs))\.s\b", r"\1", txt)
    with tempfile.TemporaryDirectory() as d:
        s_, o, l = Path(d) / "e.s", Path(d) / "e.srec", Path(d) / "e.lst"
        s_.write_text(txt2)
        r = subprocess.run([VASM, "-Fsrec", "-m68000", "-L", str(l), "-o", str(o), str(s_)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(r.stdout + r.stderr)
        mem = {}
        for ln in o.read_text().splitlines():
            if ln.startswith("S3"):
                n = int(ln[2:4], 16); addr = int(ln[4:12], 16); data = bytes.fromhex(ln[12:12 + (n - 5) * 2])
                for k, v in enumerate(data):
                    assert addr + k not in mem
                    mem[addr + k] = v
        lst = l.read_text()
    segs = []
    for ad in sorted(mem):
        if segs and segs[-1][0] + len(segs[-1][1]) == ad:
            segs[-1][1].append(mem[ad])
        else:
            segs.append((ad, bytearray([mem[ad]])))
    segs = [(ad, bytes(v)) for ad, v in segs]
    assert [ad for ad, _ in segs] == [eq["CODE1"], eq["DATA"], eq["CODE2"]], [(hex(ad), len(v)) for ad, v in segs]
    sym = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"^(\w+)\s+A:([0-9A-Fa-f]+)", lst, re.M)}
    return segs, sym


def gen_editor(remap: bool):
    """gen_ed.py's assembly of patches/ed_editor.s; the floppy variant maps the game addresses and replaces the disk save (a TOS excursion through
    the Gamex TOS image, which only exists in PP's START.TOS flow) by a message.  The replacement changes the code size, so entry points that
    the .nep sites jump to directly (ed_key, ed_opt) move: `symmap` translates the HD build's addresses to the floppy build's (by symbol)."""
    txt = (PATCHES / "ed_editor.s").read_text()
    segs, sym = _asm_editor(txt)
    if not remap:
        return segs, {}
    ftxt = remap_source(txt)
    a = re.search(r"^save_file:\n", ftxt, re.M)
    b = re.search(r"^swap_tos:\n", ftxt, re.M)
    assert a and b and a.start() < b.start(), "ed_editor.s: save_file/swap_tos anchors changed; update tools/nefloppy.py"
    ftxt = (ftxt[:a.start()] + "save_file:\n        lea     sNoFl(pc),a0\n        move.l  a0,vMsg(a5)\n        rts\n"
            f"sNoFl:  dc.b    '{MSG_NODISK}',0\n        even\n\n" + ftxt[b.start():])
    fsegs, fsym = _asm_editor(ftxt)
    symmap = {}
    for name, ad in sym.items():
        if name in fsym and fsym[name] != ad and ad >= ZONE_LO:
            if symmap.get(ad, fsym[name]) != fsym[name]:
                raise SystemExit(f"ed_editor.s: symbols at ${ad:x} map to different floppy addresses")
            symmap[ad] = fsym[name]
    return fsegs, symmap


GENS = {"cr_credit": gen_credit, "ni_latch": gen_latch, "nt_trainers": gen_trainers, "ed_overlay": gen_editor}
SITE_ONLY = {"ni_jump", "ni_shoot", "ni_hop", "ni_turn", "nt_freeze_static", "nt_noenemy_static"}


# ------------------------------------------------------------------ comparison of sites with PP's game
import capstone  # noqa: E402
_md = capstone.Cs(capstone.CS_ARCH_M68K, capstone.CS_MODE_BIG_ENDIAN | capstone.CS_MODE_M68K_000)


def _norm_dis(code: bytes, addr: int, mapper):
    out = []
    for ins in _md.disasm(code, addr):
        ops = re.sub(r"\$([0-9a-fA-F]{5,8})\b", lambda m: "$%x" % mapper(int(m.group(1), 16)), ins.op_str)
        out.append((ins.mnemonic, ops, ins.size))
    return out


def site_equivalent(pp_ram: bytes, fl_img: bytes, pp_addr: int, length: int) -> bool:
    """Do PP's `length` bytes at pp_addr and the floppy's at map_addr(pp_addr) hold the same instructions (absolute operands and branch targets mapped)?"""
    fa = map_addr(pp_addr)
    a = _norm_dis(bytes(pp_ram[pp_addr:pp_addr + length]), pp_addr, map_addr)
    b = _norm_dis(bytes(fl_img[fa - BASE:fa - BASE + length]), fa, lambda x: x)
    return bool(a) and a == b and sum(s for *_, s in a) == length == sum(s for *_, s in b)


# ------------------------------------------------------------------ build
class Plan:
    def __init__(self, names, remap=True):
        allp = {p.name: p for p in nepatch.load_patches()}
        self.names = names
        self.sites, self.blocks = [], []
        for n in names:
            if n not in allp:
                raise SystemExit(f"unknown patch {n}")
            if n not in GENS and n not in SITE_ONLY:
                raise SystemExit(f"{n}: no floppy translation in tools/nefloppy.py (GENS / SITE_ONLY): its sites are in PP's address map and its blobs are assembled from "
                                 "game addresses; add a generator before shipping it on the floppy")
            p = allp[n]
            for a, new in p.sites:
                if a >= ZONE_LO:
                    continue                      # blob stored as a `site`: replaced by the generated blocks below
                self.sites.append((n, a, new))
            self.symmap = getattr(self, "symmap", {})
            if n in GENS:
                gen, sm = GENS[n](remap)
                self.blocks += [(n, ad, d) for ad, d in gen]
                self.symmap.update(sm)


def translate_new(new: bytes, symmap: dict) -> bytes:
    """jmp/jsr abs.l targets that moved between the HD and the floppy assembly (same symbol, other address)."""
    out = bytearray(new); i = 0
    while i < len(out):
        w = bytes(out[i:i + 2])
        if w in (b"\x4e\xf9", b"\x4e\xb9"):
            t = struct.unpack(">L", out[i + 2:i + 6])[0]
            out[i + 2:i + 6] = struct.pack(">L", symmap.get(t, t)); i += 6
        else:
            i += 2
    return bytes(out)


def check_new_bytes(name, a, new):
    """New bytes of a site may only be: jmp/jsr abs.l into the patch zone, nop(s), or a short bra whose source and target shift equally."""
    i = 0
    while i < len(new):
        w = new[i:i + 2]
        if w in (b"\x4e\xf9", b"\x4e\xb9"):
            t = struct.unpack(">L", new[i + 2:i + 6])[0]
            if not (ZONE_LO <= t < ZONE_HI + 0x40):
                raise SystemExit(f"{name}: site ${a:x} jumps to ${t:x} outside the patch zone: needs translation")
            i += 6
        elif w == b"\x4e\x71":
            i += 2
        elif w[0] == 0x60 and w[1] not in (0, 0xFF):
            tgt = a + i + 2 + (w[1] - 256 if w[1] > 127 else w[1])
            if map_addr(tgt) - map_addr(a + i) != tgt - (a + i):
                raise SystemExit(f"{name}: short branch at ${a:x} crosses a displaced block")
            i += 2
        else:
            raise SystemExit(f"{name}: site ${a:x} new bytes {new.hex()} are not a form tools/nefloppy.py can translate")


def stub_bytes(editor: bool, title_orig: bytes) -> bytes:
    if not editor:
        return b""
    src = f"""        org ${STUB:x}
        dc.b    'NEPO'
        dc.w    0
        dc.w    0
        cmpi.l  #$c0000,$42e.w          ; phystop: below 768 KB = 512 KB machine (the editor needs RAM up to $c0000)
        bhs.s   .go
        lea     orig(pc),a0
        lea     ${map_addr(TITLE_SITE):x}.l,a1
        moveq   #{len(title_orig) // 2 - 1},d0
.c:     move.w  (a0)+,(a1)+
        dbra    d0,.c
        move.l  #'NEPS',${STUB:x}.l
.go:    jmp     ${ENTRY:x}.l
orig:   dc.b    {",".join("$%02x" % x for x in title_orig)}
"""
    return nepatch.asm(STUB, src)


def build_game(names, corrupt=False, remap=True, quiet=False):
    """-> (new TOPPLER.JMP bytes, applied sites, blocks)"""
    disk = Disk(SRC_IMG.read_bytes())
    if hashlib.md5(bytes(disk.b)).hexdigest() != SRC_MD5:
        raise SystemExit(f"{SRC_IMG.name}: md5 differs from the image this tool was written against ({SRC_MD5}); the address map is only valid for that game")
    jmp0 = disk.read(disk.find(b"TOPPLER JMP"))
    if hashlib.md5(jmp0).hexdigest() != JMP_MD5:
        raise SystemExit("TOPPLER.JMP md5 mismatch")
    ts, ds, offs = parse_gemdos(jmp0)
    assert (ts, ds) == (FL_TEXT, FL_DATA) and BASE + 28 + ts + ds == ZONE_LO
    img = bytearray(FILE_END - BASE)
    img[0:28] = jmp0[0:28]
    rel = relocated(jmp0)
    img[28:28 + len(rel)] = rel
    struct.pack_into(">H", img, 0x1A, 0xFFFF)              # the file's own relocator: absolute flag -> skips relocation, jumps
    pp = nepatch.predicted_stage2(hook=False)
    plan = Plan(names, remap)
    plan.sites = [(n, a, translate_new(new, getattr(plan, "symmap", {}))) for n, a, new in plan.sites]
    rep = []
    used = {}                                              # addr -> owner, for overlap detection
    for n, a, new in plan.sites:
        fa = map_addr(a)
        if corrupt and not rep:
            img[fa - BASE] ^= 0x01                         # negative control: a wrong byte in the source game
        check_new_bytes(n, a, new)
        orig_pp = bytes(pp[a:a + len(new)])
        if not site_equivalent(pp, img, a, len(new)):
            raise SystemExit(f"{n}: site ${a:x} -> floppy ${fa:x}: original instructions differ from PP's ({orig_pp.hex()} vs {bytes(img[fa - BASE:fa - BASE + len(new)]).hex()}); nothing written")
        for k in range(len(new)):
            if (fa + k) in used:
                raise SystemExit(f"{n}: site ${fa:x} overlaps {used[fa + k]}")
            used[fa + k] = n
        rep.append((n, a, fa, bytes(img[fa - BASE:fa - BASE + len(new)]), new))
    for n, fa, new in [(n, map_addr(a), new) for n, a, new in plan.sites]:
        img[fa - BASE:fa - BASE + len(new)] = new
    blocks = []
    for n, ad, d in plan.blocks:
        assert ZONE_LO <= ad and ad + len(d) <= ZONE_HI, f"{n}: block ${ad:x}+{len(d)} outside ${ZONE_LO:x}..${ZONE_HI:x}"
        assert not any(img[ad - BASE:ad - BASE + len(d)]), f"{n}: block at ${ad:x} overlaps another"
        img[ad - BASE:ad - BASE + len(d)] = d
        blocks.append((n, ad, len(d)))
    editor = "ed_overlay" in names
    if editor:
        fa = map_addr(TITLE_SITE)
        # the title site's ORIGINAL bytes are what the stub puts back on a 512 KB machine (read before patching: re-derive from the source game)
        orig = bytes(relocated(jmp0)[fa - RB:fa - RB + 10])
        st = stub_bytes(True, orig)
        assert STUB + len(st) <= FILE_END and not any(img[STUB - BASE:FILE_END - BASE])
        img[STUB - BASE:STUB - BASE + len(st)] = st
        struct.pack_into(">L", img, 28 + 0x50, STUB + 8)   # the relocator's final `jmp` (4ef9 at text offset $4e, operand at $50)
    else:
        struct.pack_into(">L", img, 28 + 0x50, ENTRY)
    assert img[28 + 0x4E:28 + 0x50] == b"\x4e\xf9", "jmp operand not where expected"
    return bytes(img), rep, blocks


def build_disk(names, **kw) -> tuple[bytes, list, list]:
    jmp, rep, blocks = build_game(names, **kw)
    disk = Disk(SRC_IMG.read_bytes())
    oj, on = disk.find(b"TOPPLER JMP"), disk.find(b"TOPPLER NEO")
    neo = disk.read(on)
    first = struct.unpack("<H", disk.b[oj + 26:oj + 28])[0]
    disk.rewrite([(oj, jmp, first), (on, neo, NEO_CLUSTER)])
    return bytes(disk.b), rep, blocks


def default_names():
    allp = nepatch.load_patches()
    names = [p.name for p in allp if p.default and p.name != "test_poke"]
    return sorted(names)


# ------------------------------------------------------------------ campaign disk (720 KB, FAT12, deterministic)
def campaign_disk(ovl: bytes = b"\0" * 0x2000, label=b"NEBCAMPAIGN") -> bytes:
    spt, heads, tracks = 9, 2, 80
    nsec = spt * heads * tracks
    b = bytearray(nsec * 512)
    bs = bytearray(512)
    bs[0:3] = b"\xeb\x34\x90"
    bs[3:8] = b"NEBLV "[:5]
    bs[8:11] = b"\x4e\x45\x42"                             # TOS volume serial (3 bytes)
    struct.pack_into("<HBHBHHBHHH", bs, 11, 512, 2, 1, 2, 112, nsec, 0xF9, 3, spt, heads)
    b[0:512] = bs
    nfat, spf, ndir = 2, 3, 112
    fat0 = 512
    dir0 = fat0 + nfat * spf * 512
    data0 = dir0 + ndir * 32
    ncl = 8                                                # 8192 B / 1024 (2 sectors per cluster)
    fat = bytearray(spf * 512)
    fat[0:3] = b"\xf9\xff\xff"
    def sf(n, v):
        o = n * 3 // 2
        x = fat[o] | fat[o + 1] << 8
        x = (x & 0x000F) | (v << 4) if n & 1 else (x & 0xF000) | v
        fat[o], fat[o + 1] = x & 0xFF, x >> 8
    for k in range(ncl):
        sf(2 + k, 3 + k if k < ncl - 1 else 0xFFF)
    for k in range(nfat):
        b[fat0 + k * spf * 512:fat0 + (k + 1) * spf * 512] = fat
    d = bytearray(32); d[0:11] = label.ljust(11); d[11] = 0x08
    e = bytearray(32); e[0:11] = b"NEBLEVELOVL"; e[11] = 0x20
    struct.pack_into("<HH", e, 22, 0x6000, 0x5D72)           # fixed time/date (2026-03-18 12:00)
    struct.pack_into("<HL", e, 26, 2, len(ovl))
    b[dir0:dir0 + 32] = d; b[dir0 + 32:dir0 + 64] = e
    b[data0:data0 + len(ovl)] = ovl
    return bytes(b)


# ------------------------------------------------------------------ CLI
def selftest():
    """Unmapped generators must reproduce the shipped HD .nep blocks byte for byte (proves this tool assembles like gen_ed.py / gen_nep.py / ...)."""
    allp = {p.name: p for p in nepatch.load_patches()}
    bad = 0
    for n, gen in GENS.items():
        got = dict(gen(False)[0])
        want = {a: d for a, d in allp[n].blocks}
        want.update({a: d for a, d in allp[n].sites if a >= ZONE_LO})
        ok = got == want
        print(f"{n:12} unmapped generator == patches/{n}.nep blocks: {'yes' if ok else 'NO'}  ({', '.join('$%x+%d' % (a, len(d)) for a, d in sorted(got.items()))})")
        if not ok:
            bad += 1
            for a in sorted(set(got) | set(want)):
                print("   ", hex(a), len(got.get(a, b"")), len(want.get(a, b"")), got.get(a) == want.get(a))
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify")
    sub.add_parser("selftest")
    b = sub.add_parser("build"); b.add_argument("--only", nargs="*"); b.add_argument("--out", default=str(GAME / "build/floppy/nebulus_game.st")); b.add_argument("--corrupt", action="store_true")
    c = sub.add_parser("campaign"); c.add_argument("out")
    a = ap.parse_args()
    if a.cmd == "selftest":
        sys.exit(selftest())
    if a.cmd == "campaign":
        Path(a.out).write_bytes(campaign_disk()); print("wrote", a.out)
    elif a.cmd in ("verify", "build"):
        names = (a.only if a.cmd == "build" and a.only else default_names())
        img, rep, blocks = build_disk(names, corrupt=getattr(a, "corrupt", False))
        for n, pa, fa, orig, new in rep:
            print(f"  {n:12} PP ${pa:06x} -> floppy ${fa:06x}  {orig.hex()} -> {new.hex()}")
        for n, ad, ln in blocks:
            print(f"  {n:12} block ${ad:06x} {ln} B")
        if a.cmd == "build":
            out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(img)
            print("wrote", out, len(img), "B md5", hashlib.md5(img).hexdigest())


if __name__ == "__main__":
    main()
