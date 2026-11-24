import re, sys, collections
def load(snap):
    txt = open(f'work/sprite/raw/foot_{snap}.log', errors='replace').read()
    parts = re.split(r"\n\t(pc = \$[0-9a-f]+) :trace :file [^\n]*\nReading debugger commands from[^\n]*\n", txt)
    ev = []
    for i in range(1, len(parts)-1, 2):
        pc = int(parts[i].split('$')[1], 16); body = parts[i+1]
        m = re.search(r"0000100E: ([0-9a-f]{2}) ([0-9a-f]{2})", body)
        mem = bytearray()
        for mm in re.finditer(r"^([0-9A-F]{8}): ((?:[0-9a-f]{2} ?){1,16})", body, re.M):
            a = int(mm.group(1), 16)
            if a >= 0x70000: mem += bytes.fromhex(mm.group(2).replace(' ', ''))
        if m and len(mem) >= 11200: ev.append((pc, int(m.group(1)+m.group(2), 16), bytes(mem[:11200])))
    return ev
for snap in sys.argv[1:]:
    ev = load(snap)
    foot = collections.Counter(); n = 0
    effE = collections.Counter()
    for i in range(len(ev)-2):
        (p1, c1, a), (p2, c2, b), (p3, c3, c) = ev[i:i+3]
        if (p1, p2, p3) == (0xde1c, 0xef84, 0xefb6) and c1 == c2 == c3:
            n += 1
            for k in range(11200):
                if b[k] != c[k]: foot[k] += 1
                if a[k] != b[k]: effE[k] += 1
    print(snap, 'passes', n, 'bytes written between E and D (union):', len(foot), ' bytes changed by E:', len(effE))
    rows = collections.defaultdict(set)
    for k in foot: rows[k // 160].add(k % 160)
    for r in sorted(rows):
        cols = sorted(rows[r]); 
        # compress to ranges
        rng = []; s = cols[0]; p = s
        for c in cols[1:]:
            if c != p + 1: rng.append((s, p)); s = c
            p = c
        rng.append((s, p)); print('  row', r, rng)


print("---- P0 words written between E and D inside each cloud's E-rect (x&~15 .. +80, rows y..y+h)")
exec(open('work/sprite/cloudan.py').read().split("for snap in sys.argv")[0])
for snap in ('race_grid','race_start','race_up'):
    ev = load(snap)
    ps = load_cloud = None
    cl = [s for s in [slotinfo(bytearray(open('/dev/null','rb').read()), 0)] ] if False else None
    # cloud rects from the cloud trace of the same snapshot (first pass)
    cps = None
    try:
        cp = globals()['load']  # footan.load shadowed by cloudan.load; reload explicitly
    except KeyError: pass
