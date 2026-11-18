import sys, types
PATCHES=sys.argv[1].split(',')
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/'
sys.path.insert(0,G+'work/input'); sys.path.insert(0,G+'tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
src=open(G+'work/input/scripted2.py').read()
a="        for c in (LIVE[live] if isinstance(live, str) else live):\n            h.debug(c, 0.2)\n        h.debug('b all', 0.2)\n"
assert a in src
src=src.replace(a,"        h.debug('b all', 0.2)\n")
b="        for pcx in ('$39fc8', '$39ffc', '$3a2f8'):"
assert b in src
src=src.replace(b,"""        cmds = (LIVE[live] if isinstance(live, str) else live) or ['m $0 2']
        (d / 'apply.txt').write_text('\\n'.join(cmds) + '\\n')
        h.cmd(f'hatari-debug b pc = $3dcf4 :once :trace :file {d}/apply.txt'); time.sleep(0.15)
"""+b)
m=types.ModuleType('scripted3'); m.__file__=G+'work/input/scripted3.py'; exec(compile(src,'scripted3','exec'),m.__dict__)
sys.modules['scripted3']=m; sys.modules['scripted2']=m
import cmp_sc
from nebulus import Nebulus
orig=m.Nebulus
m.Nebulus=lambda **kw: orig(**{**kw,'workdir':'/tmp/strun-ikbd-eq'})
import nepatch as NP
patches=NP.chosen(PATCHES,NP.load_patches()); ram=NP.predicted_stage2(); sites=NP.derive_sites(patches,ram)
cmds=[]; n=0
for p in patches:
    for a_,d in p.blocks:
        open(f'/tmp/edblk{n}.bin','wb').write(d); cmds.append(f'loadbin /tmp/edblk{n}.bin ${a_:x}'); n+=1
for a_,o,nw in sites:
    if len(nw) > 16:
        open(f'/tmp/ikst{a_:x}.bin','wb').write(bytes(nw)); cmds.append(f'loadbin /tmp/ikst{a_:x}.bin ${a_:x}')
    else:
        cmds.append('w $%x '%a_+' '.join('$%02x'%x for x in nw))
ref,_=m.run('iq_ref',[],duration=10)
spec={8:0x08,20:0x88,26:0x08,40:0x00,55:0x80,60:0x00,75:0x04,90:0x00}
ev=m.build_script(ref,spec)
sf,st=m.run('iq_stock',ev,caps=(1,4),live='none')
hf,ht=m.run('iq_hook',ev,caps=(1,4),live=cmds)
print('loops',len(sf),len(hf))
cmp_sc.main('iq_stock','iq_hook'); cmp_sc.main2('iq_stock','iq_hook')
fs=cmp_sc.frames('iq_stock',st); fh=cmp_sc.frames('iq_hook',ht)
for k in sorted(fs): print('framebuffer event',k,'differing bytes, rows:',cmp_sc.pix_diff(fs[k],fh[k]) if k in fh else 'missing')
