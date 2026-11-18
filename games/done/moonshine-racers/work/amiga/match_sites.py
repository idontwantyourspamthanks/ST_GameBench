import re,subprocess,sys
T='/home/ryan/Code/Amiga/gamebench/tools/m68dis.py'
def dis(f,a,b):
    return subprocess.run([sys.executable,T,f,'%x'%a,'--end','%x'%b],capture_output=True,text=True).stdout
AM='work/amiga/ram_race_a.bin'; ST='work/dumps/ram_race_start.bin'
am=open(AM,'rb').read(); st=open(ST,'rb').read()
def sites(buf,tgts):
    out=[]
    for tgt in tgts:
        pat=bytes.fromhex('4eb9')+tgt.to_bytes(4,'big')
        i=-1
        while True:
            i=buf.find(pat,i+1)
            if i<0: break
            out.append(i)
    return sorted(out)
asites=sites(am,[0x7b70]); ssites=sites(st,[0x7bb2,0x7bba])
def ops(f,a):
    t=dis(f,a-48,a+24)
    return set(re.findall(r'\$([0-9a-f]{3,4})\.w',t)), set(re.findall(r'jsr\s+\$([0-9a-f]+)\.l',t))
def shift(v): 
    x=int(v,16); return x+0x300 if 0xd00<=x<=0xfff else x
for a in asites:
    va,ja=ops(AM,a)
    best=[]
    for s in ssites:
        vs,js=ops(ST,s)
        sc=len({'%x'%shift(v) for v in va} & {v.lstrip('0') for v in vs})
        best.append((sc,s))
    best.sort(reverse=True)
    print(hex(a),sorted(va)[:8],'->',[(sc,hex(s)) for sc,s in best[:3]])
