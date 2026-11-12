import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
import re
snap, setname = sys.argv[1], sys.argv[2]
pcs = sys.argv[3]; dumps = sys.argv[4].split(','); n = int(sys.argv[5]); pokes=sys.argv[6:]
from vgate import SETS
live = build_live(SETS[setname], 'dbg_'+setname)
h = Hatari(snapshot=str(SNAP/snap), memsize_kb=2048)
try:
    h.set_cpuclock(16)
    v = h.vbl()
    hit = h.R/'hit.txt'; hit.write_text('\n'.join(['e VBL']+['m $'+d for d in dumps])+'\n')
    cmds = apply_cmds(live) + [ 'w $'+p.split('=')[0]+' '+' '.join('$%02x'%b for b in bytes.fromhex(p.split('=')[1])) for p in pokes] + [f'b pc = ${pcs} :trace :file {hit}']
    start=len(h._logtext())
    at_flip(h, cmds, v+100)
    t=time.time()
    while len(re.findall(r'#\d+ \(dec\)', h._logtext()[start:])) < n:
        time.sleep(0.5)
        if time.time()-t>600: break
    h.debug('b all',0.5)
    print(h._logtext()[start:])
finally:
    h.close()
