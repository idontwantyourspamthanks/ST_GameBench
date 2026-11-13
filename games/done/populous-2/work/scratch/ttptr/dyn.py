import sys
from lib import *
build=sys.argv[1]
h=mk(build,"tt")
try:
    ok=h.boot_to_menu(); print("menu",ok,flush=True)
    h.debug('b all',0.3)
    h.cmd('hatari-debug b pc = $1c26 :trace'); time.sleep(0.4)
    h.cmd('hatari-debug b pc = $1c3a :trace'); time.sleep(0.4)
    def click_st(x,y,wait=3.0):
        goto_st(h,x,y); time.sleep(0.3); h.click(hold=0.4); time.sleep(wait)
    click_st(144,100,3); click_st(82,20,1.0)
    for ch in "zeus": h.key(ch,0.3); time.sleep(0.4)
    h.key("Return",0.3); time.sleep(1)
    click_st(164,180,3); click_st(144,100,8); click_st(60,195,12); click_st(152,181,15)
    print("in_play",h.in_play(),flush=True)
    h.debug('b all',0.5)
    t=h._logtext(); i=t.rfind("CPU breakpoints")
    print('MATCH LINES',[l for l in t.splitlines() if 'matched' in l or 'Breakpoint' in l][:10]); print('1c26/1c3a mentions', t.count('pc = $1c26'), t.count('pc = $1c3a'))
finally: h.close()
