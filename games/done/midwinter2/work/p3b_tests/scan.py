import sys,time,re
sys.path.insert(0,'/tmp/p3b')
from exp2 import *
sys.path.insert(0,'/tmp/p5')
from lib import apply_live
h=Hatari(snapshot=str(ROOT/'work/snapshots/1mb_ingame_walking.sav'))
def rd(a,n):
    out=h.debug(f"m ${a:x} {n}",0.35)
    m=re.findall(rf"{a:08X}:\s+((?:[0-9a-f]{{2}} ?)+)",out)[-1]
    return bytes.fromhex(m.replace(' ',''))
try:
    apply_live(h,'/tmp/p3b/live/A',['w $26aca $4e $71 $4e $71'])
    res=[]
    for X in range(6000,24001,3000):
        for Y in range(18000,34001,3000):
            h.debug("w $66e6 %s"%" ".join("$%02x"%b for b in X.to_bytes(4,'big')+Y.to_bytes(4,'big')),0.1)
            time.sleep(1.2)
            blk=[]
            for _ in range(3):
                blk.append(int.from_bytes(rd(0x676e,2),'big')); time.sleep(0.4)
            p=rd(0x66e6,8)
            print(X,Y,'->',int.from_bytes(p[:4],'big'),int.from_bytes(p[4:],'big'),'blk',blk,flush=True)
finally:
    h.close()
