import sys, time, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
names=['p4_hud_pfx_fill','p4_hud_pfx_replay','p4_hud_pfx_ymin','p4_hud_reset']
live=build_live(names,'trace188')
h=Hatari(snapshot=str(ROOT:=GAME/'work/explosions/jeep_fired.sav'))
try:
    base=0x3532+3*0x42
    v0=h.vbl(); at=(v0//100+3)*100
    (h.R/'circ.txt').write_text("r\nm $b4684 2\nm $b4680 4\nm $7b6b0 48\n")
    ap=apply_cmds(live)+[pokel(base+6,25856+494),pokel(base+10,25600-494),pokew(base+0x36,1),
        f"b pc = $1d188 :trace :file {h.R}/circ.txt"]
    (h.R/'apply.txt').write_text('\n'.join(ap)+'\n')
    start=len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {at} && pc = ${h.FLIP:x} :trace :once :file {h.R}/apply.txt")
    time.sleep(5)
    h.debug('b all',0.5)
    log=h._logtext()[start:]
    open('/tmp/ex/trace188.log','w').write(log)
    print(len(log))
finally:
    h.close()
