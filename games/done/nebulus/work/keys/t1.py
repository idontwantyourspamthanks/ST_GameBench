import sys, time
from kh import KH
IMG='/home/ryan/Code/AtariST/gamebench/dist/AtariST_enhanced_games_2026-11-18.img'
h = KH(IMG, workdir='/tmp/nf/t1', auto=r'C:\NEBULUS\START.TOS')
print(h.args)
t0=time.time()
for i in range(18):
    time.sleep(5)
    h.shot(f'/tmp/nf/t1/s{i:02d}.png')
    print(i*5+5, h.debug('m $3d00f 4',0.3).strip().splitlines()[-1:], h.debug('m $b0020 4',0.3).strip().splitlines()[-1:])
h.close()
