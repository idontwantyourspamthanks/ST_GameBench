"""headscan.py hdg1,hdg2,.. : for each heading poked into the unpatched standing snapshot, capture window frames at several flips and report identity + screenshot."""
import sys, time, hashlib
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
FLIP=0x26E98
snap='/home/ryan/Code/AtariST/midwinter2/work/snapshots/1mb_ingame_foot.sav'
hdgs=[int(x) for x in sys.argv[1].split(',')]
ks=[6,7,20,21,41]
for hd in hdgs:
    h = Hatari(snapshot=snap, memsize_kb=1024)
    try:
        out=Path(f'/tmp/hs_{hd}'); out.mkdir(exist_ok=True)
        hi,lo=(hd>>8)&255,hd&255
        for a in ('$6742','$6294','$764a'):
            h.debug(f"w {a} ${hi:02x} ${lo:02x}",0.2)
        cmds=[]
        for k in ks:
            cf=h.R/f'c{k}.txt'
            cf.write_text(f"savebin {out}/b60_{k}.bin $60000 $8000\nsavebin {out}/b70_{k}.bin $70000 $8000\nsavebin {out}/p_{k}.bin $67a6 8\n")
            cmds.append(f"b pc = ${FLIP:x}{(' :%d'%k) if k>1 else ''} :trace :once :file {cf}")
        app=h.R/'apply.txt'; app.write_text('\n'.join(cmds)+'\n')
        h.cmd(f"hatari-debug b pc = ${FLIP:x} :trace :once :file {app}")
        t=time.time()
        while not (out/f'p_{ks[-1]}.bin').exists() and time.time()-t<300: time.sleep(0.5)
        time.sleep(1)
        h.shot(f'/tmp/hs_{hd}.png')
        md=lambda p:hashlib.md5(p.read_bytes()[58*160:32000]).hexdigest()[:8]
        res=[]
        for k in ks:
            ptr=(out/f'p_{k}.bin').read_bytes()
            res.append((k,md(out/f'b60_{k}.bin'),md(out/f'b70_{k}.bin'),ptr.hex()))
        print(hd,[(r[0],r[1],r[2]) for r in res])
        print('  distinct window images:',len({r[1] for r in res}|{r[2] for r in res}))
    finally:
        h.close()
