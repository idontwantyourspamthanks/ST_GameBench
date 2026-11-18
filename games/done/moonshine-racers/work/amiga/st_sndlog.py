import sys,time,re,json
from pathlib import Path
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/tools')
from msr import Moonshine, GAME
snap=sys.argv[1] if len(sys.argv)>1 else str(GAME/'work/snapshots/ste1m_race_start.sav')
secs=float(sys.argv[2]) if len(sys.argv)>2 else 120
h=Moonshine(snapshot=snap)
try:
    time.sleep(3)
    f=h.R/'snd_8c00.txt'
    f.write_text("e VBL\ne d0\ne d1\n")
    h.debug("b all",0.3)
    h.cmd(f"hatari-debug b pc = $8c00 :trace :file {f}")
    t0=time.time(); v0=h.vbl()
    pats=[0x01,0x05,0x09,0x00,0x04,0x08,0x81,0x85]
    k=0
    while time.time()-t0<secs:
        h.debug(f"w $6105 ${pats[k%len(pats)]:02x}",0.2); k+=1
        time.sleep(5)
    v1=h.vbl()
    log=h._logtext()
    Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/amiga/st_sndlog_raw.txt').write_text(log)
    print('vbl',v0,v1,len(log))
finally:
    h.close()
