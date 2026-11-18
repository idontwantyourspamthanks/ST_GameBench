from ed import *
import threading
gd=__import__('pathlib').Path
h=Nebulus(workdir='/tmp/ned52',game=gd(E+'build_final'))
def K(k,n=1,hold=0.2,gap=0.4):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
try:
    print('title',h.boot_to_title(timeout=100),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    t=threading.Thread(target=lambda:h.key('Down',hold=1.5)); t.start()
    time.sleep(0.6); print('before save: 38498',hex(grab(h,0x38498,1)[0]),'dy',W(h,0x338f4)); t.join()
    K('Down',2); K('Control_R',hold=0.35,gap=1.0); time.sleep(4)
    print(h.debug('m $fffc00 4',0.6)[-80:]); print(h.debug('m $fffa01 32',0.6)[-200:])
    t=threading.Thread(target=lambda:h.key('Up',hold=1.5)); t.start()
    time.sleep(0.6); print('after save: 38498',hex(grab(h,0x38498,1)[0]),'dy',W(h,0x338f4),'vec118',hex(L(h,0x118))); t.join()
finally: h.close()
