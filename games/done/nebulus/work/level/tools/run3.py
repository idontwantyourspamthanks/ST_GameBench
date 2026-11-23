from nl import *
h=boot()
try:
    print('base',hex(h.peekw(0x38498)),hex(h.peekw(0x3849a)),flush=True)
    h._xdo('keydown','--window',h.win,'h'); time.sleep(0.5)
    print('xdo h down',hex(h.peekw(0x38498)),hex(h.peekw(0x3849a)),flush=True)
    h._xdo('keyup','--window',h.win,'h'); time.sleep(0.3)
    print('xdo h up',hex(h.peekw(0x38498)),flush=True)
    h.cmd('hatari-event keydown 35'); time.sleep(0.5)
    print('ev h down',hex(h.peekw(0x38498)),hex(h.peekw(0x3849a)),flush=True)
    h.cmd('hatari-event keyup 35'); time.sleep(0.3)
    print('ev h up',hex(h.peekw(0x38498)),flush=True)
    h.cmd('hatari-event keypress 35'); time.sleep(0.5)
    print('ev h press',hex(h.peekw(0x38498)),hex(h.peekw(0x3849a)),hex(h.peekw(0x3d85e)),flush=True)
    h.shot(L+'shots/r3.png')
finally:
    h.close()
