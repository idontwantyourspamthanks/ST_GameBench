import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0, 'tools')
from nebulus import Nebulus
h = Nebulus(snapshot='work/snapshots/1mb_tower.sav', workdir='/tmp/strun-ni2')
try:
    time.sleep(2)
    n=len(h._logtext())
    h.cmd('hatari-debug b pc = $3853a :trace'); 
    h.cmd('hatari-debug b pc = $39c8c :trace'); 
    h.cmd('hatari-debug b pc = $39aaa :trace'); 
    h.cmd('hatari-debug b pc = $382d8 :trace'); 
    time.sleep(1.0)
    h.debug('b all',0.5)
    print(h._logtext()[n:][:3000])
finally:
    h.close()
