"""Exact interpreter of the MWII music routine ($57720 tick, $5760c start).  Emits the Paula register write stream.
Writes are tuples (reg, value) with reg in 'LC','LEN','PER','VOL','DMACON' + channel; data read from the flat dump (operand space)."""
import struct, sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/done/midwinter2/work/music_study/amiga')
from mwmusic import D,B,u16,u32,TUNE_TABLE

IDLE_STREAM=0x58304; IDLE_LIST=0x582fc; SILENCE_ENV=0x5c3f4
import os
_LM=os.path.join(os.path.dirname(os.path.abspath(__file__)),'lowmem_a1200_ks31_hd.bin')
LOWMEM=open(_LM,'rb').read() if os.path.exists(_LM) else bytes(0x400)
def w16(a):
    # addresses below $400 are Amiga low memory (exec vectors, ExecBase at 4): read from the captured image.  The driver reads them
    # (a) for `move.w $0.l,..` (a bug: meant #0) and (b) as the volume envelope of a channel that never got an ENV command (tunes 3/11/13 ch1)
    if a<0x400: return (LOWMEM[a]<<8)|LOWMEM[a+1]
    return u16(a)

class Rec: pass
class Music:
    def __init__(self):
        self.out=[]; self.recs=[]; self.chg=0
        self.led=None; self.tickno=0; self.ev=[]
    def hw_reset(self):
        # $5750a
        o=self.out
        o.append(('DMACON',0x000f))
        for c in range(4): o.append((f'LC{c}',0))      # move.l $5c292.l -> memory contents (0), see notes
        for c in range(4): o.append((f'LEN{c}',0x10))
        for c in range(4): o.append((f'VOL{c}',0))
        for c in range(4): o.append((f'PER{c}',1))
    def start(self,tune):
        self.hw_reset()
        self.recs=[]
        ptrs=[u32(TUNE_TABLE+16*tune+4*i) for i in range(4)]
        for c in range(4):
            r=Rec()
            r.ch=c; r.id=c+1; r.cnt=0; r.state=0; r.per=0; r.slide=0; r.step=0; r.target=0; r.delay=0
            r.vib=0; r.env=0; r.ev=IDLE_STREAM; r.lst=IDLE_LIST; r.lst0=ptrs[c]; r.env0=0
            r.lc=0; r.len=0; r.lc2=0; r.len2=0; r.vcnt=0; r.vrel=0; r.vup=0; r.vdn=0; r.vdel=0; r.vdelrel=0
            r.volsub=0; r.voladd=0; r.voladdf=0; r.inst=0
            self.recs.append(r)
    # --- helpers
    def dma(self,c,val): self.out.append(('DMACON',val))
    def tick(self):
        for r in self.recs: self.chan(r)
        self.tickno+=1
    def chan(self,r):
        c=r.ch; mask=1<<c; d1=0x8200|mask; d5=mask
        o=self.out
        if r.id==0: return
        if r.cnt==0:
            self.new_event(r,c,d1); return
        if r.cnt==1:
            if r.state!=0: o.append(('DMACON',d5))
            r.cnt-=1
            self.proc(r,c); return
        if r.state==3:
            o.append((f'LC{c}',r.lc2)); o.append((f'LEN{c}',r.len2))
            r.cnt=(r.cnt-1)&0xffff; r.state=1
            self.proc(r,c); return
        r.cnt=(r.cnt-1)&0xffff
        self.proc(r,c)
    def proc(self,r,c):
        o=self.out; self.chg=0
        d2=r.per
        if r.slide!=0:
            if r.delay!=0: r.delay-=1
            else:
                self.chg+=1; d3=r.step; d4=r.target
                if r.slide==1:
                    d2=(d2+d3)&0xffff
                    if not (d4>=d2): d2=d4; r.slide=0
                else:
                    d2=(d2-d3)&0xffff
                    if not (d4<d2): d2=d4; r.slide=0
        if r.vib!=0:
            if r.vdel!=0: r.vdel-=1
            elif r.vcnt!=0: r.vcnt-=1
            else:
                r.vcnt=r.vrel; self.chg+=1
                if r.vib<3:
                    d2=(d2-r.vdn)&0xffff; r.vib+=1
                else:
                    d2=(d2+r.vup)&0xffff; r.vib+=1
                    if r.vib==5: r.vib=1
        if self.chg:
            r.per=d2; o.append((f'PER{c}',d2))
        self.vol(r,c)
    def vol(self,r,c):
        o=self.out
        # path A never taken ($5736c/$5736e are never written): always B
        a1=r.env
        if w16(a1)==0xff:
            a1-=2; o.append((f'VOL{c}',w16(a1))); a1+=2
        elif r.voladdf==1:
            d=(w16(a1)+r.voladd)&0xffff; a1+=2; o.append((f'VOL{c}',d))
        else:
            o.append((f'VOL{c}',w16(a1))); a1+=2
        r.env=a1
    def new_event(self,r,c,d1):
        o=self.out
        r.voladdf=w16(0)
        a1=r.ev
        while True:
            d0=w16(a1); a1+=2
            if d0>0x64:
                r.per=d0; o.append((f'PER{c}',d0))
                r.cnt=(w16(a1)-1)&0xffff; a1+=2
                r.ev=a1
                r.env=r.env0
                r.vdel=r.vdelrel
                if r.vib!=0: r.vib=1
                if r.state==0:
                    o.append(('DMACON',d1))
                else:
                    r.state=3; o.append((f'LC{c}',r.lc)); o.append((f'LEN{c}',r.len)); o.append(('DMACON',d1))
                self.vol(r,c); return
            # command
            if d0==0x00:
                self.ev.append(('HALT',r.ch,self.tickno)); return                                   # nop/rts: stream parked, ev not stored
            elif d0==0x04:
                a3=u32(a1); a1+=4; r.inst=a3
                f=w16(a3)
                if f==0:
                    r.state=f; r.lc=u32(a3+2); r.len=w16(a3+6)
                    o.append((f'LC{c}',r.lc)); o.append((f'LEN{c}',r.len))
                else:
                    r.state=f; r.lc=u32(a3+2); r.len=w16(a3+6); r.lc2=u32(a3+8); r.len2=w16(a3+12)
            elif d0==0x08:
                p=r.lst
                if u32(p)==0:
                    self.ev.append(('WRAP',r.ch,self.tickno)); r.lst=r.lst0; p=r.lst
                r.lst+=4
                a1=u32(p)
            elif d0==0x0c:
                a4=u32(a1); a1+=4
                r.volsub=w16(a4); r.voladd=w16(a4+2); r.env0=a4+4
            elif d0==0x10:
                r.slide=w16(a1); r.step=w16(a1+2); r.target=w16(a1+4); r.delay=w16(a1+6); a1+=8
            elif d0==0x14:
                r.vib=1; r.vcnt=w16(a1); r.vrel=w16(a1+2); r.vup=w16(a1+4); r.vdn=w16(a1+6); r.vdel=w16(a1+8); r.vdelrel=w16(a1+10); a1+=12
            elif d0==0x18: r.slide=0
            elif d0==0x1c: r.vib=0
            elif d0==0x20:
                r.cnt=(w16(a1)-1)&0xffff; self.ev.append(('REST',r.ch,self.tickno,w16(a1))); a1+=2; r.ev=a1; r.env=SILENCE_ENV; o.append((f'VOL{c}',0))
                self.vol(r,c); return
            elif d0 in (0x24,0x28,0x2c-0x2c+0x24):
                self.chan_end(r,c); return
            elif d0==0x2c: self.led='on'
            elif d0==0x30: self.led='off'
            elif d0==0x34: r.voladdf=1
            elif d0==0x38:
                self.ev.append(('GOTO',r.ch,self.tickno)); a1=u32(a1)
            else: raise ValueError(hex(d0))
    def chan_end(self,r,c):
        # $57dce -> default case (ids 1..4) = $57de6: DMA off for this channel, PER of channel 0 := 1, VOL of this channel := 0
        o=self.out; self.ev.append(('END',c,self.tickno))
        o.append(('DMACON',1<<c)); o.append(('PER0',1)); o.append((f'VOL{c}',0))
