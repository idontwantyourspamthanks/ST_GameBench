import sys, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/lotus')
from lotus import *
h = Lotus(memsize_kb=int(sys.argv[1]) if len(sys.argv)>1 else 1024)
try:
    for i in range(12):
        time.sleep(10)
        h.shot(f'/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/lotus/shots/boot_{i:02d}.png')
        print(i, h.vbl(), flush=True)
finally:
    h.close()
