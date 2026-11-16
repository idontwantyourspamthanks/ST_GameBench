from trace import *
import collections
m=Machine(floppies=disks())
with Session(m) as s:
    t=Tracer(s)
    for T in (10,20):
        t.run_to(T); print(T,len(t.rows)); s.shot(f'/tmp/mw_{T}.png')
    # leave intro
    s.mouse(left=True); t.run_to(s.now()+2.5); s.mouse(left=False)
    for T in (30,40,60,80):
        t.run_to(T); print(T,len(t.rows)); s.shot(f'/tmp/mw_{T}.png')
    t.dump('run1_trace.jsonl')
c=collections.Counter((r[4]>>12, r[5]) for r in t.rows)
print(c.most_common(40))
