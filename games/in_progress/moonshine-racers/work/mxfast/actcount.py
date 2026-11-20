import sys, collections
from mflib import *
res = {}
for d in ['start', 'up', 'L0', 'L3', 'L5', 'L7', 'L10', 'L12', 'L14']:
    try:
        e = Emu(DUMPS[d]); apply_live(e, live_build('X', 'cmp_X')); e.setb(0xB8F21, 1)
        cnt = []; idxc = collections.Counter()
        for p in range(80):
            v = schedule(p, 'zig'); e.setb(0x6105, v); e.setb(0xB8F08, 0); e.setl(0xB8F00, 30 * (p + 1))
            e.run(0x7a88, 0x7b46)
            S = e.read(0x2c68, 2688)
            n = sum(1 for s in range(48) if S[s * 56 + 4] & 1)
            if p >= 5:
                cnt.append(n)
                for s in range(48):
                    if S[s * 56 + 4] & 1: idxc[s] += 1
            e.run(0x7b46, 0x7b7a); e.run(0x7b7a, 0x7a88)
        print(d, 'active slots at P: mean %.1f min %d max %d' % (sum(cnt) / len(cnt), min(cnt), max(cnt)), 'always-active idx', [s for s, c in idxc.items() if c == len(cnt)], 'ever', len(idxc))
    except Exception as ex:
        print(d, 'ERR', ex)
