import sys,re,time,json
from pathlib import Path
sys.path.insert(0,'/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
ROOT=Path('/home/ryan/Code/AtariST/midwinter2')
ABS_VBL=21600

DUMPS=["m $66e6 8","m $6742 2","m $6294 2","m $764a 2","m $674e 2","m $6740 2","m $6772 2","m $f984 2","m $b41c0 2","m $b41c4 8","m $b41cc 2"]

def run(snap, live, hit_cond, dumps, nhits, tag, apply_extra=(), timeout=900, after=3):
    h=Hatari(snapshot=snap)
    try:
        R=h.R
        hit=R/'hit.txt'; hit.write_text("\n".join(dumps)+"\n")
        cmds=[]
        if live:
            spec=json.loads(Path(live+'.json').read_text())
            cmds.append(f"loadbin {Path(live+'.img').resolve()} ${spec['img_base']:x}")
            for s in spec['sites']:
                new=bytes.fromhex(s['new'])
                cmds.append(f"w ${s['addr']:x} "+" ".join(f"${b:02x}" for b in new))
        cmds += list(dumps)
        cmds += list(apply_extra)
        cmds.append(f"b {hit_cond} :trace :file {hit}")
        app=R/'apply.txt'; app.write_text("\n".join(cmds)+"\n")
        v=h.vbl()
        start=len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {ABS_VBL} && pc = $26e98 :trace :once :file {app}")
        t=time.time()
        while True:
            txt=h._logtext()[start:]
            n=len(re.findall(r'^000066E6:',txt,re.M|re.I))
            if n>=nhits+1: break
            if time.time()-t>timeout: raise TimeoutError(txt[-1500:])
            time.sleep(0.4)
        h.debug("b all",0.5)
        txt=h._logtext()[start:]
        Path(f'/tmp/ti2/{tag}.log').write_text(txt)
        return txt
    finally:
        h.close()

def parse(txt):
    rows=[]; cur={}
    for m in re.finditer(r'^([0-9A-F]{8}):((?: [0-9a-f]{2})+)',txt,re.M|re.I):
        a=int(m.group(1),16); b=bytes.fromhex(m.group(2).replace(' ',''))
        if a in cur: rows.append(cur); cur={}
        cur[a]=b
    if cur: rows.append(cur)
    return rows

def sw(b): return int.from_bytes(b,'big',signed=True)
def uw(b): return int.from_bytes(b,'big')
def row(r):
    return dict(X=sw(r[0x66e6][0:4]),Y=sw(r[0x66e6][4:8]),H=uw(r[0x6742]),H94=uw(r[0x6294]),H4a=uw(r[0x764a]),lean=sw(r[0x674e]),d=sw(r[0x6740]),spd=uw(r[0x6772]),f984=sw(r[0xf984]),PH=uw(r[0xb41c0]) if 0xb41c0 in r else None)
