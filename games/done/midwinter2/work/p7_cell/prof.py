import sys, re, json, time, argparse; from pathlib import Path
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[2]/'tools'))
from mw2harness import Hatari
ap = argparse.ArgumentParser()
ap.add_argument('snap'); ap.add_argument('out'); ap.add_argument('--mem', type=int, default=2048)
ap.add_argument('--at', type=int, required=True); ap.add_argument('--flips', type=int, default=20)
ap.add_argument('--live'); ap.add_argument('--poke', action='append', default=[]); ap.add_argument('--pos', type=int, nargs=3)
a = ap.parse_args()
h = Hatari(snapshot=a.snap, memsize_kb=a.mem)
try:
    sv = Path(a.out + ".save").resolve()
    if sv.exists(): sv.unlink()
    end = h.R/'end.txt'
    end.write_text(f"profile stats\nprofile save {sv}\n")
    cmds=[]
    if a.live:
        spec = json.loads(Path(a.live + '.json').read_text())
        cmds.append(f"loadbin {Path(a.live + '.img').resolve()} ${spec['img_base']:x}")
        for s_ in spec['sites']:
            cmds.append(f"w ${s_['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s_['new'])))
    cmds += a.poke
    if a.pos:
        x,y,hd=a.pos; px=x*512+256; py=(100-y)*512-256
        for ad,v in ((0x66e6,px),(0x66ee,px),(0x66ea,py),(0x66f2,py)):
            cmds.append(f"w ${ad:x} "+" ".join(f"${(v>>sh)&255:02x}" for sh in (24,16,8,0)))
        for ad in (0x6742,0x6294,0x764a):
            cmds.append(f"w ${ad:x} ${hd>>8:02x} ${hd&255:02x}")
    cmds.append(f"b pc = ${h.FLIP:x} :{a.flips} :trace :once :file {end}")
    cmds.append("profile on")
    app = h.R/'apply.txt'; app.write_text("\n".join(cmds)+"\n")
    st=len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {a.at} && pc = ${h.FLIP:x} :trace :once :file {app}")
    t0=time.time()
    while not sv.exists():
        if time.time()-t0>600: raise TimeoutError
        time.sleep(0.5)
    time.sleep(3)
    Path(a.out+'.log').write_text(h._logtext()[st:])
    print('ok',a.out)
finally:
    h.close()
    import shutil; shutil.rmtree(h.R, ignore_errors=True)
