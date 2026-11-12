import sys
from watch import *
cond=sys.argv[1]; secs=int(sys.argv[2]); mask=int(sys.argv[3],16) if len(sys.argv)>3 else 0x40
live = live_build('t3', OUT/'patches', ['sw_head','sw_post','sw_ramp','sw_range','sw_probe2','p3b_pos','p3b_hdg','p3b_bank','p3b_alt','p3b_save','p3b_probe'])
pokes = [wb(0x6fba,150<<16,4), wb(0x6fb6,(-160&0xffff)<<16,4), wb(0xb4e00,mask,4)]
txt = watch(SNAP/'raid_speedboat_iquitos.sav','watch2',live,pokes,cond,['r','m $b42e6 2','m $66e6 8','m $6220 2'],secs=secs)
import re
i=txt.find('Wrote 4 \'b\' values starting from 0xb4e00')
print(txt[i:i+4000])
