import sys, time, re
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
snap = sys.argv[1] if len(sys.argv) > 1 else 'raid_speedboat_iquitos.sav'
only = names(['jag_poll', 'jag_dir', 'jag_btn'])
pre = build_live(only, 'jag_all')
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=1024, extra=PADX)
try:
    time.sleep(2); apply_live(h, pre); jmode(h); time.sleep(1)
    h.debug('b all', 0.3)
    h.cmd('hatari-debug b pc = $31568 :trace'); time.sleep(0.3)
    h.cmd('hatari-debug b pc = $26e98 :trace'); time.sleep(0.3)   # flip
    v0 = h.vbl(); n0 = len(h._logtext()); time.sleep(12); v1 = h.vbl()
    t = h._logtext()[n0:]
    a = len(re.findall(r'^1\. CPU breakpoint', t, re.M)); b = len(re.findall(r'^2\. CPU breakpoint', t, re.M))
    print(f'{snap}: VBLs {v1 - v0}  $31568 (Esc poll) hits {a}  flips {b}   -> VBL per Esc poll {(v1 - v0) / max(a, 1):.1f}')
finally:
    h.close()
