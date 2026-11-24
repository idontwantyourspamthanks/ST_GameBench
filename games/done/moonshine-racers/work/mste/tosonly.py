"""Boot TOS only (empty drive C:) on machine/mem/clock; count Bus Errors logged. python3 tosonly.py MACHINE MEM TOS CLOCK SECS [extra hatari args...]"""
import sys, time, tempfile
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
from stharness import Hatari, TOS
m, mem, tos, clk, secs = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4], float(sys.argv[5])
d = tempfile.mkdtemp(prefix='mste-empty-')
h = Hatari(game_dir=d, machine=m, memsize_kb=mem, tos=TOS[tos], autorun=None, extra=['--cpuclock', clk] + sys.argv[6:])
try:
    time.sleep(secs)
    t = h._logtext()
    print(f"{m} {mem} TOS {tos} clk {clk}: vbl {h.vbl()} bus errors {t.count('Bus Error')}", flush=True)
    print(h.debug("m $68d0 2", 0.5).strip())
    import os
    if os.environ.get('SHOT'): h.shot(os.environ['SHOT']); print('SHOT', os.environ['SHOT'])
finally:
    h.close()
