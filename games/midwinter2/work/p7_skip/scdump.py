import sys, time
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
import gate
snap=sys.argv[1]; prefix=sys.argv[2]; pokes=sys.argv[3]; flips=[int(x) for x in sys.argv[4].split(',')]
h=Hatari(snapshot=snap,memsize_kb=1024)
try:
    v=h.vbl(); at=(v//100+4)*100
    cmds=gate.live_cmds(prefix)
    od=Path('/tmp/sk/scd'); import shutil; shutil.rmtree(od,ignore_errors=True); od.mkdir(exist_ok=True)
    for k in flips:
        cf=h.R/f'c{k}.txt'; cf.write_text(f"savebin {od}/sc_{k}.bin $b6040 $138\nsavebin {od}/d_{k}.bin $b6000 $40\nsavebin {od}/p_{k}.bin $66e6 8\nsavebin {od}/h_{k}.bin $6742 2\n")
        cmds.append(f"b pc = $26e98 :{k} :trace :once :file {cf}")
    pf=h.R/'p.txt'; pf.write_text(pokes.replace(';','\n')+'\n'); cmds.append(f"b pc = $26e98 :2 :trace :once :file {pf}")
    app=h.R/'apply.txt'; app.write_text('\n'.join(cmds)+'\n')
    h.cmd(f"hatari-debug b VBL > {at} && pc = $26e98 :trace :once :file {app}")
    t=time.time()
    while not (od/f'd_{flips[-1]}.bin').exists() and time.time()-t<200: time.sleep(0.5)
    time.sleep(1)
finally:
    h.close()
import struct
import sys
sys.path.insert(0,'.')
SCL=104
def words(b): return [int.from_bytes(b[i:i+2],'big') for i in range(0,len(b),2)]
names=['$6220','$66e0','$66e6h','$66e6l','$66eah','$66eal','$670a','$670c','$6f78','$67be','$6806','$6808']+[f'$763e+{2*i}' for i in range(18)]+['$17fc4','$18768']+[f'$18556+{2*i}' for i in range(6)]+[f'$18772+{2*i}' for i in range(4)]+['$18784','$18786','$18788','$18796','$18798','$1879a','$53ac','$53ae','$53da','$53dc']
prev=None
for k in flips:
    raw=(od/f'sc_{k}.bin').read_bytes()
    stage=words(raw[0xd0:0xd0+104]) if len(raw)>=0xd0+104 else []
    sc0=words(raw[0:104]); sc1=words(raw[104:208])
    print(k,'stage',len(stage),'pos',(od/f'p_{k}.bin').read_bytes().hex(),'hdg',(od/f'h_{k}.bin').read_bytes().hex(), gate.counters((od/f'd_{k}.bin').read_bytes()))
    for nm,x in (('SC0',sc0),('SC1',sc1)):
        for i,(a,b) in enumerate(zip(stage,x)):
            if a!=b: print('   ',nm,'differs from stage at',names[i],hex(b),'vs stage',hex(a))
    if prev:
        for i,(a,b) in enumerate(zip(prev,stage)):
            if a!=b: print('   stage changed',names[i],hex(a),'->',hex(b))
    prev=stage
