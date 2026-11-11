"""Check the d1 clobber in state 4 ($35d36): tank placed 6000 units dead ahead of itself's line to the player."""
import sys
sys.path.insert(0,'work/enemy_ai'); sys.path.insert(0,'tools')
import trace_spawn as T
from live import *
dist=int(sys.argv[1]); out=sys.argv[2]
def setup(h):
    x=25600+dist
    bs=lambda v,n: ' '.join('$%02x'%((v>>(8*(n-1-i)))&255) for i in range(n))
    lines=['w $%x %s'%(0x3532+0x6,bs(x,4)),'w $%x %s'%(0x3532+0xa,bs(25600,4)),'w $%x %s'%(0x3532+0x1a,bs(0xc000,2)),'w $%x %s'%(0x3532+0x1c,bs(0,2)),
           'w $%x %s'%(0x3532+0x3a,bs(4,2)),'w $%x %s'%(0x3532+0x36,bs(30,2)),'w $%x %s'%(0x3532+0x38,bs(0,2)),'w $%x %s'%(0x3532+0x18,bs(290,2)),'w $%x %s'%(0x3532+0x3e,bs(12,2)),
           'w $%x %s'%(0x3532+0x22,bs(25600,4)),'w $%x %s'%(0x3532+0x26,bs(25600,4))]
    open('/tmp/ai/poke.txt','w').write('\n'.join(lines)+'\n')
def pre(h):
    h.cmd('hatari-debug b pc = $35b0a :trace :once :file /tmp/ai/poke.txt')
    time.sleep(0.3)
T.main(vbls=300,gtype=0,outfile=out,setup=setup,pre=pre)
