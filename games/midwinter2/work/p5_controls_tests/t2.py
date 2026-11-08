import sys; sys.path.insert(0,'/tmp/p5')
from lib import *
# usage: t2.py label live|none mode(J|K) key hold_s
label,live,mode,key,hold=sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],float(sys.argv[5])
live=None if live=='none' else live
extra=['--joy1','keys'] if mode=='J' else []
h=Hatari(snapshot=SNAP,extra=extra)
try:
    if live: apply_live(h,live)
    if mode=='J': h.debug("w $eb76 $ff $ff $00 $00 $00 $00",0.5)
    else: h.debug("w $eb76 $00 $00 $ff $ff $00 $00",0.5)
    print(h.debug("m $eb76 6",0.5).strip().splitlines()[-1])
    import os
    if os.environ.get('TYPE'): h.debug('w $6220 $00 $%02x'%int(os.environ['TYPE']),0.5)
    if os.environ.get('TYPE'): print('type after poke:',h.debug('m $6220 2',0.5).strip().splitlines()[-1])
    time.sleep(2)
    start_log(h, addrs=(0x6742,0x6766,0x6fb6,0x6220))
    time.sleep(1.5)
    h._xdo('keydown','--window',h.win,key)
    t=time.time(); time.sleep(hold)
    h._xdo('keyup','--window',h.win,key)
    time.sleep(4)
    if os.environ.get('TYPE'): print('type after:',h.debug('m $6220 2',0.5).strip().splitlines()[-1])
    rows=stop_log(h)
    print('==',label,mode,key,'hold',hold,'s')
    prev=None
    for r in rows:
        hd=r.get(0x6742)
        if hd is None: continue
        d='' if prev is None else f' d={sgn((hd-prev)&0xffff)}'
        print(f" vbl {r['vbl']} heading {hd:4d}{d} $6766={sgn(r.get(0x6766,0))} $6fb6hi={sgn(r.get(0x6fb6,0))} type={r.get(0x6220)}")
        prev=hd
finally:
    h.close()
