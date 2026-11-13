#!/usr/bin/env python3
"""Test scaffolding for the land-score patches (pop_land_*). Not a game patch.

- parse_patch / assemble: the Midwinter 2 patch-file format (one site, `org` segments,
  preamble `equ` lines), assembled segment by segment with vasm.
- model_181d6 / model_18244: Python models of the ORIGINAL routines, written from the
  listing in work/notes/landscore.md (checked against the real routines by exhaust.py).
- Run: a Hatari session on a snapshot with deterministic "at turn T" actions.
"""
from __future__ import annotations

import re
import struct
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GAME = HERE.parent.parent.parent
BENCH = GAME.parent.parent.parent
sys.path.insert(0, str(BENCH / "tools"))
sys.path.insert(0, str(GAME / "tools"))
from populous import Populous  # noqa: E402

PATCHES = GAME / "patches"
SNAP = GAME / "work" / "snapshots"
MAP_BLK, MAP_BK2, OFFTAB = 0x36EB6, 0x3C560, 0x22B8C
V_CNT, V_FLAT, TURN = 0x3B040, 0x37EF4, 0x3C506
LOOP_PC = 0xB800          # `jsr $12fc2`, the instruction before `jsr $db8a` in the main loop: once per pass, no
                          # patched routine active. (Not $b806 itself: a write to the operand of the instruction
                          # at PC comes after the 68000 prefetch and is not executed.)

HDR_RE = re.compile(r"^;\s*(name|default|site|orig|phase|data|note|version)\s*:\s*(.*)$")
ORG_RE = re.compile(r"^\s+org\s+\$([0-9a-fA-F]+)\s*(?:;.*)?$")


def assemble(org: int, lines: list[str], equ: str = "") -> bytes:
    src = equ + f"\n\torg\t${org:x}\n" + "\n".join(lines) + "\n"
    with tempfile.TemporaryDirectory() as td:
        s = Path(td) / "seg.s"
        s.write_text(src)
        out = Path(td) / "seg.bin"
        r = subprocess.run(["vasmm68k_mot", "-Fbin", "-m68000", "-quiet", "-o", str(out), str(s)],
                           capture_output=True, text=True)
        if r.returncode != 0 or r.stderr.strip():
            raise SystemExit(f"vasm failed for org ${org:x}:\n{r.stderr}\n{r.stdout}")
        return out.read_bytes()


def parse_source(text: str) -> dict:
    """{'hdr': {...}, 'segs': {org: bytes}} for a patch file or a multi-org test stub."""
    hdr: dict = {"data": []}
    pre: list[str] = []
    segs: list[tuple[int, list[str]]] = []
    cur = None
    for line in text.splitlines():
        if cur is None and re.match(r"^\s*\w+\s+equ\s+", line):
            pre.append(line)
            continue
        m = HDR_RE.match(line)
        if m and cur is None:
            k, v = m.group(1), m.group(2).strip()
            if k == "data":
                a, ln = v.split()[:2]
                hdr["data"].append((int(a.lstrip("$"), 16), int(ln, 0)))
            elif k == "site":
                hdr[k] = int(v.split()[0].lstrip("$"), 16)
            elif k == "orig":
                hdr[k] = bytes.fromhex(v.split(";")[0].replace(" ", ""))
            else:
                hdr[k] = v
            continue
        m = ORG_RE.match(line)
        if m:
            cur = (int(m.group(1), 16), [])
            segs.append(cur)
        elif cur is not None:
            cur[1].append(line)
    equ = "\n".join(pre)
    return {"hdr": hdr, "segs": {org: assemble(org, lines, equ) for org, lines in segs}}


def load_patch(name: str, ram: bytes | None = None) -> dict:
    """A patches/<name>.s file: site bytes (nop-padded to len(orig)) + blob segments. Verifies orig against `ram`."""
    p = parse_source((PATCHES / f"{name}.s").read_text())
    site, orig = p["hdr"]["site"], p["hdr"]["orig"]
    new = p["segs"].pop(site)
    if len(new) > len(orig):
        raise SystemExit(f"{name}: site code {len(new)} B > orig {len(orig)} B")
    new += b"\x4e\x71" * ((len(orig) - len(new)) // 2)
    if ram is not None and ram[site:site + len(orig)] != orig:
        raise SystemExit(f"{name}: orig mismatch at ${site:x}: ram {ram[site:site+len(orig)].hex()} != {orig.hex()}")
    return {"name": name, "site": site, "orig": orig, "new": new, "blobs": p["segs"], "data": p["hdr"]["data"]}


# ---- models of the original routines ------------------------------------------
def s16(v):
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def s8(v):
    v &= 0xFF
    return v - 0x100 if v & 0x80 else v


def model_181d6(ram, cell: int, off: int) -> int:
    """$181d6(cell, off): 0 ok, 1 off the map, 2 rock, 3 water. Words in, d0.l out."""
    cell &= 0xFFFF
    off &= 0xFFFF
    if off == 0:
        return 0
    d4 = s16(cell + off)
    if d4 < 0 or d4 >= 0x1000:
        return 1
    d3 = off & 0x3F
    if s16(d3) > 3:
        d3 |= 0xFFC0
    d3 = s16(d3 + (cell & 0x3F))
    if d3 < 0 or d3 > 0x3F:
        return 1
    t = ram[MAP_BLK + d4]
    return 3 if t == 0 else 2 if t == 0x2F else 0


def model_18244(ram, owner: int, cell: int) -> tuple[int, int, int]:
    """$18244(owner, cell) -> (d0.w, $3b040.w, $37ef4.w)."""
    d6 = (owner + 0x1F) & 0xFF
    cell &= 0xFFFF
    d4 = 0
    cnt = 0
    flat = 0
    tab = struct.unpack_from(">17h", ram, OFFTAB)
    for d5 in range(17):
        off = tab[d5]
        r = model_181d6(ram, cell, off)
        if r:
            if r == 2:
                d4 = s16(d4 - 15)
            continue
        idx = s16(cell + off)
        blk = ram[MAP_BLK + idx]
        good = True
        if blk == d6:
            pass
        elif blk == 0x0F:
            flat = 1
        else:
            good = False
            if d5 == 0:
                return 0, cnt, flat
        if good:
            if d4 == 0:
                d4 = 0x32
            d4 = s16(d4 + 15)
        d1 = s8(ram[MAP_BK2 + idx])
        if d5 < 9 and ram[MAP_BK2 + s16(cell)] == 0x2A and 0x29 <= d1 <= 0x2C:
            cnt += 1
            continue
        if d5 != 0 and 0x20 < d1 <= 0x2C:
            return 0, cnt, flat
    if d4 < 0x23:
        d4 = 0
    if d4 == 0x131:
        d4 = 0xBEA
    return d4 & 0xFFFF, cnt, flat


def model_path(ram, owner: int, cell: int) -> tuple:
    """Which code path of patches/pop_land_score.s an (owner 0/1, cell 0..4095) input takes, for coverage:
    (region, castle, exit, k, kind) with region 'in' (unrolled) / 'edge'; exit 'A' (cell itself not good),
    'B' (building at offset k; kind = 'good' or 'other' tile), 'full' (kind = 'zero', 'score' or 'bea')."""
    x, y = cell & 63, cell >> 6
    region = "in" if 2 <= x <= 61 and 2 <= y <= 61 else "edge"
    castle = ram[MAP_BK2 + cell] == 0x2A
    d6 = owner + 0x1F
    tab = struct.unpack_from(">17h", ram, OFFTAB)
    for k in range(17):
        off = tab[k]
        if model_181d6(ram, cell, off):
            continue
        blk = ram[MAP_BLK + cell + off]
        good = blk in (d6, 0x0F)
        if not good and k == 0:
            return (region, castle, "A", 0, "")
        d1 = s8(ram[MAP_BK2 + cell + off])
        if k < 9 and castle and 0x29 <= d1 <= 0x2C:
            continue
        if k and 0x20 < d1 <= 0x2C:
            return (region, castle, "B", k, "good" if good else "other")
    r = model_18244(ram, owner, cell)[0]
    return (region, castle, "full", 17, "zero" if r == 0 else "bea" if r == 0xBEA else "score")


def all_paths() -> set:
    """Every exit of the two unrolled chains (interior; edge without a castle centre), and the exits of the
    loop that serves a castle centre near an edge (one body for all k, so one k per exit kind is asked)."""
    p = set()
    for region, castle in (("in", False), ("in", True), ("edge", False)):
        p.add((region, castle, "A", 0, ""))
        for k in range(1, 17):
            for kind in ("good", "other"):
                p.add((region, castle, "B", k, kind))
        for kind in ("zero", "score", "bea"):
            if region == "in" or kind != "bea":          # 17 good cells are impossible within 2 of an edge
                p.add((region, castle, "full", 17, kind))
    p |= {("edge", True, "A", 0, ""), ("edge", True, "full", 17, "zero"), ("edge", True, "full", 17, "score"),
          ("edge", True, "B", 1, "good"), ("edge", True, "B", 1, "other")}
    return p


# ---- Hatari session -------------------------------------------------------------
class Run(Populous):
    """Snapshot run with actions at exact game turns (breakpoint at the main loop's `jsr $db8a`)."""

    def __init__(self, snap: str, **kw):
        super().__init__(snapshot=SNAP / f"{snap}.sav", **kw)
        self._n = 0
        time.sleep(1.5)

    def at_turn(self, turn: int, cmds: list[str], pc: int = LOOP_PC) -> None:
        """Run debugger commands the first time `pc` executes with the turn word == turn."""
        self._n += 1
        f = self.R / f"a{self._n}.txt"
        for c in cmds:
            if len(c) > 240:
                raise ValueError("debugger command too long: " + c[:60])
        f.write_text("\n".join(cmds) + "\n")
        self.cmd(f"hatari-debug b pc = ${pc:x} && (${TURN:x}).w = {turn} :trace :once :file {f}")
        time.sleep(0.3)

    def wait_file(self, path: Path, timeout: float = 600, size: int = 1) -> None:
        t = time.time()
        while not (path.exists() and path.stat().st_size >= size):
            if time.time() - t > timeout:
                raise TimeoutError(f"{path} never appeared; log tail:\n{self._logtext()[-800:]}")
            time.sleep(0.25)
        time.sleep(0.4)

    def load_cmds(self, segs: dict[int, bytes], tag: str) -> list[str]:
        """Debugger commands that load {addr: bytes} (loadbin for big segments, `w` for small ones)."""
        cmds = []
        for i, (a, b) in enumerate(sorted(segs.items())):
            if len(b) <= 60:
                cmds.append(f"w ${a:x} " + " ".join(f"${x:02x}" for x in b))
            else:
                p = self.R / f"{tag}{i}.bin"
                p.write_bytes(b)
                cmds.append(f"loadbin {p} ${a:x}")
        return cmds

    def patch_cmds(self, patches: list[dict]) -> list[str]:
        """Blobs first, then the site bytes (each site is written by one `w`, atomically at the breakpoint)."""
        cmds = []
        for p in patches:
            cmds += self.load_cmds(p["blobs"], p["name"][-6:])
        for p in patches:
            cmds.append(f"w ${p['site']:x} " + " ".join(f"${x:02x}" for x in p["new"]))
        return cmds

    def fast(self, on: bool = True) -> None:
        self.cmd(f"hatari-option --fast-forward {'on' if on else 'off'}")
        time.sleep(0.5)
