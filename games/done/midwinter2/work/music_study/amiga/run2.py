from trace import *
import sys
m=Machine(floppies=disks())
with Session(m) as s:
    s.run_to(14.0)
    s.mouse(left=True); s.run_to(17.0); s.mouse(left=False)
    s.run_to(55)
    s.shot('shots/t55.png')
    # find MWII code base: signature of the tick routine start
    pat=bytes.fromhex('4a7900057374') # tst.w $57374.l  (operand relocated -> differs)
    segs=s.call("segments.list")
    print(json.dumps(segs)[:600])
    s.save_state('states/t55.clstate')
