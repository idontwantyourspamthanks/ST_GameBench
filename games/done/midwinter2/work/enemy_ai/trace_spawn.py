"""Scenario: pull a Lobos garrison ($b3aa list, record at $c6fc+16*idx) next to the player so the
game's own spawner ($34adc) creates a hostile NPC, then log NPC slots 0..NS-1 plus counters at every
state dispatch ($35b0a).  Garrison record: +0 x(map) +2 y(map) +4 strength +6 threshold +8 deployed
+$a WORD type (0-based; the low byte is +$b) +$c flags (bit7 active) +$e losses."""
import sys
sys.path.insert(0,'work/enemy_ai'); sys.path.insert(0,'tools')
from live import *

NS=5
def main(vbls=1500, gtype=0, outfile='/tmp/ai/spawn_trace.txt', dx=14, dy=3, gidx=4, pokes=None, setup=None, snap='ingame_lobos_foot', ns=NS, pre=None):
    h=start(snap)
    try:
        time.sleep(3)
        px=int.from_bytes(mem(h,0x66bc,2),'big'); py=int.from_bytes(mem(h,0x66be,2),'big')
        g=0xc6fc+0x10*gidx
        w16(h,g,px+dx, py+dy)
        h.debug('w $%x $00 $%02x'%(g+10,gtype),0.15)
        for a,v in (pokes or []):
            w16(h,a,v)
        if setup: setup(h)
        cf='/tmp/ai/c1.txt'
        cmds=''.join('m $%x 66\n'%(0x3532+0x42*i) for i in range(ns))+'m $6820 8\nm $6282 2\nm $66e6 8\nm $764c 2\ne VBL\n'
        open(cf,'w').write(cmds)
        h.debug('b all',0.3)
        if pre: pre(h)
        n0=len(h._logtext())
        h.cmd('hatari-debug b pc = $35b0a :trace :file %s'%cf)
        v=h.vbl()
        h.cmd('hatari-debug b VBL > %d :trace :once'%(v+vbls))
        t=time.time()
        while 'Removed CPU breakpoint' not in h._logtext()[n0:]:
            time.sleep(1)
            if time.time()-t>900: break
        open(outfile,'w').write(h._logtext()[n0:])
        h.debug('b all',0.3)
    finally:
        h.close()

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--type',type=int,default=0); ap.add_argument('--vbls',type=int,default=1500)
    ap.add_argument('--out',default='/tmp/ai/spawn_trace.txt'); ap.add_argument('--dx',type=int,default=14); ap.add_argument('--dy',type=int,default=3)
    ap.add_argument('--g',type=int,default=4)
    a=ap.parse_args()
    main(a.vbls,a.type,a.out,a.dx,a.dy,a.g)
