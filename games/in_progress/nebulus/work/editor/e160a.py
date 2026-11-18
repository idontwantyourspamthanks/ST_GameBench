from e160_lib import *
h=mk('/tmp/ne/g3','/tmp/ned160')
t=T(h)
try:
    print('title',h.boot_to_title(timeout=140),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    t.K('Down',3,hold=0.2,gap=0.4); h.shot(E+'e160_main.png'); t.F(1.0); h.shot(E+'e160_prompt.png')
    print('vDisk',struct.unpack('>H',grab(h,0x77cc0+174,2))[0])
    t.F(3.0); print('empty drive ->',t.msg(),'alive',t.alive()); h.shot(E+'e160_nodisk.png')
    t.insert('/tmp/ne/d/t3.st'); print('inserted')
    t.K('Down',3,hold=0.2,gap=0.4); t.F(1.0); t.F(4.0); print('t3 disk ->',t.msg(),'alive',t.alive()); h.shot(E+'e160_loaded.png')
    st=t.store(); open('/tmp/ne/store_after_load.ovl','wb').write(st)
finally: h.close()
