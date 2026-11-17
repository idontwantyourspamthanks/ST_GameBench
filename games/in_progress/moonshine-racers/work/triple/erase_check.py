"""Stock game, race_grid snapshot (time-out state: many messages): log every entry of the message-box erase $12086 and of the glyph draw $120a4
with the pass counter, the back buffer ($1008), the ticker flags.  python3 erase_check.py OUT.log SECONDS"""
import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint')
from mxlib_int import *
import msrabtest as ab
from msr import Moonshine
out, secs = sys.argv[1], float(sys.argv[2])
h = Moonshine(snapshot=ab.snap_path('race_grid'))
R = h.R
try:
    time.sleep(1.5); h.debug('b all', 0.3)
    (R / 'e1.txt').write_text("e $1\nm $100e 2\nm $1004 8\nm $11a6 2\nm $11ab 6\n")   # erase box
    (R / 'e2.txt').write_text("e $2\nm $100e 2\nm $1004 8\nm $11a6 2\nm $11ae 2\n")   # glyph
    (R / 'e3.txt').write_text("e $3\nm $100e 2\nm $1004 8\n")                          # pass top 7a88
    n0 = len(h._logtext())
    for pc, f in ((0x12086, 'e1'), (0x120a4, 'e2'), (0x7a88, 'e3')):
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {R}/{f}.txt"); time.sleep(0.2)
    time.sleep(secs)
    h.debug('b all', 0.5); log = h._logtext()[n0:]
finally:
    h.close()
open(out, 'w').write(log)
print(len(log))
