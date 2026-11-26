import sys; sys.path.insert(0,'/tmp/ng12hd/nb/work/core')
import ikg, json
from pathlib import Path
O=Path('/tmp/ng12hd/q/hd111'); N=Path('/tmp/ng12hd/q/hd')
for nm,g in (('v111',O),('v12',N)):
    ikg.snap('megaste', g, 'ctl'+nm, 'x')
    f=ikg.MY/f'snap_ctl{nm}_megaste.sav'
    for spec in ('none','0.3:space:0.08'):
        r=ikg.trial('megaste',spec,game=g,snapf=f,tag='x'); r['build']=nm; print(json.dumps(r),flush=True)
