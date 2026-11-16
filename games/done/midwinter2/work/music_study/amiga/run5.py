from trace import *
m=Machine(floppies=disks())
with Session(m) as s:
    t=Tracer(s)
    t.run_to(14.0); s.mouse(left=True); t.run_to(17.0); s.mouse(left=False)
    for T in range(20,131,10):
        t.run_to(T); print(T,len(t.rows),flush=True)
    t.dump('full_trace_a.jsonl')
