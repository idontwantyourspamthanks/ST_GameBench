import sys, json
from trace import *
from mw2cl import MW2, HALL_RAIDS, LEVELS, CAMARGO, BRIEFING_QUESTION, THUMBS_UP
IMG='/home/ryan/Code/Amiga/gamebench/dist/Amiga_enhanced_games_2026-11-15.hdf'
FL=[0,217912,302344,402344]
class Explorer:
    def __init__(self,g,mmio=True,segs=None):
        self.g=g; self.ev=[]; self.rows=[]
        self.segs=segs or g.call("segments.list")["current"]
        if segs: g._hunk1=lambda: segs[1]['start']
        self.names={}
        for nm,op in (('tune',0x60a8e),('req',0x57340),('pause',0x57344),('tick',0x5e296),('scene',0x609da),('sfxreq',0x56820)):
            a=self.rt(op); self.names[a]=nm; g.watch(a,'write')
        if mmio:
            g.mmio(0xdff0a0,0x40,'write'); g.mmio(0xdff096,2,'write')
    def rt(self,op):
        f=op-0x270d0
        for i in (3,2,1,0):
            if f>=FL[i]: return self.segs[i]['start']+f-FL[i]
    def run_to(self,T):
        g=self.g
        while True:
            r=g.run_to(T)
            rs=r.get('reason')
            if rs=='mmio':
                a=r['access']; p=a['position']
                self.rows.append((p['frame'],p['vpos'],p['hpos'],round(p['seconds'],4),a['pc'],a['addr'],a['size'],a['value']))
            elif rs in ('watch','watchpoint'):
                import re
                m=re.match(r'Watch \$([0-9A-F]+): ([0-9A-F]+)->([0-9A-F]+) \(pc \$([0-9A-F]+)\)',r['detail'])
                a=int(m.group(1),16)
                nm=self.names.get(a,hex(a))
                self.ev.append((round(r['seconds'],3),r['frame'],nm,m.group(2),m.group(3),hex(int(m.group(4),16))))
            else: return r
    def tail(self,n=0):
        e=self.ev[n:]; return e

def hold_click(x, pt, hold=1.2, settle=6):
    g=x.g
    g.goto(*pt)
    g.mouse(left=True); x.run_to(g.now()+hold); g.mouse(left=False)
    x.run_to(g.now()+settle)

def key(x, raw, hold=0.5, settle=6):
    g=x.g
    g.key(raw, action='down') if False else None
    g.key(raw, hold_ms=int(hold*1000))
    x.run_to(g.now()+settle)
