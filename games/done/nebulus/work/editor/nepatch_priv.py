#!/usr/bin/env python3
r"""Nebulus patch delivery (Hunter's design adapted to this Gamex START: games/done/hunter/work/notes/loading.md ss2).

Carrier = a patched copy of START.TOS (unpacked, same size as the unpacked original, no relocation change) + the payload file
NEPATCH.BIN in the image root. Details and evidence: work/notes/boot.md.
  stage 0  START text $34c `move.w #$7f,d7` -> `bsr.w stub`; stub = 0x..b in the dead zero run $7c10.. of START's text.
           It reads NEPATCH.BIN (GEMDOS: Fopen/Fread/Fclose, exactly like START reads NEBEXE.FIC) to $B0000; only if the magic
           'NEPA' is there it rewrites START text $3b2 (`jmp $33b00`, 6 bytes) to `jmp $B0008` -- a missing/short/bad file leaves
           START untouched and the game starts unpatched.
  stage 1  core1 ($B0008, runs where START's `jmp $33b00` was, from START's $7fd00 copy, SR $2700, game unpacked, not relocated):
           stores (core2 - $33b1c) in the long the game's own relocator turns into its final `jmp $38624`
           (`$33b6c`: `4ef9 00004b08`), then `jmp $33b00`.
  stage 2  core2 (runs after the game relocated itself; every address is its final RAM address): pass 1 compares the original
           bytes of EVERY site, pass 2 (only if all matched) writes them, marker 'NEPO' (or 'NEPF' on a mismatch), `jmp $38624`.
Commands: verify | list | build | live | boot | taildump | fillcheck   (see --help)
Patch files: patches/*.nep, lines `patch NAME` / `site HEXADDR NEWHEX` / `default yes|no` (original bytes are derived from the
predicted stage-2 RAM image, so they cannot be mistyped, and are checked against a real dump by `verify`).
"""
from __future__ import annotations

import argparse, json, shutil, struct, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent
BENCH = GAME.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools")); sys.path.insert(0, str(HERE))
ORIG = GAME / "originals/NEBULGX"
import os
PATCHES = Path(os.environ["NEP_PATCHES"]) if os.environ.get("NEP_PATCHES") else GAME / "patches"
BUILD = HERE / "build"
DUMP = GAME / "work/dumps/boot/ram_stage2_1mb.bin"
VASM = "vasmm68k_mot"

GAME_BASE = 0x33B00           # NEBEXE.FIC unpacks here (a GEMDOS program image: header + text + data + reloc table)
RELOC_BASE = 0x33B1C          # base the program relocates itself to
JMP_OPERAND = 0x33B6C         # `4ef9 00004b08` in the relocator: becomes `jmp $38624` after relocation
ENTRY = 0x38624               # lea $800,a7 / jmp $3db62 : the game proper
PB = 0xB0000                  # payload RAM address
PB_MAX = 0xC000               # the payload may use $B0000..$BBFFF; the campaign store (NEBLEVEL.OVL) is loaded at OB = $BC000
MARKER = PB + 0x20
NSITES = PB + 0x24
TABLE = PB + 0x100
TABLE_END = PB + 0x6000           # sites (verified, orig+new)
BLKTAB = PB + 0x6000              # blocks (unverified copies into the dead zone / zero gap): {addr.l len.w data} ..., 0.l
BLK_END = PB + 0xB000
BLK_LO, BLK_HI = 0x75728, 0x77EC0
STUB_OFF = 0x7C10             # START text offset of the loader stub (zero run $7c06..$7dc5)
BSR_OFF = 0x34C               # START text: 3e3c007f
JMP_OFF = 0x3B2               # START text: 4ef9 00033b00
DEAD_LO, DEAD_HI = 0x76B10, 0x77EC0   # zero at stage 2 (1 MB and 4 MB), inside game RAM so Gamex F9 saves/restores it
FILEN = "NEPATCH.BIN"
OVLN = "NEBLEVEL.OVL"
OB = 0xBC000                  # campaign store: NEBLEVEL.OVL is read here by the loader stub (outside game RAM; F9 overwrites it, the hooks check the magic)
OVS = OB
OVSZ = 0x2000                 # fixed size of NEBLEVEL.OVL



# ---------------------------------------------------------------- game image
def lz(src: bytes) -> bytes:
    out = bytearray(); i = 0
    while True:
        c = src[i]; i += 1
        if c == 0:
            break
        if c < 0x80:
            out += src[i:i + c]; i += c; continue
        cnt = c & 0x3F
        if c & 0x40:
            cnt += 3; off = (src[i] << 8) | src[i + 1]; i += 2
        else:
            cnt += 2; off = src[i]; i += 1
        for _ in range(cnt + 1):
            out.append(out[-off])
    return bytes(out)


def unpacked_game() -> bytes:
    fic = (ORIG / "NEBEXE.FIC").read_bytes()
    assert fic[:2] == b"C3"
    g = lz(fic[0x20:])
    assert len(g) == struct.unpack(">L", fic[6:10])[0], "unpacked size mismatch"
    return g


def reloc_offsets(g: bytes) -> list[int]:
    tl, dl, sl = (struct.unpack(">L", g[i:i + 4])[0] for i in (2, 6, 14))
    p = 28 + tl + dl + sl
    first = struct.unpack(">L", g[p:p + 4])[0]
    if first == 0:
        return []
    p += 4; offs = [first]; cur = first
    while g[p] != 0:
        if g[p] == 1:
            cur += 254
        else:
            cur += g[p]; offs.append(cur)
        p += 1
    return offs


def predicted_stage2(hook: bool = True) -> bytearray:
    """RAM $0..$100000 as the game sees it at `jmp $38624`: unpacked, relocated, Gamex `jmp $200` keyboard hook installed."""
    g = unpacked_game()
    ram = bytearray(0x100000)
    ram[GAME_BASE:GAME_BASE + len(g)] = g
    tl, dl = struct.unpack(">L", g[2:6])[0], struct.unpack(">L", g[6:10])[0]
    for o in reloc_offsets(g):
        a = RELOC_BASE + o
        ram[a:a + 4] = struct.pack(">L", (struct.unpack(">L", ram[a:a + 4])[0] + RELOC_BASE) & 0xFFFFFFFF)
    if hook:
        ram[0x3850C:0x38512] = bytes.fromhex("4ef900000200")
    return ram


# ---------------------------------------------------------------- patch files
class Patch:
    def __init__(self, name):
        self.name = name; self.sites: list[tuple[int, bytes]] = []; self.blocks: list[tuple[int, bytes]] = []; self.default = False


def load_patches() -> list[Patch]:
    out = []; cur = None
    for f in sorted(PATCHES.glob("*.nep")):
        for ln in f.read_text().splitlines():
            ln = ln.split("#")[0].strip()
            if not ln:
                continue
            w = ln.split()
            if w[0] == "patch":
                cur = Patch(w[1]); out.append(cur)
            elif w[0] == "default":
                cur.default = w[1] == "yes"
            elif w[0] == "site":
                cur.sites.append((int(w[1], 16), bytes.fromhex("".join(w[2:]))))
            elif w[0] == "block":
                cur.blocks.append((int(w[1], 16), bytes.fromhex("".join(w[2:]))))
            else:
                raise SystemExit(f"{f}: bad line {ln!r}")
    return out


def derive_sites(patches: list[Patch], ram: bytes) -> list[tuple[int, bytes, bytes]]:
    """[(addr, orig, new)], checked: inside the relocated game image, no overlap between sites, not on the relocator's own jmp."""
    g = unpacked_game()
    sites = []
    for p in patches:
        for a, new in p.sites:
            in_game = GAME_BASE <= a and a + len(new) <= GAME_BASE + len(g)
            in_gap = DEAD_LO <= a and a + len(new) <= DEAD_HI          # blob area: verified to be zero at stage 2
            if not (in_game or in_gap):
                raise SystemExit(f"{p.name}: site ${a:x} outside the game image and the dead gap ${DEAD_LO:x}..${DEAD_HI:x}")
            sites.append((a, bytes(ram[a:a + len(new)]), new))
    sites.sort()
    for (a, o, n), (b, _, _) in zip(sites, sites[1:]):
        if a + len(o) > b:
            raise SystemExit(f"sites overlap at ${a:x}/${b:x}")
    return sites


# ---------------------------------------------------------------- assembly
def asm(org: int, src: str) -> bytes:
    with tempfile.TemporaryDirectory() as d:
        s = Path(d) / "a.s"; o = Path(d) / "a.bin"; s.write_text(f"\torg ${org:x}\n{src}\n")
        r = subprocess.run([VASM, "-Fbin", "-m68000", "-no-opt", "-o", str(o), str(s)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"vasm failed:\n{src}\n{r.stdout}\n{r.stderr}")
        return o.read_bytes()


# Core: table entries {addr.l, len.w (even), orig[len], new[len]}, end addr.l = 0.
CORE = f"""
MARKER  equ ${MARKER:x}
NSITES  equ ${NSITES:x}
TABLE   equ ${TABLE:x}
\tdc.b 'NEPA'
\tdc.l 0
core1:
\tmove.l #core2-${RELOC_BASE:x},${JMP_OPERAND:x}.l
\tjmp ${GAME_BASE:x}.l
\tcnop 0,32
\tdc.l 'NEPF'
\tdc.w 0
\tdc.w 0
\tcnop 0,16
core2:
\tmovem.l d0-d7/a0-a6,-(a7)
\tmove.l #'NEPF',MARKER.l
\tlea TABLE.l,a0
\tmove.l a0,a3
p1:
\tmove.l (a0)+,d0
\tbeq.s p1ok
\tmove.l d0,a1
\tmoveq #0,d1
\tmove.w (a0)+,d1           ; len (even)
\tmove.l a0,a2
\tmove.w d1,d2
\tsubq.w #1,d2
p1c:
\tcmpm.b (a2)+,(a1)+
\tbne.s fin
\tdbra d2,p1c
\tadda.l d1,a0
\tadda.l d1,a0
\tbra.s p1
p1ok:
\tmove.l a3,a0
\tmoveq #0,d3
p2:
\tmove.l (a0)+,d0
\tbeq.s p2ok
\tmove.l d0,a1
\tmoveq #0,d1
\tmove.w (a0)+,d1
\tlea 0(a0,d1.l),a2          ; new bytes
\tmove.w d1,d2
\tsubq.w #1,d2
p2c:
\tmove.b (a2)+,(a1)+
\tdbra d2,p2c
\tadda.l d1,a0
\tadda.l d1,a0
\taddq.w #1,d3
\tbra.s p2
p2ok:
\tmove.w d3,NSITES.l
\tmove.l #'NEPO',MARKER.l
\tlea ${BLKTAB:x}.l,a0
blk:
\tmove.l (a0)+,d0
\tbeq.s fin
\tmove.l d0,a1
\tmoveq #0,d1
\tmove.w (a0)+,d1
\tmove.w d1,d2
\tlsr.w #1,d2
\tsubq.w #1,d2
blkc:
\tmove.w (a0)+,(a1)+
\tdbra d2,blkc
\tbra.s blk
fin:
\tmovem.l (a7)+,d0-d7/a0-a6
\tjmp ${ENTRY:x}.l
"""


def stub_code(patch_start_off: int = STUB_OFF) -> bytes:
    return asm(patch_start_off, f"""
\tmovem.l d0-d7/a0-a6,-(a7)
\tclr.w -(a7)
\tpea fname(pc)
\tmove.w #$3d,-(a7)
\ttrap #1
\taddq.l #8,a7
\ttst.l d0
\tbmi.w done
\tmove.w d0,d7
\tpea ${PB:x}.l
\tpea ${PB_MAX:x}.l
\tmove.w d7,-(a7)
\tmove.w #$3f,-(a7)
\ttrap #1
\tlea 12(a7),a7
\tmove.w d7,-(a7)
\tmove.w #$3e,-(a7)
\ttrap #1
\taddq.l #4,a7
\tcmpi.l #'NEPA',${PB:x}.l
\tbne.w done
\tlea ${OB:x}.l,a0
\tmove.w #{OVSZ // 4 - 1},d0
zl:
\tclr.l (a0)+
\tdbra d0,zl
\tclr.w -(a7)
\tpea fname2(pc)
\tmove.w #$3d,-(a7)
\ttrap #1
\taddq.l #8,a7
\ttst.l d0
\tbmi.s noovl
\tmove.w d0,d7
\tpea ${OB:x}.l
\tpea {OVSZ}.l
\tmove.w d7,-(a7)
\tmove.w #$3f,-(a7)
\ttrap #1
\tlea 12(a7),a7
\tmove.w d7,-(a7)
\tmove.w #$3e,-(a7)
\ttrap #1
\taddq.l #4,a7
noovl:
\tlea ${JMP_OFF + 2:x}(pc),a0     ; START text $3b4 = operand of `jmp $33b00`
\tmove.l #${PB + 8:x},(a0)
done:
\tmovem.l (a7)+,d0-d7/a0-a6
\tmove.w #$7f,d7
\trts
fname:
\tdc.b '{FILEN}',0
fname2:
\tdc.b '{OVLN}',0
\teven
""")


def build_carrier() -> bytes:
    sp = (BENCH / "tools").as_posix()
    sys.path.insert(0, sp)
    import pp_depack
    f = bytearray(pp_depack.depack((ORIG / "START.TOS").read_bytes()))
    tl = struct.unpack(">L", f[2:6])[0]
    T = 28
    assert f[T + BSR_OFF:T + BSR_OFF + 4] == bytes.fromhex("3e3c007f"), "START layout changed"
    assert f[T + JMP_OFF:T + JMP_OFF + 6] == bytes.fromhex("4ef900033b00")
    stub = stub_code()
    z = f[T + STUB_OFF:T + STUB_OFF + len(stub)]
    assert not any(z) and STUB_OFF + len(stub) <= 0x7DC6, f"stub zone not free / too long ({len(stub)} bytes)"
    f[T + STUB_OFF:T + STUB_OFF + len(stub)] = stub
    disp = STUB_OFF - (BSR_OFF + 2)
    f[T + BSR_OFF:T + BSR_OFF + 4] = bytes([0x61, 0x00]) + struct.pack(">h", disp)
    return bytes(f)


def build_payload(sites, corrupt=False, fill=False, blocks=()) -> bytes:
    code = asm(PB, CORE)
    assert code[8:10] == bytes.fromhex('23fc') and code[MARKER - PB:MARKER - PB + 4] == b'NEPF', 'core layout moved'
    img = bytearray(max(len(code), 0x100))
    img[:len(code)] = code
    tab = bytearray()
    for a, o, n in sites:
        if corrupt and not tab:
            o = bytes([o[0] ^ 0xFF]) + o[1:]
        ln = len(o) + (len(o) & 1)
        tab += struct.pack(">LH", a, ln) + o.ljust(ln, b"\0") + n.ljust(ln, b"\0")
        # padding byte of an odd-length site: orig and new both 0 -> would clobber the byte after the site; forbid odd sites
        if len(o) & 1:
            raise SystemExit(f"site ${a:x} has odd length {len(o)}: use an even number of bytes")
    tab += b"\0\0\0\0"
    if len(tab) > TABLE_END - TABLE:
        raise SystemExit(f"site table {len(tab)} B > {TABLE_END - TABLE} B")
    btab = bytearray()
    for a, d in blocks:
        if not (BLK_LO <= a and a + len(d) <= BLK_HI) or (a & 1) or (len(d) & 1):
            raise SystemExit(f"block ${a:x}+{len(d)} outside ${BLK_LO:x}..${BLK_HI:x} or odd")
        btab += struct.pack(">LH", a, len(d)) + d
    btab += b"\0\0\0\0"
    if len(btab) > BLK_END - BLKTAB:
        raise SystemExit(f"block table {len(btab)} B too big")
    out = bytearray(TABLE - PB) ; out[:len(img)] = img[:len(img)]
    out += tab
    out = bytearray(out.ljust(BLKTAB - PB, b"\0"))
    out += btab
    if fill:
        n = PB_MAX
        out = bytearray(out.ljust(n, b"\0"))
        for i in range(len(out)):
            if i >= len(out) - 0 or out[i] == 0 and i >= (TABLE - PB) + len(tab):
                out[i] = fill_byte(PB + i)
    return bytes(out)


def fill_byte(addr: int) -> int:
    return ((addr * 7 + (addr >> 8) * 13 + (addr >> 16) * 29) & 0xFF) | 1


# ---------------------------------------------------------------- commands
def chosen(names: list[str] | None, patches: list[Patch]) -> list[Patch]:
    if names is None:
        return [p for p in patches if p.default]
    by = {p.name: p for p in patches}
    for n in names:
        if n not in by:
            raise SystemExit(f"unknown patch {n}; have {sorted(by)}")
    return [by[n] for n in names]


def cmd_verify(a):
    ram = predicted_stage2()
    dump = Path(a.dump)
    if not dump.exists():
        print(f"no dump {dump}: run `taildump` first (predicted image only)"); return 1
    real = dump.read_bytes()
    g = unpacked_game()
    lo, hi = GAME_BASE, GAME_BASE + len(g)
    bad = [i for i in range(lo, hi) if ram[i] != real[i]]
    print(f"predicted stage-2 image vs {dump.name}: {hi - lo} game bytes compared, {len(bad)} differ")
    if bad:
        print("first differences:", ", ".join(f"${i:x}" for i in bad[:20]))
    sites = derive_sites(chosen(a.only, load_patches()), ram)
    for ad, o, n in sites:
        print(f"site ${ad:06x} orig {o.hex()} new {n.hex()}  dump-orig {'OK' if bytes(real[ad:ad+len(o)]) == o else 'MISMATCH'}")
    return 1 if bad else 0


def cmd_list(a):
    ram = predicted_stage2()
    for p in load_patches():
        print(f"{p.name} default={'yes' if p.default else 'no'}")
        for ad, new in p.sites:
            print(f"   ${ad:06x} orig {bytes(ram[ad:ad+len(new)]).hex()} new {new.hex()}")


def cmd_build(a):
    ram = predicted_stage2()
    sites = derive_sites(chosen(a.only, load_patches()), ram)
    out = Path(a.out)
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(ORIG, out)
    (out / "START.TOS").write_bytes(build_carrier())
    blocks = sorted((ba, bd) for p in chosen(a.only, load_patches()) for ba, bd in p.blocks)
    for (ba, bd), (bb, be) in zip(blocks, blocks[1:]):
        if ba + len(bd) > bb:
            raise SystemExit(f"blocks overlap at ${ba:x}/${bb:x}")
    (out / FILEN).write_bytes(build_payload(sites, a.corrupt, a.fill, blocks))
    ovl = Path(a.ovl) if a.ovl else None
    (out / OVLN).write_bytes(ovl.read_bytes() if ovl else bytes(OVSZ))
    man = {"payload": hex(PB), "sites": [{"addr": ad, "orig": o.hex(), "new": n.hex()} for ad, o, n in sites],
           "marker": hex(MARKER)}
    (out.parent / (out.name + ".json")).write_text(json.dumps(man, indent=1))
    print(f"built {out}: START.TOS {(out/'START.TOS').stat().st_size} B, {FILEN} {(out/FILEN).stat().st_size} B, {len(sites)} sites")


def cmd_live(a):
    ram = predicted_stage2()
    sites = derive_sites(chosen(a.only, load_patches()), ram)
    for ad, o, n in sites:
        print("w $%x " % ad + " ".join(f"${b:02x}" for b in n))


def cmd_boot(a):
    cmd = [sys.executable, str(GAME / "work/boot/boot4.py"), a.out, "--machine", a.machine, "--mem", str(a.mem), "--tos", a.tos,
           "--game", str(a.game), "--t0", str(a.t0), "--dump", str(a.dump_kb), "--settle", str(a.settle), "--stage2",
           "--work", f"scratch/np_{a.machine}_{a.mem}"]
    return subprocess.call(cmd)


def cmd_taildump(a):
    sys.argv = [""]
    return subprocess.call([sys.executable, str(GAME / "work/boot/boot4.py"), str(DUMP.parent / "tail"), "--stage2", "--dump", "1024",
                            "--settle", "0.5", "--work", "scratch/np_tail", "--game", str(ORIG)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify"); v.add_argument("--dump", default=str(DUMP)); v.add_argument("--only", nargs="*")
    sub.add_parser("list")
    b = sub.add_parser("build"); b.add_argument("--out", default=str(BUILD)); b.add_argument("--only", nargs="*")
    b.add_argument("--corrupt", action="store_true"); b.add_argument("--fill", action="store_true"); b.add_argument("--ovl")
    l = sub.add_parser("live"); l.add_argument("--only", nargs="*")
    t = sub.add_parser("boot"); t.add_argument("out"); t.add_argument("--machine", default="ste"); t.add_argument("--mem", type=int, default=1024)
    t.add_argument("--tos", default="1.62"); t.add_argument("--game", default=str(BUILD)); t.add_argument("--t0", type=float, default=2.0)
    t.add_argument("--dump-kb", type=int, default=1024); t.add_argument("--settle", type=float, default=6.0)
    sub.add_parser("taildump")
    a = ap.parse_args()
    sys.exit({"verify": cmd_verify, "list": cmd_list, "build": cmd_build, "live": cmd_live, "boot": cmd_boot, "taildump": cmd_taildump}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
