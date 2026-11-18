from e160_lib import *
h=mk('/tmp/ne/gdbg','/tmp/ned160h'); t=T(h)
def dbg(): return [hex(x) for x in struct.unpack('>4l',grab(h,0x77cc0+176,16,'dbg'))]
try:
    print('title',h.boot_to_title(timeout=140),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    h.cmd('hatari-option --protect-floppy on'); time.sleep(1)
    t.insert('/tmp/ne/d/t3.st')
    t.K('Down',4,hold=0.2,gap=0.4); t.F(1.0); t.F(5.0); print('wp SAVE msg',t.msg(),dbg(),flush=True)
    t.K('Down',4,hold=0.2,gap=0.4); t.F(1.0); t.F(5.0); print('wp SAVE again msg',t.msg(),dbg(),flush=True)
finally: h.close()
