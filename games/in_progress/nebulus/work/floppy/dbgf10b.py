import sys,time,re
sys.path.insert(0,'.')
from nebfloppy import NebFloppy
img=sys.argv[1]; wd=sys.argv[2]
h=NebFloppy(img,workdir=wd)
def W(a):
    o=h.debug(f'm ${a:x} 2',0.35); m=re.findall(r'[0-9A-F]{8}:\s+([0-9a-f]{2}) ([0-9a-f]{2})',o,re.I); return int(''.join(m[-1]),16)
try:
    print('title',h.boot_to_title(),flush=True)
    for i in range(40):
        if W(0x3d5ae)==0: break
        time.sleep(1)
    for name,a in (('ed_run',0x75a7e),('m_main',0x7643a),('ed_vbl',0x75a32),('redraw',0x75c1a),('d85a',0x3d852),('d5e2',0x3d5da),('tiles',0x776fc),('ov_ok',0x7772e)):
        h.cmd(f'hatari-debug b pc = ${a:x} :once :trace'); time.sleep(0.2)
    n=len(h._logtext())
    h.key('F10',hold=0.6); time.sleep(4)
    log=h._logtext()[n:]
    for m in re.finditer(r'pc = \$([0-9a-f]+)',log): print('hit',m.group(1))
    print(h.debug('r',0.5))
finally:
    h.close()
