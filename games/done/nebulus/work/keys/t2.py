import sys, time, re
sys.path.insert(0,'../input')
from kh import KH
import tr
IMG='/home/ryan/Code/AtariST/gamebench/dist/AtariST_enhanced_games_2026-11-18.img'
joy = len(sys.argv)>1 and sys.argv[1]=='joy'
h = KH(IMG, workdir='/tmp/nf/t2'+('j' if joy else ''), auto=r'C:\NEBULUS\START.TOS', joy=joy)
while True:
    time.sleep(2)
    if 'High' in ''.join(chr(int(x,16)) for x in re.findall(r'3d00f:\s+(.*?)\s{2}', h.debug('m $3d00f 4',0.3)+'  ')[0].split() ) if False else b'48 69 67 68' in h.debug('m $3d00f 4',0.3).encode().lower().replace(b'high',b'48 69 67 68').upper() or False: pass
    out=h.debug('m $3d00f 4',0.3)
    if '48 69 67 68' in out: break
print('title up', time.time()-h.t0)
time.sleep(1)
EV=dict(tr.EV); EV['POLLT']='pc = $3853a'
order = tr.arm(h, ['POLL','ACIA','STORE'])
n0=len(h._logtext()); tr.marker(h)
time.sleep(1.0)
tr.marker(h)
for key,hold in (('F10',0.1),):
    h._xdo('keydown', key); tr.marker(h); time.sleep(hold); h._xdo('keyup', key); tr.marker(h)
time.sleep(1.0); tr.marker(h); time.sleep(0.4)
txt=h._logtext()[n0:]
h.debug('b all',0.3)
evs=tr.parse(txt, order, 160256)
last=None
for e in evs:
    print(e['n'], e['vbl'], e['fc'], hex(e.get('d0',0)) if 'd0' in e else '')
print('manager $70:', h.debug('m $70 4',0.4).strip().splitlines()[-1])
h.shot('/tmp/nf/t2_after.png')
h.close()
