import sys, time, re, json
sys.path.insert(0,'tools')
from p2abtest import *
mhz=int(sys.argv[1]); t_from=int(sys.argv[2]); t_to=int(sys.argv[3]); snap=sys.argv[4]
sp=snap_path(snap); t0=start_turn_for(sp)
live=make_live(WALKSET)
h=Populous2(snapshot=sp)
try:
    R=h.R; time.sleep(1)
    if mhz!=8: h.set_cpuclock(mhz)
    cmds=apply_cmds(live)+[f"w ${PX:x} $00 $a0 $00 $64", f"w ${MODE:x} $00 $03"]
    (R/'ev.txt').write_text("\n".join(["e VBL","e ($3979c).w","e ($393fa).w","e ($393fc).w","e ($392dc).l","e ($202e).l","e ($2246).w","e ($11d50).w","e CycleCounter"])+"\n")
    for pc in (0x1a1a,0x1b34,0x1b4e,0x1b9a,0x1bfe,0x1254e):
        cmds.append(f"b pc = ${pc:x} && ($3979c).w > {(t_from-1) & 0xffff} && ($3979c).w < {(t_to+1) & 0xffff} :trace :file {R/'ev.txt'}")
    (R/'end.txt').write_text(f"b all\nsavebin {R}/end.flag $0 2\n")
    cmds.append(f"b ($3979c).w > {t_to & 0xffff} :trace :once :file {R/'end.txt'}")
    (R/'apply.txt').write_text("\n".join(cmds)+"\n")
    start=len(h._logtext())
    h.cmd(f"hatari-debug b pc = ${APPLYPC:x} && (${TURN:x}).l = {t0} :trace :once :file {R/'apply.txt'}")
    time.sleep(0.3); h.cmd("hatari-option --fast-forward on")
    t=time.time()
    while not (R/'end.flag').exists() and time.time()-t<600: time.sleep(0.3)
    time.sleep(1)
    text=h._logtext()[start:]
    open(f'work/scratch/ptrtrace_{mhz}.log','w').write(text)
finally:
    h.close()
