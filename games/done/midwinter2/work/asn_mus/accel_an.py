#!/usr/bin/env python3
"""Analyse work/asn_mus/accel/TAG/samples.log (accel_route.py): state transitions, tune windows, tick/VBL consistency."""
import re, sys
from pathlib import Path
tag = sys.argv[1]
d = Path(__file__).resolve().parent / "accel" / tag
txt = (d / "samples.log").read_text(errors="replace")
rows = []
for b in txt.split("> e VBL\n")[1:]:
    m = re.search(r"#(\d+) \(dec\)", b)
    if not m: continue
    got = {}
    for mm in re.finditer(r"^([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)", b, re.M | re.I):
        a0 = int(mm.group(1), 16)
        for i, x in enumerate(mm.group(2).split()): got[a0 + i] = int(x, 16)
    g = lambda a, k: bytes(got.get(a + i, 0) for i in range(k))
    sv = g(0xbbe00, 24)
    rows.append(dict(vbl=int(m.group(1)), p5138=g(0x5138, 4).hex(), t7626=int.from_bytes(g(0x7626, 2), "big"), b96=int.from_bytes(g(0xb96, 4), "big"),
                     b9a=g(0xb9a, 1)[0], ba2=int.from_bytes(g(0xba2, 2), "big"), mode=sv[0], act=sv[1], dma=sv[2], mus=sv[0x12], rate=sv[0x14],
                     tick=int.from_bytes(g(0xbbed0, 4), "big"), ff8901=g(0xff8901, 1).hex(), pos=g(0xff8909, 3).hex()[4:], ff8921=g(0xff8921, 1).hex(),
                     t6220=int.from_bytes(g(0x6220, 2), "big"), t700a=int.from_bytes(g(0x700a, 2), "big"), b40b6=int.from_bytes(g(0x40b6, 2), "big"),
                     ym=g(0xbc0, 16).hex(), dist=int.from_bytes(g(0x6888, 2), "big")))
print(f"{len(rows)} samples, VBL {rows[0]['vbl']}..{rows[-1]['vbl']} ({(rows[-1]['vbl'] - rows[0]['vbl']) / 50.05:.1f} s emulated); max gap {max(b['vbl'] - a['vbl'] for a, b in zip(rows, rows[1:]))} VBL")
prev = None
for r in rows:
    key = (r["p5138"], r["t7626"], r["b96"], r["b9a"], r["act"], r["dma"], r["mus"], r["rate"], r["ff8901"], r["ff8921"], r["b40b6"])
    if key != prev:
        print(f"VBL {r['vbl']:6d} t={(r['vbl'] - rows[0]['vbl']) / 50.05:7.1f}s $5138={r['p5138']} $7626={r['t7626']} $b96={r['b96']} $b9a={r['b9a']} act={r['act']} dma={r['dma']} tune={r['mus']} rate={r['rate']} "
              f"tick={r['tick']} $ff8901={r['ff8901']} $ff8921={r['ff8921']} $40b6={r['b40b6']:04x} $6220={r['t6220']} $700a={r['t700a']} dist={r['dist']}")
        prev = key
# tick progress per VBL while ticking sessions run
bad = []
for a, b in zip(rows, rows[1:]):
    if a["p5138"] == b["p5138"] and a["act"] == b["act"] and a["act"] in (1, 2) and a["dma"] == 255 and a["ff8901"] == "03" and b["tick"] == a["tick"] and b["vbl"] > a["vbl"]:
        bad.append((a["vbl"], b["vbl"], a["tick"]))
print("intervals with the same session and no tick progress while DMA on:", bad[:10], len(bad))
print("distinct ring positions (mid byte) seen:", sorted({r["pos"] for r in rows}))
print("ym shadow regs nonzero anywhere:", sorted({r["ym"] for r in rows})[:6])
anom = []
for a, b in zip(rows, rows[1:]):
    if a["act"] == 2 and b["act"] == 2 and a["mus"] == b["mus"] and a["tick"] > 0 and b["tick"] >= a["tick"] and b["vbl"] - a["vbl"] <= 100:
        dv, dt = b["vbl"] - a["vbl"], b["tick"] - a["tick"]
        if abs(dv - dt) > 2: anom.append((a["vbl"], b["vbl"], dv, dt))
mus = [r for r in rows if r["act"] == 2]; sfx = [r for r in rows if r["act"] == 1]
print("music-session intervals where ticks != VBLs (+-2):", anom)
print("music samples:", len(mus), "dma on:", sum(1 for r in mus if r["dma"] == 255), "$ff8901", {r["ff8901"] for r in mus}, "| sfx samples:", len(sfx), "dma on:", sum(1 for r in sfx if r["dma"] == 255),
      "$ff8921", {r["ff8921"] for r in sfx}, "rate", {r["rate"] for r in sfx}, "| sfx span VBL", sfx[0]["vbl"] if sfx else None, sfx[-1]["vbl"] if sfx else None)
