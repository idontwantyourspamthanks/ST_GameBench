import sys, time, os
sys.path.insert(0, 'tools')
from msr import Moonshine, GAME
from stharness import TOS
h = Moonshine(machine='ste', memsize_kb=1024, game_dir=GAME / sys.argv[1], tos=TOS['1.62'])
try:
    n=0
    while True:
        v = h.vbl(); m = h.peekl(0xb2700)
        print(v, hex(m), flush=True)
        if m or v > 9000: break
        if v>5000 and n%2==0: h.keypress(57)
        n+=1; time.sleep(2)
finally:
    h.close()
