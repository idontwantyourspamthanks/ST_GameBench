from cl import *
m=machine()
with Session(m) as s:
    t=Tracer(s)
    for T in range(70,400,30):
        t.run_to(T)
        s.shot(OUT+f'nav_{T:03d}.png')
        print(T, len(t.rows), hex(s.regs()['pc']))
    t.dump(OUT+'trace_nav1.jsonl')
