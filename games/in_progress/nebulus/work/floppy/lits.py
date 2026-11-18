import sys,re; sys.path.insert(0,'.')
from sitecmp import *
n,flr,bad=compare()
P=NEB/'patches'
lo,hi=0x33b1c,0x75720
res={}
for fn in ('ed_editor.s','nt_keys.s','ni_latch.s','cr_credit.s','nt_tmrhook.s','nt_enhook.s'):
    for ln,line in enumerate((P/fn).read_text().splitlines(),1):
        code=line.split(';')[0]
        for m in re.finditer(r'\$([0-9a-fA-F]{5,6})\b',code):
            v=int(m.group(1),16)
            if lo<=v<hi: res.setdefault(v,[]).append(f'{fn}:{ln}')
print(len(res),'distinct image literals')
for v in sorted(res):
    p=v-BASE; f=mp(p)
    if f is None: print('%x UNMAPPED'%v,res[v][:2]); continue
    a=bytes(n[p:p+16]); b=bytes(flr[f:f+16])
    st='same' if a==b else 'DIFF'
    print('%x -> %x %s %s'%(v,f+BASE,st,res[v][:3]), '' if st=='same' else (a.hex()+' | '+b.hex()))
