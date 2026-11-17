"""Hatari flip-by-flip capture: python3 hflips.py SET MHZ NPASS OUTDIR [KS=140]
X_TEST = 1 (one extra per tick at f = 1/2, no timing), steering zig as a pure function of the pass key, at the end of every pass ($7b86, after the group) both screen buffers are
saved: with one extra per tick they hold the main frame and the extra of that pass (the drawn pair), so every pass gives 2 frames (main + extra)."""
import sys, time, re
from hlib import *
sset, mhz, npass, outd = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
KS = int(sys.argv[5]) if len(sys.argv) > 5 else 140
import os; os.makedirs(outd, exist_ok=True)
for f in os.listdir(outd): os.remove(os.path.join(outd, f))
od = os.path.abspath(outd)
h = open_snap('ste1m_race_start.sav', 8)
try:
    if sset != 'A': apply_prefix(h, live_build(sset, 'hf_' + sset), pokes=[(0xB8F21, b'\x01')])
    if mhz != 8: h.set_cpuclock(mhz)
    time.sleep(0.5); h.debug('b all', 0.3)
    vals = [1, 5, 1, 9]
    for K in range(KS, KS + npass + 3):
        (h.R / f'z_{K}.txt').write_text(f"w $6105 ${vals[((K - KS) // 15) % 4]:02x}\nb pc = $7a88 && ($100e).w = ${K + 1:x} :trace :once :file {h.R}/z_{K + 1}.txt\n")
        (h.R / f's_{K}.txt').write_text(f"savebin {od}/f{K}_a.bin $70000 $7d00\nsavebin {od}/f{K}_b.bin $78000 $7d00\nm $1008 4\nb pc = $7b86 && ($100e).w = ${K + 1:x} :trace :once :file {h.R}/s_{K + 1}.txt\n")
    h.cmd(f"hatari-debug b pc = $7a88 && ($100e).w = ${KS:x} :trace :once :file {h.R}/z_{KS}.txt"); time.sleep(0.3)
    h.cmd(f"hatari-debug b pc = $7b86 && ($100e).w = ${KS:x} :trace :once :file {h.R}/s_{KS}.txt")
    t0 = time.time()
    while not os.path.exists(f'{od}/f{KS + npass}_b.bin') and time.time() - t0 < 1500: time.sleep(2)
    time.sleep(1)
finally:
    h.close()
print(sset, mhz, 'captured', len([f for f in os.listdir(outd) if f.endswith('_b.bin')]), 'passes')
