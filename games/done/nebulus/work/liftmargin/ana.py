"""Parse a ride.py log into per-loop records: busy/total cycles, VBL delta, player vars."""
import re, sys, statistics as S
VBLC = 160256
def parse(path):
    txt = open(path).read()
    ev = []; cur = None
    for line in txt.splitlines():
        m = re.match(r'> e (770[12])$', line)
        if m: cur = {'k': 'F' if m.group(1) == '7701' else 'P', 'skip': 1}; ev.append(cur); continue
        if cur is None: continue
        m = re.match(r'= .*#(\d+) \(dec\)', line)
        if m:
            if cur['skip']: cur['skip'] = 0
            elif 'vbl' not in cur: cur['vbl'] = int(m.group(1))
            elif 'cyc' not in cur: cur['cyc'] = int(m.group(1))
            continue
        m = re.match(r'(0003[0-9A-F]{4}):\s+((?:[0-9a-f]{2} )+)', line)
        if m: cur[m.group(1)] = bytes.fromhex(m.group(2).replace(' ', ''))
    loops = []; lastF = None; lastP = None
    for e in ev:
        if e['k'] == 'P': lastP = e; continue
        if lastF is not None and lastP is not None and 'cyc' in e and 'cyc' in lastF:
            p = e.get('00033A16', b'\0' * 12)
            loops.append(dict(vbl=e['vbl'] - lastF['vbl'], tot=e['cyc'] - lastF['cyc'], busy=lastP['cyc'] - lastF['cyc'],
                              spin=e['cyc'] - lastP['cyc'], x=int.from_bytes(p[0:2], 'big'), y=int.from_bytes(p[2:4], 'big'),
                              st=int.from_bytes(p[10:12], 'big'), stem=int.from_bytes(e.get('0003390A', b'\xff\xff'), 'big'),
                              timer=e.get('0003AD98', b'')))
        lastF = e
    return loops
def summ(name, L):
    if not L: print(name, 'no loops'); return
    n = len(L); v = [l['vbl'] for l in L]
    print(f'{name}: loops {n}  VBL/loop mean {sum(v)/n:.3f}  >2VBL {sum(1 for x in v if x > 2)} ({100*sum(1 for x in v if x>2)/n:.1f}%)  '
          f'fps {50*n/sum(v):.2f}  busy mean {S.mean(l["busy"] for l in L):.0f} max {max(l["busy"] for l in L)}  spin mean {S.mean(l["spin"] for l in L):.0f}  '
          f'hist {dict(sorted(__import__("collections").Counter(v).items()))}')
if __name__ == '__main__':
    L = parse(sys.argv[1])
    for i, l in enumerate(L):
        if '-v' in sys.argv: print(i, l['vbl'], l['tot'], l['busy'], l['spin'], 'x', l['x'], 'y', l['y'], 'st', l['st'], 'stem', hex(l['stem']))
    summ('all', L)
    # phases by state
    summ('state0 before', [l for i, l in enumerate(L) if l['st'] == 0 and i < next((j for j, q in enumerate(L) if q['st'] == 6), 10**9)])
    summ('state6 ride', [l for l in L if l['st'] == 6])
    summ('after', [l for i, l in enumerate(L) if l['st'] != 6 and i > max([j for j, q in enumerate(L) if q['st'] == 6] or [-1])])
