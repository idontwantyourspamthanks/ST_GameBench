from cl import *
m=machine()
with Session(m) as s:
    s.run_to(1)
    for p in ({'name':'d0','value':5},{'reg':'d0','value':5},{'d0':5},{'regs':{'d0':5}},{'register':'d0','value':5}):
        try: r=s.call('regs.set',**p); print(p,'OK',r); print(s.regs()['d'][0]); break
        except Exception as e: print(p,'ERR',str(e)[:200])
