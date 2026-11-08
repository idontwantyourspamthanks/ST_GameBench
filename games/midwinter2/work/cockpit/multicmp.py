"""Multi-flip pixel comparator: base vs live-patched, buffers ($60000/$70000) captured at several flip counts.

    python3 work/cockpit/multicmp.py <snapshot.sav> <live prefix from mw2patch.py live> <tag> 2,3,4,6,9,14,20,28,40,60

One Hatari pair per call (2 instances).  Keep the list short (<= ~10 flips): every pending :N breakpoint
slows the emulator (16 of them did not finish in 15 min).  Output under /tmp/mc/<tag>/{base,pat}."""
import sys,json,time,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from mw2harness import Hatari
from concurrent.futures import ThreadPoolExecutor
FLIP=0x26E98
def run(snap, live, ks, out, at_extra=400):
    h=Hatari(snapshot=snap)
    try:
        od=Path(out); od.mkdir(parents=True,exist_ok=True)
        cmds=[]
        if live:
            spec=json.loads(Path(live+'.json').read_text())
            cmds.append(f"loadbin {Path(live+'.img').resolve()} ${spec['img_base']:x}")
            for s in spec['sites']:
                new=bytes.fromhex(s['new'])
                cmds.append(f"w ${s['addr']:x} "+" ".join(f"${b:02x}" for b in new))
        for k in ks:
            cf=h.R/f"cap{k}.txt"
            cf.write_text(f"savebin {od}/b60_{k}.bin $60000 $8000\nsavebin {od}/b70_{k}.bin $70000 $8000\nsavebin {od}/ptr_{k}.bin $67a6 8\n")
            cmds.append(f"b pc = ${FLIP:x} :{k} :trace :once :file {cf}")
        app=h.R/"apply.txt"; app.write_text("\n".join(cmds)+"\n")
        v=h.vbl(); at=(v//100+4)*100
        start=len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${FLIP:x} :trace :once :file {app}")
        t=time.time()
        while not (od/f"ptr_{ks[-1]}.bin").exists():
            if time.time()-t>900: raise TimeoutError("cap")
            time.sleep(0.5)
        time.sleep(1.0)
    finally:
        h.close()
def md(od,k): return [hashlib.md5((Path(od)/f"{n}_{k}.bin").read_bytes()).hexdigest() for n in ('b60','b70')]
if __name__=='__main__':
    snap,live,tag=sys.argv[1],sys.argv[2],sys.argv[3]
    ks=[int(x) for x in sys.argv[4].split(',')]
    base=f"/tmp/mc/{tag}/base"; pat=f"/tmp/mc/{tag}/pat"
    with ThreadPoolExecutor(2) as ex:
        a=ex.submit(run,snap,None,ks,base); b=ex.submit(run,snap,live,ks,pat); a.result(); b.result()
    bad=[]
    for k in ks:
        ok = md(base,k)==md(pat,k)
        if not ok:
            nb=0
            for n in ('b60','b70'):
                x=(Path(base)/f"{n}_{k}.bin").read_bytes(); y=(Path(pat)/f"{n}_{k}.bin").read_bytes()
                nb+=sum(1 for i in range(len(x)) if x[i]!=y[i])
            bad.append((k,nb))
    print(Path(snap).stem, 'flips',ks, 'ALL IDENTICAL' if not bad else f'DIFF {bad}')
