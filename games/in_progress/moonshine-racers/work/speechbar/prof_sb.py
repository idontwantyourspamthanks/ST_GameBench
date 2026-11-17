"""Cycle profile between labels inside sbent: python3 prof_sb.py SNAP SET NPASS name=addr ... ; events in order per pass, mean cycles between consecutive events (typing passes only: $11ab == 1 at the end)"""
import sys, re, time, collections, statistics as st
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/speechbar')
from sblib import *
import msrabtest as ab
from msr import Moonshine
snap, setn, npass = sys.argv[1], sys.argv[2], int(sys.argv[3])
pcs = {a.split('=')[0]: int(a.split('=')[1], 16) for a in sys.argv[4:]}
names = list(pcs)
live = live_build_sb(SETS[setn], setn)
h = Moonshine(snapshot=ab.snap_path(snap)); R = h.R; CYC = 160256
try:
    time.sleep(1.5); ab.apply_live(h, live, 0x7A88); time.sleep(0.4); h.debug('b all', 0.3)
    for j, k in enumerate(names): (R / f'pf_{k}.txt').write_text(f"e VBL\ne FrameCycles\ne {1000 + j}\nm $11ab 1\n")
    n0 = len(h._logtext())
    for k, pc in pcs.items(): h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {R}/pf_{k}.txt"); time.sleep(0.2)
    t0 = time.time()
    while h._logtext()[n0:].count('> e VBL') < 12 * npass and time.time() - t0 < 600: time.sleep(2)
    h.debug('b all', 0.5); log = h._logtext()[n0:]
finally:
    h.close()
ev = []
for sg in log.split('> e VBL')[1:]:
    nums = re.findall(r'#(\d+) \(dec\)', sg)
    m = re.search(r'\n[0-9a-f]{8}:\s+([0-9a-f]{2})', sg, re.I)
    if len(nums) >= 3: ev.append((int(nums[0]) * CYC + int(nums[1]), names[int(nums[2]) - 1000], int(m.group(1), 16) if m else 0))

agg = collections.defaultdict(list)
first = names[0]
i = 0
while i < len(ev):
    if ev[i][1] == first:
        j = i + 1
        while j < len(ev) and ev[j][1] != first: j += 1
        seq = ev[i:j]
        if seq[-1][2] == 1 or any(e[2] == 1 for e in seq):          # typing pass ($11ab == 1 at some event)
            for a, b in zip(seq, seq[1:]): agg[(a[1], b[1])].append(b[0] - a[0])
            agg[('total', first)].append(seq[-1][0] - seq[0][0])
        i = j
    else: i += 1
for k, v in agg.items(): print(f"{k[0]:>8s} -> {k[1]:8s} n {len(v):4d} mean {st.mean(v):8.0f}")
