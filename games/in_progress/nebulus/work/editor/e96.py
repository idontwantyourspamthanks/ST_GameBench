import sys
G='/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/'
sys.path.insert(0,G+'work/input'); sys.path.insert(0,G+'tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
import scripted2, cmp_sc
from nebulus import Nebulus
orig=scripted2.Nebulus
scripted2.Nebulus=lambda **kw: orig(**{**kw,'workdir':'/tmp/ned_eq'})
ref,_=scripted2.run('eq_ref',[],duration=10)
spec={8:0x08,20:0x88,26:0x08,40:0x00,55:0x80,60:0x00,75:0x04,90:0x00}
ev=scripted2.build_script(ref,spec)
s2,t2=scripted2.run('eq_stock2',ev,caps=(1,4),live='none')
print('baseline: stock vs stock2 (same script twice)')
cmp_sc.main('eq_stock','eq_stock2'); cmp_sc.main2('eq_stock','eq_stock2')
