import json,collections,struct
ram=open('work/amiga/ram_race_a.bin','rb').read()
R=json.load(open('work/amiga/inject_all.json'))
SIL=0x505a0
# instrument by sample ptr
inst={}
a=0x6436a
for n in range(39):
    w24,w26,w28,p1c,p10=struct.unpack('>HHHII',ram[a:a+14]); inst.setdefault(p1c,[]).append(n); a+=14
def an(sid):
    t0,rows=R[str(sid)]
    starts=[];per=collections.defaultdict(list);vol=collections.defaultdict(list)
    lc={}
    # first, find the time of the script's first real start (skip silence)
    for fr,v,h,t,pc,addr,sz,val in rows:
        if addr==0xdff096: continue
        if not 0xdff0a0<=addr<0xdff0e0: continue
        ch=(addr-0xdff0a0)//16; reg=(addr-0xdff0a0)%16
        if reg==0 and sz==4:
            lc[ch]=val
        elif reg==4 and pc==0x4ee16:
            if lc.get(ch) not in (None,SIL) : starts.append((round(t-t0,3),ch,lc[ch],val*2))
        elif reg==6 and pc==0x4edfc: per[ch].append((t,val))
        elif reg==8 and pc==0x4ee00: vol[ch].append((t,val))
    return starts,per,vol
out=[]
for sid in sorted(int(k) for k in R):
    st,per,vol=an(sid)
    chs=sorted(set(s[1] for s in st))
    desc=[]
    for ch in chs:
        v=[x for x in vol[ch]]; p=[x for x in per[ch]]
        aud=[t for t,x in v if x>0]
        dur=(max(aud)-min(aud)) if aud else 0
        ps=[x for t,x in p if x and any(abs(t-tt)<0.001 for tt,xx in v if xx>0)]
        starts=[s for s in st if s[1]==ch]
        uniq=collections.OrderedDict()
        for s in starts: uniq.setdefault((s[2],s[3]),[]).append(s[0])
        maxv=max([x for t,x in v] or [0])
        desc.append((ch,[(hex(k[0]),k[1],len(vv),vv[0]) for k,vv in uniq.items()],round(dur,2),(min(ps),max(ps)) if ps else None,maxv))
    out.append((sid,desc))
    print(sid,desc)
