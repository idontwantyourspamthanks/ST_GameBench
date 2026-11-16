"""Extract the Amiga music data: tunes.json (tunes -> channel lists -> patterns -> events), instruments/*.raw (signed 8 bit)."""
import sys, json, os; sys.path.insert(0,'.')
from mwmusic import *
H3=0x89478
os.makedirs('extract/instruments',exist_ok=True)
tunes={}; pats={}; envs={}; insts={}
def env_read(a):
    p=a+4; w=[]
    while u16(p)!=0xff: w.append(u16(p)); p+=2
    return {'volsub':u16(a),'voladd':u16(a+2),'steps':w,'loop_last':True}
for n in range(1,18):
    t={'channels':[]}
    for c in range(4):
        p=u32(TUNE_TABLE+16*n+4*c); L=read_list(p)
        t['channels'].append(['%x'%x for x in L])
        for pp in L:
            if '%x'%pp in pats: continue
            ev,end=parse_pattern(pp)
            out=[]
            for e in ev:
                if e[0]=='N': out.append(['NOTE',e[1],e[2]])
                elif e[0] in('INSTR','ENV','GOTO'):
                    out.append([e[0],'%x'%e[3][0]])
                    if e[0]=='ENV': envs['%x'%e[3][0]]=env_read(e[3][0])
                    if e[0]=='INSTR': insts[e[3][0]]=1
                else: out.append([e[0]]+e[2])
            pats['%x'%pp]={'bytes':end-pp,'events':out}
    tunes[n]=t
ins={}
for a in sorted(insts):
    f=u16(a); lc=u32(a+2); ln=u16(a+6)*2; lc2=u32(a+8); ln2=u16(a+12)*2
    rec={'flag':f,'lc':lc,'len':ln,'lc2':lc2,'len2':ln2}
    if lc>=H3:
        off=(lc&~1)-H3
        data=bytes(D[(lc&~1)-B:(lc&~1)-B+ln])
        fn=f'extract/instruments/inst_{a:x}.raw'; open(fn,'wb').write(data); rec['file']=fn; rec['hunk3_off']=off
    else:
        rec['file']=None; rec['note']='code-hunk bytes (tune 13 only)'
        rec['bytes']=bytes(D[lc-B:lc-B+ln]).hex()
    rec['loop_is_silence']=(lc2==0x5c292)
    ins['%x'%a]=rec
json.dump({'tunes':tunes,'patterns':pats,'envelopes':envs,'instruments':ins},open('extract/tunes.json','w'),indent=0)
print(len(tunes),'tunes',len(pats),'patterns',len(envs),'envelopes',len(ins),'instruments')
