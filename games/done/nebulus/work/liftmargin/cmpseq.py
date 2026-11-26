"""Compare two seq.py runs loop by loop: displayed buffer pixels, variable block $33900..$33a4f, timer words, lift column, VBL deltas.  usage: cmpseq.py TAG_A TAG_B"""
import re, sys
from pathlib import Path
def load(tag):
    D = Path('/tmp/nlm/sq_' + tag); txt = (D / 'log.txt').read_text()
    caps = {}; cur = None; ctx = None
    for line in txt.splitlines():
        m = re.match(r'> e (77\d\d|7[89]\d\d)$', line)
        if m: cur = int(m.group(1)) - 7700; caps[cur] = {'vbl': None, 'm': {}}; ctx = None; continue
        if cur is None: continue
        if line.startswith('> m $'): ctx = line.split()[2]; caps[cur]['m'].setdefault(ctx, bytearray()); continue
        if line.startswith('> e VBL'): ctx = 'vbl'; continue
        m = re.match(r'= .*#(\d+) \(dec\)', line)
        if m and ctx == 'vbl': caps[cur]['vbl'] = int(m.group(1)); continue
        m = re.match(r'([0-9A-F]{8}):\s+((?:[0-9a-f]{2} )+)', line)
        if m and ctx and ctx != 'vbl': caps[cur]['m'][ctx] += bytes.fromhex(m.group(2).replace(' ', ''))
    out = {}
    for k, c in caps.items():
        base = int.from_bytes(c['m']['$38758'][:4], 'big')
        buf = (D / f'{"b" if base == 0x78000 else "a"}_{k}.bin').read_bytes() if (D / f'a_{k}.bin').exists() else b''
        out[k] = dict(vbl=c['vbl'], buf=buf, vars=bytes(c['m']['$33900']), timer=bytes(c['m']['$3ad98']), col=bytes(c['m'][[x for x in c['m'] if x.startswith('$327') or x.startswith('$32')][0]]))
    return out
if __name__ == '__main__':
    A, B = load(sys.argv[1]), load(sys.argv[2])
    n = min(len(A), len(B)); bad = []; vd = []
    for k in sorted(set(A) & set(B)):
        a, b = A[k], B[k]
        px = sum(1 for x, y in zip(a['buf'], b['buf']) if x != y) + abs(len(a['buf']) - len(b['buf']))
        vv = [hex(0x33900 + i) for i in range(min(len(a['vars']), len(b['vars']))) if a['vars'][i] != b['vars'][i]]
        if px or vv or a['timer'] != b['timer'] or a['col'] != b['col']: bad.append((k, px, vv[:8], a['timer'] != b['timer'], a['col'] != b['col']))
    va = [A[k]['vbl'] - A[k - 1]['vbl'] for k in sorted(A) if k - 1 in A]; vb = [B[k]['vbl'] - B[k - 1]['vbl'] for k in sorted(B) if k - 1 in B]
    print(f'{sys.argv[1]} vs {sys.argv[2]}: {n} loops compared, differing loops: {len(bad)}', bad[:12])
    print(f'  VBL/loop A: {sum(va)/max(len(va),1):.3f} (>2: {sum(1 for x in va if x>2)})  B: {sum(vb)/max(len(vb),1):.3f} (>2: {sum(1 for x in vb if x>2)})')
