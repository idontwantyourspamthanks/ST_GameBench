#!/usr/bin/env python3
"""Where are the sprite-$21 ('finish') objects in each of the 15 tracks, relative to the race length (word 0 of the minimap block)?"""
import sys, struct
sys.path.insert(0, '../trackstudy')
import msrtrack as M
for lev in range(15):
    t, b = M.parse(lev)
    off = t['types_off']
    types = []
    while off + 12 <= len(b) and struct.unpack('>H', b[off:off+2])[0] == 0xff00:
        types.append(struct.unpack('>6h', b[off:off+12])); off += 12
    ms, mn = M.descr('minimap_hdr', lev)
    rlen = struct.unpack('>H', M.MS2[ms*512:ms*512+2])[0]
    pos = t['obj_first']; hits = []; last = 0
    for i, (ty, lat, gap) in enumerate(t['objs']):
        if 1 <= ty <= len(types) and types[ty-1][3] == 0x21:
            hits.append((i, ty, lat, pos))
        last = pos
        pos += gap
    print(f"lev {lev:2d} len {rlen:5d} ntypes {len(types):3d} objs {len(t['objs'])} last_obj_pos {last} final_pos {pos}  sprite33 objs: {hits}")
