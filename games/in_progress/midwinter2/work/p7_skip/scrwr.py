import sys, collections
sys.path.insert(0,'.')
import rdset
recs = rdset.parse(sys.argv[1])
ENTRY = {0x263de, 0x26298, 0x26882}
isr=[]; phase='pre'
wr=collections.defaultdict(lambda: collections.defaultdict(set))  # phase -> pc -> addrs
rd_scr=collections.defaultdict(lambda: collections.Counter())
for (pc,mn,ops,nxt,line) in recs:
    if pc in ENTRY: isr.append(pc)
    if isr:
        if mn.startswith('rte'): isr.pop()
        continue
    if pc==0x5056: phase='render'
    if pc==0x315a8: phase='post'
    if pc==0x315c6: phase='flip'
    if pc==0x315ca: phase='postflip'
    for kind,ea,size in rdset.accesses(mn,ops):
        if 0x60000<=ea<0x80300:
            if kind=='W' : wr[phase][pc].add(ea)
            else: rd_scr[phase][pc]+=1
for ph in ('pre','render','post','flip','postflip'):
    print('==',ph)
    for pc,a in sorted(wr[ph].items()):
        lo,hi=min(a),max(a)
        base=0x60000 if lo<0x70000 else 0x70000
        rows=sorted({((x-base)//160) for x in a if x < base+32000})
        print(f'  pc {pc:06x}: {len(a)} bytes {lo:06x}-{hi:06x}  rows {rows[:3]}..{rows[-3:]} nrows {len(rows)}')
