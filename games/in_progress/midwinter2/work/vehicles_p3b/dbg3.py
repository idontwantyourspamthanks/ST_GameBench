import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
import re
snap, setname, cond, n = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]); pokes=sys.argv[5:]
from vgate import SETS
live = build_live(SETS[setname], 'dbg_'+setname)
h = Hatari(snapshot=str(SNAP/snap), memsize_kb=2048)
try:
    h.set_cpuclock(16)
    v = h.vbl()
    hit = h.R/'hit.txt'; hit.write_text('e VBL\nr\nm $b42e6 2\n')
    cmds = apply_cmds(live) + [ 'w $'+p.split('=')[0]+' '+' '.join('$%02x'%b for b in bytes.fromhex(p.split('=')[1])) for p in pokes] + [f'b {cond} :trace :file {hit}']
    start=len(h._logtext())
    at_flip(h, cmds, v+100)
    t=time.time()
    while len(re.findall(r'#\d+ \(dec\)', h._logtext()[start:])) < n:
        time.sleep(0.5)
        if time.time()-t>600: break
    h.debug('b all',0.5)
    txt=h._logtext()[start:]
    import os
    open('/tmp/dbg3.log','w').write(txt)
    for blk in txt.split('> e VBL')[1:]:
        m=re.search(r'#(\d+) \(dec\)',blk); pc=re.search(r'\n(\w{8}) \w{4}\s',blk)
        ph=re.search(r'B42E6: (\w\w) (\w\w)',blk)
        print(m.group(1), 'PH', int(ph.group(2),16) if ph else '?', 'PC' , re.findall(r'PC=\s*(\w+)|pc\s*=\s*(\$\w+)',blk)[:1], blk.split('\n')[-6:-4] )
finally:
    h.close()
