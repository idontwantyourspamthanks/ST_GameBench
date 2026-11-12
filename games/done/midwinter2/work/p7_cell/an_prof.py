import re, sys, collections
def load(prefix):
    txt = open(prefix + '.save').read()
    d = {'addr': {}, 'edges': [], 'total': 0}
    # per-address
    for m in re.finditer(r'^\$([0-9a-f]{8})\s+(.*?)\s+[\d.]+% \((\d+), (\d+), \d+, \d+\)$', txt, re.M):
        a = int(m.group(1), 16); d['addr'][a] = (int(m.group(3)), int(m.group(4)), m.group(2).strip())
    d['total'] = sum(v[1] for v in d['addr'].values())
    sec = txt.split('# totals: calls/instructions/cycles/i-misses/d-hits\n', 1)[1]
    for line in sec.splitlines():
        m = re.match(r'0x([0-9a-f]+): (.*), (\S+)$', line)
        if not m: continue
        callee = int(m.group(1), 16)
        for c in re.finditer(r'0x([0-9a-f]+) = (\d+) ([unbsrex]+)(?: (\d+)/(\d+)/(\d+) (\d+)/(\d+)/(\d+))?', m.group(2)):
            pc = int(c.group(1), 16); n = int(c.group(2)); typ = c.group(3)
            if c.group(4) is not None:
                d['edges'].append(dict(callee=callee, pc=pc, n=n, typ=typ, icalls=int(c.group(4)), iinst=int(c.group(5)), icyc=int(c.group(6)), ecalls=int(c.group(7)), einst=int(c.group(8)), ecyc=int(c.group(9))))
    return d
if __name__ == '__main__':
    for p in 'wfb':
        d = load('/tmp/render_audit/' + p)
        fl = [e for e in d['edges'] if e['callee'] == 0x4f36]
        print(p, 'total', d['total'], 'addrs', len(d['addr']), 'edges', len(d['edges']), 'flips', fl[0]['n'] if fl else None)
