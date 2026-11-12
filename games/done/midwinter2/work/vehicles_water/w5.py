import sys,re
from watch import *
snap=sys.argv[1]; secs=int(sys.argv[2]); mask=int(sys.argv[3],16); yc=int(sys.argv[4]); xc=int(sys.argv[5]); patched=sys.argv[6]=='1'
pcs=sys.argv[7].split(',')
pl=['sw_head','sw_post','sw_ramp','sw_range','sw_probe2','sw_depth','sw_tail','p3b_pos','p3b_hdg','p3b_bank','p3b_alt','p3b_save','p3b_probe']
live = live_build('t3', OUT/'patches', pl) if patched else None
pokes = [wb(0x6fba,(yc&0xffff)<<16,4), wb(0x6fb6,(xc&0xffff)<<16,4)]+([wb(0xb4e00,mask,4),'w $b4e04 $00 $01'] if patched else [])
bps=[('pc = $%s'%p,['m $b9000 2' if False else 'e %d'%i]) for i,p in enumerate(pcs)]
# use e <n> as marker: prints "#n"
txt = watch(SNAP/snap,'w5',live,pokes,bps[0][0],bps[0][1]+['m $b42e6 2'],secs=secs,extra_bps=[(c,m+['m $b42e6 2']) for c,m in bps[1:]])
out=[]
for m in re.finditer(r'^(?:= .*, #(\d+) \(dec\)|000B42E6: ([0-9a-f]{2}) ([0-9a-f]{2}))',txt,re.M|re.I):
    if m.group(1) is not None: cur=m.group(1)
    else: out.append('%s:PH%d'%(cur,int(m.group(2)+m.group(3),16)))
print(' '.join(out))
