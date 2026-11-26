import sys; sys.path.insert(0, '/tmp/ng12fl/s')
from lib import *
h = NebFloppy(sys.argv[1], machine=sys.argv[2], mem=1024, workdir=sys.argv[3], trace='fdc')
try:
    print('title', h.boot_to_title(timeout=400, space_at=20), flush=True); time.sleep(3)
    rs = lambda off: struct.unpack('>L', grab(h, 0x77c80 + off, 4, 'rsx'))[0]
    b = grab(h, rs(58), 24, 'mb'); print('MFP block', b.hex(' '), 'IERB', hex(b[4]), 'TCDCR', hex(b[14]), flush=True)
finally: h.close()
