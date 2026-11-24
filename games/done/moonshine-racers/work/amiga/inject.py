from cl import *
import json,sys,struct
ids=[int(x) for x in sys.argv[1].split(',')] if len(sys.argv)>1 else list(range(1,71))
m=Machine(model="A500", fast=None, chip="1M", floppies=[B+'Moonshine Racers Disk 2.adf'])
res={}
with Session(m) as s:
    s.load_state(OUT+'st_n5.clstate')
    tick=s.break_pc(0x4ec82)
    tr=Tracer(s)
    def inject(calls):
        """wait for next tick break, then issue calls (id,ch) by running start routine"""
        for (sid,ch) in calls:
            while True:
                r=s.run_for(0.2)
                if r.get('reason') in ('break','pc') or 'break' in str(r.get('reason')): break
            s.call('regs.set',reg='d0',value=sid); s.call('regs.set',reg='d1',value=ch)
            s.call('regs.set',reg='pc',value=0x4ec76)
            # run just past the routine: it returns to the tick caller; continue
            r=s.cont() if False else None
    # simpler: manual loop handling
    def run_until_tick():
        while True:
            r=s.run_for(0.5)
            if r.get('reason')!='mmio': return r
            a=r['access']; p=a['position']
            tr.rows.append((p['frame'],p['vpos'],p['hpos'],round(p['seconds'],4),a['pc'],a['addr'],a['size'],a['value']))
    def call_script(sid,ch):
        r=run_until_tick()
        # now stopped at break or timeout
        s.call('regs.set',reg='d0',value=sid); s.call('regs.set',reg='d1',value=ch); s.call('regs.set',reg='pc',value=0x4ec76)
    # silence
    for ch in range(4): call_script(0,ch)
    for sid in ids:
        n0=len(tr.rows)
        call_script(sid,2)
        t0=s.now()
        # run 4 s collecting events, passing ticks
        tr_end=t0+4.0
        while s.now()<tr_end:
            r=s.run_to(tr_end)
            if r.get('reason')=='mmio':
                a=r['access']; p=a['position']
                tr.rows.append((p['frame'],p['vpos'],p['hpos'],round(p['seconds'],4),a['pc'],a['addr'],a['size'],a['value']))
        res[sid]=(t0,tr.rows[n0:])
        for ch in range(4): call_script(0,ch)
        print(sid,len(tr.rows)-n0,flush=True)
    json.dump({str(k):v for k,v in res.items()},open(OUT+'inject_all.json','w'))
