#!/usr/bin/env python3
"""Which effect ids (and tunes' instruments) have sample data in [lo,hi) of the bank in RAM.  Parses build/asn_bank.bin only.
   usage: effects_in_tail.py [lo hi]   (default $e2b6a $e61b2)"""
import struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
b = (ROOT / "build/asn_bank.bin").read_bytes()
BANK = 0xBB000
lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0xE2B6A
hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else BANK + len(b)
nrows = struct.unpack_from(">H", b, 6)[0]
def rec(off):
    f = struct.unpack_from(">H", b, 0x700 + off)  # not used
    smp, ln = struct.unpack_from(">IH", b, 0x700 + off + 0x16)
    return smp, ln * 2
def seqrecs(woff):
    """effect record offsets in a sequence starting at word offset woff"""
    out = []
    i = woff
    while True:
        w = struct.unpack_from(">h", b, 0x300 + i)[0]
        if w <= 0:
            break
        out.append(w); i += 2
        if len(out) > 64: break
    return out
print(f"bank ${BANK:x}-${BANK+len(b):x}; window ${lo:x}-${hi:x}; {nrows} rows")
samples = {}
for sid in range(nrows):
    ch = struct.unpack_from(">4H", b, 0x100 + sid * 8)
    info = []
    for c, w in enumerate(ch):
        if w == 0xFFFF: continue
        for ro in seqrecs(w):
            if (ro - 2) % 28 or ro >= 0x65A: continue
            smp, ln = rec(ro)
            if smp == 0: continue
            info.append((c, ro, smp, ln))
    samples[sid] = info
    hit = [(c, ro, smp, ln) for c, ro, smp, ln in info if smp < hi and smp + ln > lo]
    allin = [(c, ro, smp, ln) for c, ro, smp, ln in info]
    cover = 0
    for c, ro, smp, ln in hit:
        cover += min(smp + ln, hi) - max(smp, lo)
    tot = sum(x[3] for x in info)
    print(f"id {sid:2d}: {len(info)} rec uses, sample bytes {tot:6d}; in window: {len(hit)} uses, {cover} bytes" + ("   <== AFFECTED" if hit else ""))
# the sample regions (distinct)
regs = sorted({(smp, ln) for v in samples.values() for _, _, smp, ln in v})
print("distinct sample regions:", len(regs))
for smp, ln in regs:
    f = "AFFECTED" if smp < hi and smp + ln > lo else ""
    print(f"  ${smp:x}-${smp+ln:x} ({ln:6d} B) {f}")
