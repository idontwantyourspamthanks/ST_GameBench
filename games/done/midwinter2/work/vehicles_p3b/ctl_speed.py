import sys, hashlib
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
from concurrent.futures import ThreadPoolExecutor
snap=sys.argv[1]; flips=int(sys.argv[2])
def one(mhz):
    h=Hatari(snapshot=str(SNAP/snap),memsize_kb=2048)
    try:
        if mhz!=8: h.set_cpuclock(mhz)
        out=Path('/tmp/ab2/ctl_%s_%d_%d'%(snap,mhz,flips))
        h.capture_frames(str(out),live=None,at_vbl=154100,nth_flip=flips)
    finally: h.close()
    return {n:hashlib.md5((out/n).read_bytes()[:32000]).hexdigest() for n in ('buf60000.bin','buf70000.bin')}
with ThreadPoolExecutor(2) as ex:
    a=ex.submit(one,8); b=ex.submit(one,16)
    ra,rb=a.result(),b.result()
print('CTL',snap,flips,'8MHz vs 16MHz unpatched:','IDENTICAL' if ra==rb else 'DIFFER')
