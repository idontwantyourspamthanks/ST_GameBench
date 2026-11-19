#!/usr/bin/env python3
"""Prototype build: patches/ed_editor.s + the lift command of work/lifts/ed_lift.s  ->  a private game directory (default /tmp/lift_game) for Hatari tests.
Writes NOTHING in patches/, work/editor/ or tools/ (everything under /tmp).  The edits below are exactly the ones listed in the header of ed_lift.s;
this script applies them to a COPY of the source with assertions (so it fails loudly when the editor source moved on) and assembles four segments
(CODE1, DATA, CODE2 and the new block at $77a40).
usage: build_lift_editor.py [OUTDIR]"""
import re, subprocess, sys, tempfile, shutil
from pathlib import Path
G = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/lift_game")
NEWB = 0x77A40
src = (G / "patches/ed_editor.s").read_text()
lift = (G / "work/lifts/ed_lift.s").read_text()
body = lift.split("prop_begin:\n", 1)[1].split("; two tiles", 1)[0]          # colbase .. m_lift (code, strings, menu)

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (old, src.count(old))
    src = src.replace(old, new)

rep("vShow   equ     170\n", "vShow   equ     170\nvLift   equ     172\n")
rep("move_map:\n        bsr.w   draw_cursor\n", "move_map:\n        bsr.w   draw_cursor\n        tst.w   vLift(a5)\n        beq.s   .lh\n        moveq   #0,d1\n.lh:\n")
rep(".nr:    bsr.w   draw_cursor\n        move.w  #2,vRedraw(a5)\n        clr.l   vMsg(a5)\n        rts\n",
    ".nr:    bsr.w   draw_cursor\n        move.w  #2,vRedraw(a5)\n        bsr.w   lift_msg\n        rts\n")
rep("        ; map: open the cell menu\n", "        ; map: open the cell menu\n        tst.w   vLift(a5)\n        bne.w   lift_set\n")
rep("        bne.s   .r\n        bra.w   c_leaveed\n", "        bne.s   .r\n        tst.w   vLift(a5)\n        bne.w   lift_cancel\n        bra.w   c_leaveed\n")
rep("        moveq   #1,d3\n        tst.b   d1\n        beq.s   .r\n        moveq   #8,d3\n", "        moveq   #1,d3\n        tst.b   d1\n        beq.w   lift_tile\n        moveq   #8,d3\n")
rep("a_eop-acts\n", "a_eop-acts,a_lift-acts\n")
rep("        moveq   #16,d6\n.t:", "        moveq   #18,d6\n.t:")
rep("        dc.b    $00,$24,$3c,$7e,$5a,$7e,$24,$00,6,0\n",
    "        dc.b    $00,$24,$3c,$7e,$5a,$7e,$24,$00,6,0\n        dc.b    $18,$3c,$7e,$18,$18,$18,$18,$00,7,0\n        dc.b    $18,$3c,$7e,$00,$7e,$00,$7e,$00,7,0\n")
rep("n15-names\n", "n15-names,n16-names,n17-names,n18-names\n")
rep("n6:     dc.b    'Pale block',0\n", "n6:     dc.b    'Lift start',0\n")
rep("n15:    dc.b    'Eye l/r fast',0\n", "n15:    dc.b    'Eye l/r fast',0\nn16:    dc.b    0\nn17:    dc.b    'Lift end',0\nn18:    dc.b    'Lift stop',0\n")
rep("menus:  dc.w    m_root-menus,m_enemy-menus,m_tower-menus\n", "menus:  dc.w    m_root-menus,m_enemy-menus,m_tower-menus,m_lift-menus\n")
rep("        dc.b    0,$85,'Pale block',0\n", "        dc.b    2,3,'Lift >',0\n")
src += f"\n; ------------------------------------------------------------------ lift command (work/lifts/ed_lift.s)\n        org     ${NEWB:x}\n{body}\n        even\n"

eq = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"^(\w+)\s+equ\s+\$([0-9a-f]+)", src, re.M)}
txt2 = re.sub(r"\b(bra|bsr|b(?:eq|ne|cc|cs|hs|lo|hi|ls|mi|pl|ge|lt|gt|le|vc|vs))\.s\b", r"\1", src)
with tempfile.TemporaryDirectory() as d:
    s = Path(d) / "e.s"; s.write_text(txt2); o = Path(d) / "e.srec"; l = Path(d) / "e.lst"
    r = subprocess.run(["vasmm68k_mot", "-Fsrec", "-m68000", "-L", str(l), "-o", str(o), str(s)], capture_output=True, text=True)
    if r.returncode:
        print(r.stdout + r.stderr); sys.exit(1)
    mem = {}
    for ln in o.read_text().splitlines():
        if ln.startswith("S3"):
            n = int(ln[2:4], 16); a = int(ln[4:12], 16); data = bytes.fromhex(ln[12:12 + (n - 5) * 2])
            for i, b in enumerate(data):
                assert a + i not in mem, f"overlap at ${a+i:x}"
                mem[a + i] = b
    lst = l.read_text()
segs = []
for a in sorted(mem):
    if segs and segs[-1][0] + len(segs[-1][1]) == a: segs[-1][1].append(mem[a])
    else: segs.append((a, bytearray([mem[a]])))
sym = {m.group(1): int(m.group(2), 16) for m in re.finditer(r"^(\w+)\s+A:([0-9A-Fa-f]+)", lst, re.M)}
assert [a for a, _ in segs] == [eq["CODE1"], eq["DATA"], eq["CODE2"], NEWB], [hex(a) for a, _ in segs]
(c1, d1), (c2, d2), (c3, d3), (c4, d4) = segs
assert c1 + len(d1) <= 0x76C00 and c2 + len(d2) <= c3 and c3 + len(d3) <= 0x77A00 and c4 + len(d4) <= eq["RS"]
print(f"code1 {len(d1)} B ${c1:x}..${c1+len(d1):x}; tables {len(d2)} ${c2:x}..${c2+len(d2):x}; code2 {len(d3)} ${c3:x}..${c3+len(d3):x}; NEW block {len(d4)} B ${c4:x}..${c4+len(d4):x}")
H = c1
a8 = lambda x: f"{x:08x}"
PD = Path("/tmp/lift_patches"); shutil.rmtree(PD, ignore_errors=True); PD.mkdir()
shutil.copy(G / "patches/nt_trainers.nep", PD)
(PD / "ed_overlay.nep").write_text(f"""patch ed_overlay
default yes
site 377a2 4ef9{a8(H)}
site 37a90 4eb9{a8(H+6)}4e71
site 3d6c4 4eb9{a8(H+12)}4e714e71
site 3adb4 4eb9{a8(H+18)}
site 3d110 4eb9{a8(H+24)}
site 3e352 4ef9{a8(H+30)}
site 3dfd6 4eb9{a8(H+36)}
site 3851a 4ef9{a8(sym["ed_key"])}
site 3d662 4ef9{a8(sym["ed_opt"])}4e71
block {c1:x} {bytes(d1).hex()}
block {c2:x} {bytes(d2).hex()}
block {c3:x} {bytes(d3).hex()}
block {c4:x} {bytes(d4).hex()}
""")
# the private nepatch copy reads /tmp/lift_patches
np_src = (G / "work/editor/nepatch_priv.py").read_text().replace('PATCHES = GAME / "patches"', 'PATCHES = Path("/tmp/lift_patches")')
(G / "work/lifts/nepatch_lift.py").write_text(np_src)
r = subprocess.run([sys.executable, str(G / "work/lifts/nepatch_lift.py"), "build", "--out", str(OUT), "--only", "nt_trainers", "ed_overlay"], capture_output=True, text=True, cwd=G)
print(r.stdout[-800:], r.stderr[-800:])
