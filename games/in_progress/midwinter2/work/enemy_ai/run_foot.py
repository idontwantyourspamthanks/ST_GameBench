import sys
sys.path.insert(0,'work/enemy_ai'); sys.path.insert(0,'tools')
import trace_spawn as T
from live import *
hd=int(sys.argv[1]); out=sys.argv[2]
def setup(h):
    w16(h,0x6742,hd); w16(h,0x6294,hd); w16(h,0x764a,hd)
T.main(vbls=1200,gtype=5,outfile=out,setup=setup)
