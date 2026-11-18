#!/usr/bin/env python3
"""Bucket a Hatari `profile save` file by function (jsr/bsr/jmp-abs targets in the Nebulus game image $33b00..$76000).
   usage: nprof.py DUMP PROF VBLS [--top N] [--flip HEX]"""
import re, sys, bisect, struct, argparse
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
import m68dis
ap=argparse.ArgumentParser(); ap.add_argument('dump'); ap.add_argument('prof'); ap.add_argument('vbls',type=int)
ap.add_argument('--top',type=int,default=25); ap.add_argument('--flip',default='3868a')
a=ap.parse_args()
ram=open(a.dump,'rb').read()
m68dis.CODE_LO,m68dis.CODE_HI=0x33b00,0x76000
t=set(m68dis.call_targets(ram))
for x in range(0x33b00,0x76000-6,2):
    if struct.unpack_from('>H',ram,x)[0]==0x4EF9:
        y=struct.unpack_from('>I',ram,x+2)[0]
        if 0x33b00<=y<0x76000 and y%2==0: t.add(y)
tg=sorted(t)
prof={}
for ln in open(a.prof):
    m=re.match(r'^\$([0-9a-f]+)\s.*?([\d.]+)% \((\d+), (\d+),',ln)
    if m: prof[int(m.group(1),16)]=(int(m.group(3)),int(m.group(4)))
tot=sum(c for n,c in prof.values())
flip=int(a.flip,16)
frames=prof.get(flip,(0,0))[0]
W=tot  # window = profiled cycles (profile starts a little after the breakpoint is armed)
print(f'profiled window {W} cycles = {W/160256:.1f} VBL (8MHz, 50Hz); flip calls {frames} -> {W/160256/max(frames,1):.2f} VBL/frame, {frames*50/(W/160256):.1f} fps')
b={}
for ad,(n,c) in prof.items():
    i=bisect.bisect_right(tg,ad)-1
    f=tg[i] if i>=0 and ad>=0x33b00 else ad
    e=b.setdefault(f,[0,0,0]); e[0]+=c; e[1]+=n
print('func      cycles   %win   cyc/frame  insns')
for f,(c,n,_) in sorted(b.items(),key=lambda kv:-kv[1][0])[:a.top]:
    print(f'{f:06x} {c:10d} {100*c/W:5.1f}%  {c/max(frames,1):10.0f} {n:9d}  entry_count={prof.get(f,(0,0))[0]}')
