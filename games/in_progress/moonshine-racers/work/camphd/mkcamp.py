#!/usr/bin/env python3
"""Test campaigns for the HD campaign gates (scratch): three short custom tracks (the finish bar moved to unit ~700-900 so a race ends in seconds),
the stock 15-track campaign, three damaged files and campaign disks.   python3 work/camphd/mkcamp.py"""
import copy, json, sys, zlib
from pathlib import Path
G = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(G / "tools")); sys.path.insert(0, str(G / "work/trackedit"))
import msrtrack as M, make_fixtures as F
OUT = Path(__file__).resolve().parent / "camp"; OUT.mkdir(exist_ok=True)
ms2 = M.read_ms2(None)

def quick(t, at, name):
    t = copy.deepcopy(t); t["name"] = name
    bt = {n + 1 for n, e in enumerate(t["types"]) if e[2] == M.BAR_SPRITE}
    bar = [o for o in t["objects"] if o["type"] in bt]; assert len(bar) == 1
    t["objects"].remove(bar[0]); bar[0]["at"] = at; bar[0]["lateral"] = 0
    i = next((k for k, o in enumerate(t["objects"]) if o["at"] > at), len(t["objects"]))
    t["objects"].insert(i, bar[0])
    assert not [x for x in M.validate_track(t) if x.level == "ERROR"], M.validate_track(t)
    return t
t1 = quick(F.edit1(), 700, "TEST ONE EDIT1 BEND")
t2 = quick(M.decode_stock(ms2, 3)[0], 800, "TEST TWO LEVEL 4 BASE")
t3 = quick(M.decode_stock(ms2, 5)[0], 900, "TEST THREE LEVEL 6 BASE")
for i, t in enumerate((t1, t2, t3), 1):
    (OUT / f"t{i}.json").write_text(M.dumps_json(t))
ents = [(t["name"], t["base_level"], M.encode_track(t)) for t in (t1, t2, t3)]
c3 = M.build_campaign(ents); (OUT / "c3.trk").write_bytes(c3)
c15 = M.build_campaign([(f"STOCK {lev:02d}", lev, M.decode_stock(ms2, lev)[1]) for lev in range(15)]); (OUT / "c15.trk").write_bytes(c15)
# a 4-track campaign that repeats a base level and has a stock 'long' last track (for the end test, the quick tracks)
c1 = M.build_campaign(ents[:1]); (OUT / "c1.trk").write_bytes(c1)
bad = bytearray(c3); bad[-9] ^= 0x40; (OUT / "bad_crc.trk").write_bytes(bytes(bad))               # one bit in the last block
bad = bytearray(c3); bad[0] = 0x58; (OUT / "bad_magic.trk").write_bytes(bytes(bad))
bad = bytearray(c3); bad[16 + 3] ^= 1; (OUT / "bad_table.trk").write_bytes(bytes(bad))              # name byte: table CRC
(OUT / "bad_short.trk").write_bytes(c3[:-100])
for n, f in (("c3", c3), ("c15", c15), ("bad_crc", (OUT / "bad_crc.trk").read_bytes())):
    (OUT / f"{n}.st").write_bytes(M.build_disk(f))
print({p.name: p.stat().st_size for p in sorted(OUT.iterdir())})
