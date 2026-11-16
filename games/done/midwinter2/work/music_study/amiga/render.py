#!/usr/bin/env python3
"""Offline renderer of the Midwinter 2 (Amiga) music: interprets the song data exactly like the MWII driver
($57720 tick, flat dump operand addresses) -> per-tick Paula register stream -> WAV.

  render.py regs  TUNE [TICKS]            print the per-tick register writes
  render.py wav   TUNE OUT.wav [--rate R] [--ticks N] [--filter]    render one tune
  render.py all   OUTDIR [--rate R]       render tunes 1..17
  render.py loops                         per-tune loop lengths in ticks

Paula model: DMACON set/clear, LC/LEN latched at DMA start and re-latched at each end of cycle, PER (CCK, PAL 3546895 Hz),
VOL 0..64, ch0+ch3 left / ch1+ch2 right, signed 8 bit.  Tick = one VBL, PAL 49.9204 Hz (313 lines x 227 CCK).
"""
import sys, math, argparse, wave
import numpy as np
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/done/midwinter2/work/music_study/amiga')
from sim import Music
from mwmusic import D, B, u16
PAL_CCK=3546895.0; TICK_HZ=PAL_CCK/(227*313)
DATA=np.frombuffer(D,dtype=np.int8)

def sample_bytes(addr, nbytes):
    a=(addr & ~1)-B
    if a<0 or a+nbytes>len(DATA): out=np.zeros(nbytes,dtype=np.int8); return out
    return DATA[a:a+nbytes]

class Chan:
    def __init__(s):
        s.on=False; s.lc=0; s.len=1; s.per=1; s.vol=0
        s.ptr=0; s.left=0; s.phase=0.0; s.buf=None
    def start(s):
        s.cur=sample_bytes(s.lc, s.len*2 if s.len else 131072); s.phase=0.0
    def reload(s):
        s.cur=sample_bytes(s.lc, s.len*2 if s.len else 131072)

def apply_writes(chs, writes):
    for k,v in writes:
        if k=='DMACON':
            for c in range(4):
                if v&(1<<c):
                    if v&0x8000:
                        if not chs[c].on: chs[c].on=True; chs[c].start()
                    else: chs[c].on=False
        elif k.startswith('LC'): chs[int(k[2])].lc=v
        elif k.startswith('LEN'): chs[int(k[3])].len=v
        elif k.startswith('PER'): chs[int(k[3])].per=v
        elif k.startswith('VOL'): chs[int(k[3])].vol=min(v,64) if v<=64 else 64

def render_chan(ch, n, fs):
    out=np.zeros(n,dtype=np.float32)
    if not ch.on or ch.vol==0 and False: pass
    if not ch.on: return out
    per=max(ch.per,113)
    step=(PAL_CCK/per)/fs          # source bytes per output sample
    i=0
    while i<n:
        remain=(len(ch.cur)-ch.phase)/step
        m=int(min(n-i, max(1,math.ceil(remain))))
        idx=(ch.phase+np.arange(m)*step).astype(np.int64)
        ok=idx<len(ch.cur)
        seg=np.zeros(m,dtype=np.float32)
        seg[ok]=ch.cur[idx[ok]]
        out[i:i+m]=seg
        ch.phase+=m*step; i+=m
        if ch.phase>=len(ch.cur):
            ch.phase-=len(ch.cur)
            ch.reload()
    return out*(ch.vol/64.0)/128.0

def render(tune, ticks, fs=22050, filt=False):
    m=Music(); m.start(tune)
    chs=[Chan() for _ in range(4)]
    apply_writes(chs, m.out); m.out=[]
    L=[];R=[]
    acc=0.0
    stream=[]
    for t in range(ticks):
        m.out=[]; m.tick()
        stream.append(list(m.out))
        apply_writes(chs, m.out)
        n0=int(round(t*fs/TICK_HZ)); n1=int(round((t+1)*fs/TICK_HZ)); n=n1-n0
        s=[render_chan(c,n,fs) for c in chs]
        L.append(s[0]+s[3]); R.append(s[1]+s[2])
    L=np.concatenate(L); R=np.concatenate(R)
    if filt:   # Amiga LED filter: ~3.3 kHz, two cascaded one-poles (12 dB/oct), applied in the frequency domain
        fr=np.fft.rfftfreq(len(L),1/fs); H=1.0/(1+1j*fr/3300.0)**2
        L=np.fft.irfft(np.fft.rfft(L)*H,len(L)).astype(np.float32); R=np.fft.irfft(np.fft.rfft(R)*H,len(R)).astype(np.float32)
    return L,R,stream,m

def write_wav(path, L, R, fs):
    x=np.stack([L,R],1)*0.35
    x=np.clip(x,-1,1)
    pcm=(x*32767).astype('<i2')
    with wave.open(path,'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(fs); w.writeframes(pcm.tobytes())

def loop_ticks(tune, cap=20000):
    """ticks until every channel's pattern list has wrapped; LCM of per-channel wrap periods (the loop of the whole tune)"""
    m=Music(); m.start(tune)
    for t in range(cap):
        m.out=[]; m.tick()
        w={c:[e[2] for e in m.ev if e[0]=='WRAP' and e[1]==c and e[2]>0] for c in range(4)}
        if all(w[c] for c in range(4)): break
    per=[w[c][0] if w[c] else None for c in range(4)]
    from math import lcm
    return per, lcm(*[p for p in per if p])

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('cmd'); ap.add_argument('a',nargs='*')
    ap.add_argument('--rate',type=int,default=22050); ap.add_argument('--ticks',type=int,default=0)
    ap.add_argument('--filter',action='store_true')
    o=ap.parse_args()
    if o.cmd=='regs':
        tune=int(o.a[0]); nt=int(o.a[1]) if len(o.a)>1 else 20
        m=Music(); m.start(tune)
        print('reset:',m.out); 
        for t in range(nt):
            m.out=[]; m.tick(); print(t,m.out)
    elif o.cmd=='loops':
        for n in range(1,18):
            per,l=loop_ticks(n); print(n,per,'loop',l,'ticks',round(l/TICK_HZ,2),'s')
    elif o.cmd=='wav':
        tune=int(o.a[0]); per,l=loop_ticks(tune)
        nt=o.ticks or l
        L,R,_,_=render(tune,nt,o.rate,o.filter); write_wav(o.a[1],L,R,o.rate); print(o.a[1],nt,'ticks',round(nt/TICK_HZ,2),'s')
    elif o.cmd=='all':
        import os
        os.makedirs(o.a[0],exist_ok=True)
        for tune in range(1,18):
            per,l=loop_ticks(tune); nt=o.ticks or min(l,3000)
            L,R,_,_=render(tune,nt,o.rate,o.filter)
            p=f'{o.a[0]}/tune{tune:02d}.wav'; write_wav(p,L,R,o.rate); print(p,nt,round(nt/TICK_HZ,1),'s per',per,'loop',l)
