#!/usr/bin/env python3
"""Build a NEBLEVEL.OVL with one level: original M1 T1 with the first lift's end moved (6,4) -> (6,12) (+ doors above removed, + crumbling start ledge made solid).
usage: mk_lift_ovl.py OUT.ovl"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'editor'))
import ovl
g, rows = ovl.original(1, 0)
assert g[6][2] == 0x85 and g[6][4] == 0x08, (g[6][2], g[6][4])
g[6][4] = 0x00                         # old end marker
for r in (5, 6, 7): g[6][r] = 0        # the 3-cell door above the old end (a ride would flatten it)
g[6][12] = 0x08                        # new end marker, 8 rows above the start slab
g[3][1] = g[4][1] = 0x81               # crumbling start ledge -> solid (the test frog must not fall)
Path(sys.argv[1]).write_bytes(ovl.build([ovl.level(1, 0, rows, g, name="LIFT TEST")], [ovl.camp("LIFT TEST", [0])]))
