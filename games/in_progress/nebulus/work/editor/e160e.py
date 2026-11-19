from e160_lib import *
h=mk('/tmp/ne/gdbg3','/tmp/ned160g')
t=T(h)
def vdisk(): return struct.unpack('>H',grab(h,0x77cc0+174,2,'vd'))[0]
def timed(name):
    t0=time.time(); t.F(0.3)
    while time.time()-t0<90:
        time.sleep(0.7)
        if vdisk()==0: break
    print(f"{name}: {time.time()-t0:.1f} s vDisk {vdisk()} msg {t.msg()!r} dbg {[hex(x) for x in struct.unpack('>4l',grab(h,0x77cc0+176,16,'dbg'))]}",flush=True)
try:
    print('title',h.boot_to_title(timeout=140),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    t.K('Down',3,hold=0.2,gap=0.4); t.F(1.0); timed('empty drive')
    t.insert('/tmp/ne/d/nofile.st')
    t.K('Down',3,hold=0.2,gap=0.4); t.F(1.0); timed('nofile')
    t.insert('/tmp/ne/d/short.st')
    t.K('Down',3,hold=0.2,gap=0.4); t.F(1.0); timed('short 4096')
    t.insert('/tmp/ne/d/t3.st')
    t.K('Down',3,hold=0.2,gap=0.4); t.F(1.0); timed('t3')
finally: h.close()
