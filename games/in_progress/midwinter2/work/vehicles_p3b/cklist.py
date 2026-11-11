#!/usr/bin/env python3
import sys; sys.path.insert(0, "/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b")
"""cklist.py: for every vehicle snapshot, dump the cockpit overlay list ($68000.., pointer $71bc) and decode its opacity per row.
  python3 cklist.py dump  -> /tmp/ck/<snap>.bin (+ .ptr) ;  python3 cklist.py decode -> table"""
import sys, struct, json, time
from vt import *

SNAPS = ['raid_jeep_dhafra','raid_truck_aledo','raid_bus_galva','raid_onfoot_dhafra','raid_speedboat_iquitos','raid_crawler_panao','raid_submarine_jebba','raid_ship_bourem',
         'raid_biplane_maracay','raid_helicopter_lobos','raid_balloon_corozal','raid_parachute_calabar','raid_flyingboat_vicenza','raid_hovercraft_thar','raid_swimming_vitoria']
def dump():
    import os
    os.makedirs('/tmp/ck', exist_ok=True)
    for s in SNAPS:
        h = Hatari(snapshot=str(SNAP / (s + '.sav')), memsize_kb=2048)
        try:
            time.sleep(1)
            ty = h.peekw(0x6220)
            p = (h.peekw(0x71bc) << 16) | h.peekw(0x71be)
            q = (h.peekw(0x71c0) << 16) | h.peekw(0x71c2)
            h.debug(f'savebin /tmp/ck/{s}.bin $68000 $4000', 1.5)
            open(f'/tmp/ck/{s}.ptr', 'w').write(json.dumps(dict(type=ty, p71bc=p, p71c0=q, tab7824=h.peekw(0x7824))))
            print(s, ty, hex(p), hex(q))
        finally:
            h.close()
def decode(s):
    d = open(f'/tmp/ck/{s}.bin', 'rb').read(); ptr = json.load(open(f'/tmp/ck/{s}.ptr'))
    off = ptr['p71bc'] - 0x68000
    if not (0 <= off < len(d)): return None
    n = struct.unpack_from('>h', d, off)[0]; off += 2
    pos = 0                                   # destination offset from the buffer base
    rows = {}                                  # row -> number of opaque pixels
    recs = 0
    for _ in range(n + 1):
        w = struct.unpack_from('>h', d, off)[0]
        if w >= 0:
            pos += w; mask, or1, or2 = struct.unpack_from('>III', d, off + 2); off += 14
            m = (mask >> 16) & 0xffff
            row = pos // 160; 
            rows[row] = rows.get(row, 0) + (16 - bin(m).count('1') if True else 0)
            pos += 8
        else:
            pos += (~w) & 0xffff; cnt = struct.unpack_from('>h', d, off + 2)[0] + 1; off += 4 + 8 * cnt
            for g in range(cnt):
                row = (pos + 8 * g) // 160; rows[row] = rows.get(row, 0) + 16
            pos += 8 * cnt
        recs += 1
    return rows, recs
if __name__ == '__main__':
    if sys.argv[1] == 'dump': dump()
    else:
        for s in SNAPS:
            try: r = decode(s)
            except Exception as e: print(s, 'ERR', e); continue
            ptr = json.load(open(f'/tmp/ck/{s}.ptr'))
            if r is None: print(s, ptr['type'], 'no list'); continue
            rows, recs = r
            vis = {y: 320 - 1 - rows.get(y, 0) for y in range(58, 200)}
            lost = sum(rows.get(y, 0) for y in range(182, 200)); tot = sum(rows.get(y, 0) for y in range(58, 200))
            print(f"{s:28s} type {ptr['type']:2d} recs {recs:3d} opaque px rows 58-181 {tot-lost:5d} rows 182-199 {lost:5d} (of {18*319}); rows with 0 opaque: {sum(1 for y in range(58,200) if rows.get(y,0)==0)}")
