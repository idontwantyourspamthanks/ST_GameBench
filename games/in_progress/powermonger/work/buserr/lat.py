import re,sys,collections
f=sys.argv[1]
irq=None; lat=[]; ovr=[]; 
for l in open(f):
    if 'update irq irq_new=1' in l and 'ikbd' in l:
        m=re.search(r'VBL=(\d+) HBL=(\d+)',l)
        if irq is None: irq=int(m[1])*313+int(m[2])
    elif 'clock_rx overrun' in l:
        m=re.search(r'VBL=(\d+) HBL=(\d+)',l); ovr.append((int(m[1]),int(m[2])))
    elif 'read rdr' in l:
        m=re.search(r'VBL=(\d+) HBL=(\d+)',l)
        if irq is not None: lat.append(int(m[1])*313+int(m[2])-irq)
        irq=None
c=collections.Counter(lat)
print('reads',len(lat),'overruns',len(ovr),'first',ovr[:3],'max latency HBL',max(lat) if lat else None, 'hist>=8:',sorted((k,v) for k,v in c.items() if k>=8))
