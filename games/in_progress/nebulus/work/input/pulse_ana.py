import re, sys, json
FPC = 160256
def stamps(seg):
    ev = []   # (kind, T)
    lines = seg.splitlines()
    kind = None
    for i, l in enumerate(lines):
        m = re.match(r'\d+\. CPU breakpoint condition.*', l)
        if m and i + 1 < len(lines):
            nxt = lines[i + 1]
            kind = 'POLL' if '$3853a' in nxt else ('SUBA' if 'subA' in nxt else ('SUBC' if 'subC' in nxt else ('SHOOT' if '$3a2f8' in nxt else ('LATCH' if '$76d14' in nxt else ('CONSUME' if '$76d2e' in nxt else None)))))
            ev.append([kind, None, None]); continue
        if l.startswith('> r d0=$80') and ev is not None: ev.append(['A', None, None]); kind = 'A'; continue
        if l.startswith('> r d0=$00'): ev.append(['B', None, None]); kind = 'B'; continue
        m = re.match(r'= .*#(\d+) \(dec\)', l)
        if m and ev:
            if ev[-1][1] is None: ev[-1][1] = int(m.group(1))
            elif ev[-1][2] is None: ev[-1][2] = int(m.group(1))
    return [(k, v * FPC + f) for k, v, f in ev if k and v is not None and f is not None]
def main(tag):
    segs = open(f'real_{tag}.dbg').read().split('\n=====\n')
    rows = []
    for s in segs:
        e = stamps(s)
        A = next((t for k, t in e if k == 'A'), None); B = next((t for k, t in e if k == 'B'), None)
        polls = [t for k, t in e if k == 'POLL' and A and B and A < t < B]
        shoot = any(k == 'SHOOT' for k, t in e)
        rows.append((round((B - A) / FPC, 3) if A and B else None, len(polls), shoot, any(k == 'LATCH' for k, _ in e), any(k == 'CONSUME' for k, _ in e)))
    return rows
if __name__ == '__main__':
    for tag in sys.argv[1:]:
        rows = main(tag)
        print('==', tag, 'trials', len(rows), '(gap_frames, polls inside the pulse, fire reached stand-fire handler, latch set, latch consumed)')
        for r in rows: print('  ', r)
        ok = [r for r in rows if r[0] is not None]
        print('   one-frame pulses', len(ok), '| registered', sum(r[2] for r in ok), '| pulses with 0 polls inside:', sum(1 for r in ok if r[1] == 0), 'registered', sum(1 for r in ok if r[1] == 0 and r[2]), '| with >=1 poll inside:', sum(1 for r in ok if r[1] > 0), 'registered', sum(1 for r in ok if r[1] > 0 and r[2]))
