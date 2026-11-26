"""Equivalence of normal play with the FULL default patch set (this release: cr_credit, ed_overlay, ni_jump, ni_latch, ni_shoot, ni_turn, nt_trainers)
against stock: same scripted input (work/input/scripted2.py), patch RAM blocks + sites applied at the first loop-top poll.
Known benign differences, by design: $33a38 (the game printer's text cursor, the Options-page hint line: see editor.md 11), the first turn loop's
pose (ni_turn: one loop earlier, see input.md 11.2) and the trainer/editor state words that are only nonzero after a key."""
import sys, types
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
        h.cmd(f'hatari-debug b pc = $3868e :once :trace :file {d}/apply.txt'); time.sleep(0.15)
"""+b)
m=types.ModuleType('scripted3'); m.__file__=G+'work/input/scripted3.py'; exec(compile(src,'scripted3','exec'),m.__dict__)
sys.modules['scripted3']=m; sys.modules['scripted2']=m
import cmp_sc
from nebulus import Nebulus
orig=m.Nebulus
m.Nebulus=lambda **kw: orig(**{**kw,'workdir':'/tmp/oddcore/eq98'})
import nepatch as NP
allp={p.name:p for p in NP.load_patches()}
def live_for(names):
    patches=[allp[n] for n in names]
    ram=NP.predicted_stage2(); sites=NP.derive_sites(patches,ram)
    cmds=[]; n=0
    for p in patches:
        for a_,d in p.blocks:
            open(f'/tmp/oddcore/blk98_{n}.bin','wb').write(d); cmds.append(f'loadbin /tmp/oddcore/blk98_{n}.bin ${a_:x}'); n+=1
    for a_,o,nw in sites:                   # the debugger takes at most 64 values per line: 32 bytes at a time
        for k in range(0, len(nw), 32):
            cmds.append('w $%x '%(a_+k)+' '.join('$%02x'%x for x in nw[k:k+32]))
    return cmds
names=[p.name for p in NP.load_patches() if p.default and p.name!='test_poke']
print('patches:', ', '.join(names))
spec={8:0x08,20:0x88,26:0x08,40:0x00,55:0x80,60:0x00,75:0x04,90:0x00}
for attempt in range(4):                    # the snapshot boot is occasionally too slow: retry the reference run
    ref,_=m.run('gc98_ref',[],duration=10)
    try:
        ev=m.build_script(ref,spec); break
    except StopIteration:
        print('reference run empty, retry', attempt+1, flush=True)
else:
    raise SystemExit('no reference flips')
sf,st=m.run('gc98_stock',ev,caps=(1,4),live='none')
print('stock loops',len(sf),flush=True)
base=[n for n in names if n not in ('ni_jump','ni_shoot','ni_turn')]
for tag,ns in (('nospeed',base), ('full',names)):
    cmds=live_for(ns)
    hf,ht=m.run('gc98_'+tag,ev,caps=(1,4),live=cmds)
    print(tag,'loops',len(hf),flush=True)
    cmp_sc.main('gc98_stock','gc98_'+tag); cmp_sc.main2('gc98_stock','gc98_'+tag)
    fs=cmp_sc.frames('gc98_stock',st); fh=cmp_sc.frames('gc98_'+tag,ht)
    for k in sorted(fs): print('framebuffer event',k,'differing bytes, rows:',cmp_sc.pix_diff(fs[k],fh[k]) if k in fh else 'missing')
cmp_sc.main('gc98_stock','gc98_full'); cmp_sc.main2('gc98_stock','gc98_full')
fs=cmp_sc.frames('gc98_stock',st); fh=cmp_sc.frames('gc98_full',ht)
for k in sorted(fs): print('framebuffer event',k,'differing bytes, rows:',cmp_sc.pix_diff(fs[k],fh[k]) if k in fh else 'missing')
