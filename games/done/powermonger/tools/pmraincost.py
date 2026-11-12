#!/usr/bin/env python3
"""Mean cycles per rendered T / R pass, tick_wx (base) vs tick_rain: python3 tools/pmraincost.py SNAP MHZ KIND(0 = no rain, 1, 2).  notes/rain.md section 6."""
import sys; sys.path.insert(0,'tools')
import pmab, statistics as st
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
sn=sys.argv[1]; mhz=int(sys.argv[2]); kind=sys.argv[3]
sp=pmab.snap_path(sn); at=pmab.at_vbl_for(sp)
b=pmab.TICK+pmab.TESTSET; p=[('tick_rain' if n=='tick_wx' else n) for n in b]
bl,pl=pmab.make_live(b),pmab.make_live(p)
pk=(f"4bb42:{int(kind):04x}","4bb44:2000") if kind!='0' else ()
with ThreadPoolExecutor(2) as ex:
    fb=ex.submit(pmab.one,sp,at,bl,Path('/tmp/rc_b'),700,mhz,False,True,False,pk)
    fp=ex.submit(pmab.one,sp,at,pl,Path('/tmp/rc_p'),700,mhz,False,True,False,pk)
    B,P=fb.result(),fp.result()
for nm,R in (('base',B),('rain',P)):
    for k in (0,1):
        w=[r['work'] for r in R['recs'] if r['work'] is not None and bool(r['ron'])==bool(k)]
        print(nm,'R' if k else 'T',len(w),round(st.mean(w)) if w else None)
