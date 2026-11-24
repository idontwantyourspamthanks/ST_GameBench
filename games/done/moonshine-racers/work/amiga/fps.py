from cl import *
import json
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 2.adf'])
with Session(m) as s:
    s.load_state(OUT+'st_n5.clstate')
    s.joy(port=2,up=True)
    s.run_for(10)
    ds=[]
    for i in range(600):
        s.run_frames(1); ds.append(s.region_digest(0,40,716,200) if False else s.digest())
    ch=[i for i in range(1,len(ds)) if ds[i]!=ds[i-1]]
    iv=[b-a for a,b in zip(ch,ch[1:])]
    import collections
    print('frames',len(ds),'changes',len(ch)); print(collections.Counter(iv).most_common(10))
    json.dump(ds,open(OUT+'fps_digests.json','w'))
