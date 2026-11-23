import sys, time, shutil, re, json
from pathlib import Path
G = Path("/home/ryan/Code/AtariST/gamebench/games/in_progress/powermonger-ww1")
sys.path.insert(0, str(G/"tools"))
import pmww
from pmww import PMW
PEOPLE, PN, PS = 0x55DF4, 512, 0x32
FLIP = "($ff8201).b"
def open_snap(name, work, mhz=8):
    W = Path("/tmp/pmww1prof")/work; shutil.rmtree(W, ignore_errors=True)
    h = PMW(workdir=str(W), memsize_kb=1024, snapshot=f"/tmp/pmww1prof/{name}.sav")
    time.sleep(1.0)
    if mhz != 8: h.set_cpuclock(mhz)
    return h
def people(h):
    d = h.ram(PEOPLE, PN*PS)
    return [d[i*PS:(i+1)*PS] for i in range(PN)]
def moving(h, gap=0.4):
    a = people(h); time.sleep(gap); b = people(h)
    return sum(1 for x,y in zip(a,b) if 0 < x[5] < 0x80 and x[8:12] != y[8:12])
