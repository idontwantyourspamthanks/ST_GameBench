import sys
sys.path.insert(0,'work/enemy_ai'); sys.path.insert(0,'tools')
import trace_spawn as T
from live import *
which=sys.argv[1]; out=sys.argv[2]
if which=='raid':
    # zeppelin raid timer: $68fa enable, $68fc count, $68fe countdown, $6900 reload
    def setup(h):
        w16(h,0x68fa,1); w16(h,0x68fc,2); w16(h,0x68fe,1); w16(h,0x6900,4)
    # put the garrison far away so only the raid spawns
    T.main(vbls=900,gtype=0,outfile=out,setup=setup,dx=300,dy=300)
elif which=='hit100':
    def setup(h):
        h.debug('w $3283 $64',0.15)
    T.main(vbls=2200,gtype=0,outfile=out,setup=setup)
elif which=='sub':
    T.main(vbls=500,gtype=9,outfile=out)
elif which=='boat':
    T.main(vbls=500,gtype=6,outfile=out)
elif which=='heli':
    T.main(vbls=900,gtype=13,outfile=out)
