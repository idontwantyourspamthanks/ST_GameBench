from nl import *
h=boot()
try:
    print('v118',hex(h.peekl(0x118)),'v70',hex(h.peekl(0x70)), 'kbdvec',hex(h.peekl(0x4a2)),flush=True)
    for k in ['Right','Control_R','h']:
        h._xdo('keydown','--window',h.win,k); time.sleep(0.6)
        print(k,hex(h.peekw(0x38498)),hex(h.peekw(0x3849a)),hex(h.peekw(0x338f0)),flush=True)
        h._xdo('keyup','--window',h.win,k); time.sleep(0.4)
    h.shot(L+'shots/r4.png')
    print(h.debug('m $200 16'))
finally:
    h.close()
