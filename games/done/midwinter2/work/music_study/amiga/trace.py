"""Paula register-write tracer for Copperline sessions (Midwinter 2 music study)."""
import sys, json
sys.path.insert(0,'/home/ryan/Code/Amiga/gamebench/tools')
sys.path.insert(0,'/home/ryan/Code/Amiga/gamebench/games/in_progress/Midwinter-2/tools')
from clharness import *
from pathlib import Path

O=Path('/home/ryan/Code/Amiga/gamebench/games/in_progress/Midwinter-2/originals')
STATES='/home/ryan/Code/Amiga/gamebench/games/in_progress/Midwinter-2/work/states/music/'
def disks():
    return [next(O.glob(f"*Disk {i} of 3*SPL*.adf")) for i in (1,2,3)]

BASE0=0x21c740-0x270d0      # runtime = operand + BASE0  (hunk 0 code/data at this boot's load address; verify with find())

class Tracer:
    """logs MMIO writes to AUDx (0xa0-0xdf) and DMACON. rows: (frame,vpos,hpos,sec,pc,addr,size,value)"""
    def __init__(self, s, intena=False):
        self.s=s; self.rows=[]; self.ids=[]
        self.ids.append(s.mmio(0xdff0a0,0x40,'write'))
        self.ids.append(s.mmio(0xdff096,2,'write'))
        if intena:
            self.ids.append(s.mmio(0xdff09a,2,'write'))
    def run_to(self, T, maxrows=10**7):
        s=self.s
        while True:
            r=s.run_to(T)
            if r.get('reason')=='mmio':
                a=r['access']; p=a['position']
                self.rows.append((p['frame'],p['vpos'],p['hpos'],round(p['seconds'],4),a['pc'],a['addr'],a['size'],a['value']))
                if len(self.rows)>maxrows: return
            else:
                return r
    def dump(self,path):
        with open(path,'w') as f:
            for r in self.rows: f.write(json.dumps(r)+'\n')

def boot_to_mwii(s, press=14.0, release=17.0):
    s.run_to(press); s.mouse(left=True); s.run_to(release); s.mouse(left=False)
