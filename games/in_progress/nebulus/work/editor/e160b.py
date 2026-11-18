from e160_lib import *
h=mk('/tmp/ne/gdbg3','/tmp/ned160d')
t=T(h)
def dbg(): return [hex(x) for x in struct.unpack(">4l",grab(h,0x77cc0+176,16,"dbg"))]+[hex(struct.unpack(">l",grab(h,0x77cc0+240,4,"d2"))[0])]
def op(name,save=False):
    t.K('Down',4 if save else 3,hold=0.2,gap=0.4); t.F(1.0); t.F(4.0); time.sleep(1)
    print(f"{name:22s} msg={t.msg()!r} fopen/fread/fclose/fwrite={dbg()} alive={t.alive()}",flush=True)
try:
    print('title',h.boot_to_title(timeout=140),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    op('empty drive')
    t.insert('/tmp/ne/d/nofile.st'); op('disk without file')
    t.insert('/tmp/ne/d/short.st'); op('4096 B file')
    t.insert('/tmp/ne/d/blank.st'); op('blank (zero) disk')
    t.insert('/tmp/ne/d/t3.st'); op('t3 valid')
    h.cmd("hatari-option --protect-floppy on"); time.sleep(1)
    t.insert('/tmp/ne/d/t3.st'); op('t3 write-protected load')
    op('t3 write-protected SAVE',save=True)
    t.eject(); op('ejected again')
    h.cmd('hatari-option --protect-floppy off'); time.sleep(1)
    t.insert('/tmp/ne/d/big.st'); op('big text file'); t.insert('/tmp/ne/d/blank.st'); op('blank again'); t.insert('/tmp/ne/d/t3.st'); op('t3 again')
    h.cmd("hatari-option --protect-floppy off"); time.sleep(1)
finally: h.close()
