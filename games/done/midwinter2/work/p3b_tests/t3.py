import sys,os; sys.path.insert(0,'/tmp/p5')
from lib import *
# usage: t3.py label live mode(M|J|K) arg   (M: dx ; J/K: key hold_s) ; BP env = breakpoint addr
label,live,mode=sys.argv[1],sys.argv[2],sys.argv[3]
bp=int(os.environ.get('BP','31594'),16)
live='/tmp/p3b/live/'+live
extra=['--joy1','keys'] if mode=='J' else []
h=Hatari(snapshot=SNAP,extra=extra)
try:
    apply_live(h,live)
    if mode=='J': h.debug("w $eb76 $ff $ff $00 $00 $00 $00",0.5)
    elif mode=='K': h.debug("w $eb76 $00 $00 $ff $ff $00 $00",0.5)
    if os.environ.get('TYPE'): h.debug('w $6220 $00 $%02x'%int(os.environ['TYPE']),0.5)
    if os.environ.get('THR'): h.debug('w $6fba $01 $42 $00 $00',0.5)
    time.sleep(2)
    start_log(h,addrs=(0x6742,0x6766,0x6fb6,0x6220,0x66e6,0xb42e6),bp=bp)
    time.sleep(1.5)
    if mode=='M':
        h.rel(int(sys.argv[4]),0); time.sleep(8)
    else:
        key=sys.argv[4]; hold=float(sys.argv[5])
        h._xdo('keydown','--window',h.win,key); time.sleep(hold); h._xdo('keyup','--window',h.win,key); time.sleep(4)
    rows=stop_log(h)
    print('==',label,mode,sys.argv[4:],'bp',hex(bp))
    prev=None
    for r in rows:
        hd=r.get(0x6742)
        if hd is None: continue
        if not os.environ.get('ALLPH') and r.get(0xb42e6) not in (None,0,5): continue
        d='' if prev is None else f' d={sgn((hd-prev)&0xffff)}'
        X=r.get(0x66e6|0x1000000)
        print(f" vbl {r['vbl']} heading {hd:4d}{d} $6766={sgn(r.get(0x6766,0))} $6fb6hi={sgn(r.get(0x6fb6,0))} type={r.get(0x6220)} X={X} PH={r.get(0xb42e6)}")
        prev=hd
finally:
    h.close()
