import sys, os, gzip, shutil
os.environ['HOME']='/tmp/ng12hd/home'
sys.path.insert(0,'/tmp/ng12hd/nb/work/editor')
from ulib_ui import *
X='/tmp/ng12hd/x'
build, tag, mach = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(f'{X}/snap', exist_ok=True)
snap=f'{X}/snap/{tag}_{mach}.sav'
print('boot ok', mk_snap(build, snap, mach, f'/tmp/ng12hd/wd_snap_{tag}_{mach}'), flush=True)
d=gzip.open(snap).read()
for p in ('0203131402020202','303900077cbe','436f6e7665796f72206c656674'):
    print(tag, mach, p, 'present' if bytes.fromhex(p) in d else 'ABSENT', flush=True)
