import sys, os
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/'
sys.path.insert(0,G+'work/input'); sys.path.insert(0,G+'tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
import scripted2, cmp_sc
from nebulus import Nebulus
orig=scripted2.Nebulus
scripted2.Nebulus=lambda **kw: orig(**{**kw,'workdir':'/tmp/ned_eq'})
import nepatch as NP
patches=NP.chosen(['ed_overlay'],NP.load_patches()); ram=NP.predicted_stage2(); sites=NP.derive_sites(patches,ram)
cmds=[]; n=0
for p in patches:
    for a,d in p.blocks:
        open(f'/tmp/edblk{n}.bin','wb').write(d); cmds.append(f'loadbin /tmp/edblk{n}.bin ${a:x}'); n+=1
for a,o,nw in sites: cmds.append('w $%x '%a+' '.join('$%02x'%b for b in nw))
print(len(cmds),'live commands'); print('\n'.join(cmds[:3]))
ref,_=scripted2.run('eq_ref',[],duration=10)
spec={8:0x08,20:0x88,26:0x08,40:0x00,55:0x80,60:0x00,75:0x04,90:0x00}
ev=scripted2.build_script(ref,spec)
sf,st=scripted2.run('eq_stock',ev,caps=(1,4),live='none')
hf,ht=scripted2.run('eq_hook',ev,caps=(1,4),live=cmds)
print('loops',len(sf),len(hf))
cmp_sc.main('eq_stock','eq_hook')
cmp_sc.main2('eq_stock','eq_hook')
fs=cmp_sc.frames('eq_stock',st); fh=cmp_sc.frames('eq_hook',ht)
for k in sorted(fs): print('framebuffer event',k,'differing bytes, rows:',cmp_sc.pix_diff(fs[k],fh[k]) if k in fh else 'missing')
