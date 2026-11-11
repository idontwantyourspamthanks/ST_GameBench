import sys,re,collections
from watch import *
snap=sys.argv[1]; secs=int(sys.argv[2]); mask=int(sys.argv[3],16); yc=int(sys.argv[4]); xc=int(sys.argv[5]); patched=sys.argv[6]=='1'
pl=['sw_head','sw_post','sw_ramp','sw_range','sw_probe2','p3b_pos','p3b_hdg','p3b_bank','p3b_alt','p3b_save','p3b_probe']
live = live_build('t3', OUT/'patches', pl) if patched else None
pokes = [wb(0x6fba,(yc&0xffff)<<16,4), wb(0x6fb6,(xc&0xffff)<<16,4)]+([wb(0xb4e00,mask,4)] if patched else [])
txt = watch(SNAP/snap,'rng_'+sys.argv[6],live,pokes,'pc = $26fd0',['m a7 16','m $b42e6 2'],secs=secs,extra_bps=[('pc = $31486',['m $b42e6 2','m $6220 2'])])

import collections
seq=[]
for m in re.finditer(r'^([0-9A-F]{8}): ((?:[0-9a-f]{2} ){2,16})',txt,re.M):
    a=int(m.group(1),16); b=bytes.fromhex(m.group(2).replace(' ',''))
    if a==0xb42e6: ph=int.from_bytes(b[:2],'big')
    elif a==0x6220: seq.append('|%d'%ph)
    elif a>=0x7000 and len(b)>=16:
        r1=int.from_bytes(b[0:4],'big'); r3=int.from_bytes(b[8:12],'big')
        seq.append(hex(r1) if r1!=0x26fbc else 'w'+hex(int.from_bytes(b[12:16],'big')))
print(len(seq)); print(' '.join(seq))
