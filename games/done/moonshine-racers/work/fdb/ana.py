#!/usr/bin/env python3
"""Per key press timing from work/fdb/out/NAME_events.txt (written by fdb.py): python3 work/fdb/ana.py NAME [-v]
keys = the VBL read (+-1 s) just before each key press; the last key is the one after the swap (the check that succeeds, then the race load).
A press segment runs from its key to the next key.  check = first FDC event of the segment .. last FDC event of the check
(for the last key: .. last sector read of the race load = 'loaded').  VBL is emulated time at 50 Hz."""
import re, sys
name = sys.argv[1]
verbose = "-v" in sys.argv
L = open(f"/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/fdb/out/{name}_events.txt").read().splitlines()
keys = list(map(int, L[0].split()[1:]))
ev = [(int(re.search(r"VBL=(\d+)", l).group(1)), l) for l in L[2:] if "VBL=" in l]
for i, k in enumerate(keys):
    end = keys[i + 1] if i + 1 < len(keys) else 10 ** 9
    seg = [e for e in ev if k <= e[0] < end]
    if not seg:
        print(f"key {i + 1} @{k}: no FDC activity"); continue
    last_press = i == len(keys) - 1
    reads = [e for e in seg if "read sector" in e[1]]
    if last_press:                                  # the check + race load = events up to the first gap of more than 6 s
        cut = [seg[0]]
        for e in seg[1:]:
            if e[0] - cut[-1][0] > 300:
                break
            cut.append(e)
        seg = cut
    t0, t1 = seg[0][0], seg[-1][0]
    r1 = sum("drive=1" in e[1] for e in seg if "read sector" in e[1]); r0 = sum("read sector" in e[1] for e in seg) - r1
    iv = sum("type IV" in e[1] for e in seg)
    t1b = sum(1 for e in seg if re.search(r"fdc type I .*drive=1", e[1]))
    print(f"key {i + 1}{' (swap, succeeds)' if last_press else ' (fails)  '} @{k}: latency {(t0 - k) / 50:5.1f} s, check {(t1 - t0) / 50:6.2f} s  ({t0}->{t1}), reads A {r0} B {r1}, type I on B {t1b}, forced interrupts {iv}")
    if verbose and not last_press:
        for v, l in seg:
            print("     +%6.2fs %s" % ((v - t0) / 50, re.sub(r" VBL=.*", "", l)[:100]))
