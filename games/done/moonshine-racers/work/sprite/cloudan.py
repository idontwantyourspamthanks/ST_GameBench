import re, sys, struct, collections
def load(snap):
    txt = open(f'work/sprite/raw/cloud_{snap}.log', errors='replace').read()
    parts = re.split(r"Reading debugger commands from[^\n]*\n", txt)[1:]
    passes = []
    for p in parts:
        m = re.search(r"0000100E: ([0-9a-f]{2}) ([0-9a-f]{2})", p)
        if not m: continue
        cnt = int(m.group(1)+m.group(2), 16)
        mem = bytearray()
        for mm in re.finditer(r"^([0-9A-F]{8}): ((?:[0-9a-f]{2} ?)+)", p, re.M):
            if int(mm.group(1),16) >= 0x29c8:
                mem += bytes.fromhex(mm.group(2).replace(' ',''))
        if len(mem) < 672: continue
        passes.append((cnt, mem[:672]))
    return passes
def slotinfo(mem, i):
    b = mem[i*56:(i+1)*56]
    w = struct.unpack('>28H', b)
    S = lambda v: v-65536 if v>=32768 else v
    return dict(active=b[4]&1, x=S(w[0]), y=S(w[1]), f6=w[3], f8=w[4], fc=w[6], o28=w[0x14], o2a=w[0x15], h=w[5], raw=b)
for snap in sys.argv[1:]:
    ps = load(snap)
    print(snap, 'passes', len(ps), 'counters', ps[0][0], '..', ps[-1][0])
    # consecutive passes only
    stats = collections.Counter(); per = collections.defaultdict(collections.Counter)
    for k in range(2, len(ps)):
        if ps[k][0] != ps[k-1][0] + 1 or ps[k-1][0] != ps[k-2][0] + 1: continue
        for i in range(12):
            a, b, c = slotinfo(ps[k-2][1], i), slotinfo(ps[k-1][1], i), slotinfo(ps[k][1], i)
            key = lambda s: (s['active'], s['x'], s['y'], s['f6'] + s['f8'])
            same2 = key(a) == key(c)
            same1 = key(b) == key(c)
            stats['cloud-passes'] += 1
            stats['same as 2 passes ago (skippable)'] += same2
            stats['same as 1 pass ago'] += same1
            stats['active'] += c['active']
            per[i]['n'] += 1; per[i]['same2'] += same2; per[i]['active'] += c['active']
    print(dict(stats))
    for i in range(12): print('  cloud', i, dict(per[i]))
    s = slotinfo(ps[5][1], 3); print({k: v for k, v in s.items() if k != 'raw'})
