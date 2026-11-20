import sys, time, os
sys.path.insert(0, 'tools')
from msr import Moonshine, GAME
from stharness import TOS
h = Moonshine(machine='ste', memsize_kb=1024, game_dir=GAME / sys.argv[1], tos=TOS['1.62'])
try:
    while True:
        v = h.vbl(); m = h.peekl(0xb2700); w = h.peekw(0x1021) if False else 0
        print(v, hex(m), flush=True)
        if v > 5000: break
        time.sleep(2)
finally:
    h.close()
