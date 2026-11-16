from trace import *
import sys
D=0x1F5678
rt=lambda o:o+D
m=Machine(floppies=disks())
T0=float(sys.argv[1]); T1=float(sys.argv[2]); step=float(sys.argv[3]) if len(sys.argv)>3 else 4
with Session(m) as s:
    s.load_state(STATES+'t58.clstate')
    t=Tracer(s)
    cur=rt(0x60a8e); req=rt(0x57340)
    T=s.now()
    log=[]
    while T<T1:
        T+=step
        t.run_to(T)
        v=(round(s.now(),2), s.read_w(cur), s.read_l(req), s.read_w(rt(0x57344)), hex(s.regs()['pc']))
        print(v, len(t.rows), flush=True)
        s.shot(f'shots/tl_{int(T):04d}.png')
    t.dump('tl_trace.jsonl')
