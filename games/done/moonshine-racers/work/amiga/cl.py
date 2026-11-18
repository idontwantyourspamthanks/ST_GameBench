import sys, json, os
sys.path.insert(0,'/home/ryan/Code/Amiga/gamebench/tools')
os.chdir('/home/ryan/Code/Amiga/gamebench')
from clharness import Machine, Session
B='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/alt/amiga/'
OUT='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/amiga/'
def machine(disk='Moonshine Racers Disk 1.adf', disk2='Moonshine Racers Disk 2.adf', **kw):
    return Machine(model="A500", fast=None, chip="1M", floppies=[B+disk,B+disk2], **kw)
class Tracer:
    def __init__(self, s, intena=False):
        self.s=s; self.rows=[]
        s.mmio(0xdff0a0,0x40,'write'); s.mmio(0xdff096,2,'write')
    def run_to(self,T):
        s=self.s
        while True:
            r=s.run_to(T)
            if r.get('reason')=='mmio':
                a=r['access']; p=a['position']
                self.rows.append((p['frame'],p['vpos'],p['hpos'],round(p['seconds'],4),a['pc'],a['addr'],a['size'],a['value']))
            else: return r
    def dump(self,path):
        with open(path,'w') as f:
            for r in self.rows: f.write(json.dumps(r)+'\n')
