"""Emit the `dc.b` glyph table of patches/mr_credit.s from the game's OWN message font (8x8, 16 B per glyph: 8 x (edge byte, body byte); index = char - $20).
The picture leaves only 6 black rows under its frame (194-199), so each glyph is stored as ROWS = cell rows 0,2,3,4,5,6 (row 1 repeats row 0 for the
stems, row 7 only holds the tails of p and y); the game's '_' draws its bar in cell row 0 (an overline), it is moved to the last row (an underscore).
Source of truth: the original floppy disk A (work/floppy/disk_a.st = the STX conversion) at $310be; cross-checked against the RAM of the unpacked game
($190be in work/dumps/ram_hook_1024.bin, ram_race_start.bin) and against the HD release's RAM dump.
    python3 work/credit/gen_glyphs.py            # prints the table
"""
import sys
from pathlib import Path
R = Path(__file__).resolve().parents[2]
CHARS = " .0123456789abcdeghnprvy_"
DISK_OFF, RAM_OFF = 0x310BE, 0x190BE
disk = (R / "work/floppy/disk_a.st").read_bytes()
def glyph(buf, base, c): o = base + (ord(c) - 0x20) * 16; return buf[o:o + 16]
for n in ("ram_hook_1024.bin", "ram_race_start.bin", "ram_entry_1024.bin"):
    ram = (R / "work/dumps" / n).read_bytes()
    assert all(glyph(disk, DISK_OFF, c) == glyph(ram, RAM_OFF, c) for c in map(chr, range(0x20, 0x7F))), n
print(f"; font check: disk A ${DISK_OFF:x} == RAM ${RAM_OFF:x} for all 95 glyphs (3 dumps)", file=sys.stderr)
print('chars:  dc.b    "' + CHARS + '",0')
print("        even")
print("glyphs:")
ROWS = (0, 2, 3, 4, 5, 6)
for c in CHARS:
    g = glyph(disk, DISK_OFF, c)
    rows = [g[2 * r:2 * r + 2] for r in ROWS]
    if c == "_":
        rows = [bytes(2)] * (len(ROWS) - 1) + [g[0:2]]
    print("        dc.b    " + ",".join(f"${b:02x}" for r in rows for b in r) + f"   ; '{c}'")
