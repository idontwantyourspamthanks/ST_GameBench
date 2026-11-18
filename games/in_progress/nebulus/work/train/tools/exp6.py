import sys
from nt import *
snap=sys.argv[1]; enc=sys.argv[2]; wd='/tmp/strun-nt6'+enc
h=Nebulus(snapshot=snap,workdir=wd)
def M(a,n): return h.debug(f"m ${a:x} {n}",0.5).strip().splitlines()[-1]
try:
    time.sleep(3)
    print('before: ',M(0x3b0a4,12)); print('        ',M(0x3792c,6)); print('        ',M(0x3398c,8)); print('        ',M(0x3ad98,6),'vbl',h.vbl())
    if enc=='word':
        cmds=['w $3b0aa $6000','w $3792c $4e75','w $3398c 0','w $3398e 0','w $33990 0','w $33992 0']
    else:
        cmds=['w $3b0aa $60','w $3792c $4e $75','w $3398c 0 0 0 0 0 0 0 0']
    for c in cmds: print('cmd',c, '->', h.debug(c,0.4).strip().replace('\n',' | ')[-90:])
    print('after:  ',M(0x3b0a4,12)); print('        ',M(0x3792c,6)); print('        ',M(0x3398c,8))
    v0=h.vbl()
    while h.vbl()-v0<700:
        print('vbl',h.vbl(),'timer',M(0x3ad98,6),'| states',M(0x3398c,8),'| p-state',M(0x33a20,2), flush=True)
        time.sleep(1.5)
finally:
    h.close()
