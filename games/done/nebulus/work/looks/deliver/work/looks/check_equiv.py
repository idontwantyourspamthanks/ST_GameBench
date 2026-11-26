"""flags-0 / original-tower equivalence: level-start dumps of the SAME stock sequence on the un-hooked build (OLD, HEAD patch set) and the hooked build (NEW).
usage: check_equiv.py OLDDIR NEWDIR N   -> per level, per region: equal?  (regions of run_look.py: palette, raster, skyline buffer, sprite buffers incl. eye frames, grid, game variables)"""
import sys, struct
OLD, NEW, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
REG = [('palette', 0x351ac, 0x20), ('raster', 0x40398, 8), ('skyline buf', 0x100e0, 0x1000), ('eye frames', 0x24be0, 0x2fae0 - 0x24be0), ('ball frames (sample)', 0x14560, 0x400),
       ('grid', 0x327f0, 0x1000), ('game vars $33900..', 0x33900, 0x180), ('timer', 0x3ad90, 0x20)]
bad = 0
for i in range(N):
    a = open(f'{OLD}/lvl{i}.bin', 'rb').read(); b = open(f'{NEW}/lvl{i}.bin', 'rb').read()
    tw = struct.unpack('>H', b[0x3390c:0x3390e])[0], struct.unpack('>H', b[0x33910:0x33912])[0]
    line = []
    for n, ad, ln in REG:
        eq = a[ad:ad + ln] == b[ad:ad + ln]
        if not eq:
            diffs = [ad + k for k in range(ln) if a[ad + k] != b[ad + k]]
            line.append(f'{n}: DIFF {len(diffs)} B first ${diffs[0]:x}' if n not in ('game vars $33900..', 'timer') else f'{n}: {len(diffs)} B differ at ' + ' '.join(f'${d:x}' for d in diffs[:6]))
            if n not in ('game vars $33900..', 'timer'): bad += 1
        else: line.append(f'{n}: equal')
    rc = struct.unpack('>H', b[0x77c80 + 62:0x77c80 + 64])[0]; re_ = struct.unpack('>H', b[0x77c80 + 50:0x77c80 + 52])[0] & 3
    print(f'level {i} tower {tw[0]} mission {tw[1]} | ' + ' | '.join(line) + f' | NEW cache rsCol {rc} rsEye {re_} (must be tower {tw[0]} / {tw[0] & 3})')
    if rc != tw[0] or re_ != tw[0] & 3: bad += 1
print('FAILS', bad)
