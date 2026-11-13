import sys
from lib import *
build,mach,tag=sys.argv[1:4]
h=mk(build,mach)
try:
    print("menu",h.boot_to_menu(),flush=True); time.sleep(2)
    v=h.vbl()
    cd=h.R/'cd_draw.txt'; cd.write_text('info video\nm $392dc 8\n')
    cf=h.R/'cd_flip.txt'; cf.write_text('info video\nm $392dc 8\n')
    h.debug('b all',0.3)
    lo,hi=v+300,v+304
    for pc,f in (("$1a1a",cd),("$1c18",cf),("$1c3a",cf)):
        h.cmd(f'hatari-debug b pc = {pc} && VBL > {lo} && VBL < {hi} :trace :file {f}'); time.sleep(0.3)
    time.sleep(12)
    h.debug('b all',0.3)
    t=h._logtext(); i=t.find('Breakpoint')
    (OUT/f"evt_{tag}.txt").write_text(t[i-100:] if i>=0 else t[-3000:])
    print(t[i-100:i+5000] if i>=0 else t[-2000:])
finally: h.close()
