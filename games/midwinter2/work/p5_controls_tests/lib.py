import sys, time, re, json
from pathlib import Path
sys.path.insert(0,'/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
ROOT=Path('/home/ryan/Code/AtariST/midwinter2')
SNAP=str(ROOT/'work/snapshots/1mb_ingame_walking.sav')

def apply_live(h, prefix, extra_cmds=()):
    """apply a live patch set at the next flip (same mechanism as capture_frames)"""
    cmds=[]
    if prefix:
        spec=json.loads(Path(prefix+'.json').read_text())
        cmds.append(f"loadbin {Path(prefix+'.img').resolve()} ${spec['img_base']:x}")
        for s in spec['sites']:
            new=bytes.fromhex(s['new'])
            cmds.append(f"w ${s['addr']:x} "+" ".join(f"${b:02x}" for b in new))
    cmds+=list(extra_cmds)
    app=h.R/'apply.txt'; app.write_text("\n".join(cmds)+"\n")
    start=len(h._logtext())
    h.cmd(f"hatari-debug b pc = $26e98 :trace :once :file {app}")
    t=time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[start:]:
        if time.time()-t>30: raise TimeoutError
        time.sleep(0.2)
    time.sleep(0.5)

def start_log(h, addrs=(0x6742,0x6766,0x6fb6), bp=0x33bde):
    f=h.R/'tick.txt'
    f.write_text("e VBL\n"+"".join(f"m ${a:x} 4\n" for a in addrs))
    h.cmd(f"hatari-debug b pc = ${bp:x} :trace :file {f}")
    h._ls=len(h._logtext())

def stop_log(h):
    h.debug("b all",0.5)
    txt=h._logtext()[h._ls:]
    return parse(txt)

def parse(txt):
    rows=[]; cur=None
    for ln in txt.splitlines():
        m=re.search(r"#(\d+) \(dec\)",ln)
        if m:
            cur={'vbl':int(m.group(1))}; rows.append(cur); continue
        m=re.match(r"\s*([0-9A-Fa-f]{8}):\s+((?:[0-9a-f]{2} ?)+)",ln)
        if m and cur is not None:
            a=int(m.group(1),16); b=bytes.fromhex(m.group(2).replace(' ',''))
            cur[a]=int.from_bytes(b[:2],'big',signed=False)
            if len(b)>=4: cur[a|0x1000000]=int.from_bytes(b[:4],'big')
    return rows
def sgn(x): return x-65536 if x>=32768 else x
