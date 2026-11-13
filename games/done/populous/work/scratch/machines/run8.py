import sys, time
from mm import *
name, medium, path = sys.argv[1], sys.argv[2], sys.argv[3]
extra = sys.argv[4].split()
h = start(name, medium, path, extra=extra)
try:
    for i in range(8):
        time.sleep(3)
        try: h.shot(f"/tmp/run8_{i}.png")
        except Exception as e: print("shot fail", i)
    h.keypress(50)    # M make code; held below
    time.sleep(0.5)
    for i in range(8, 14):
        time.sleep(3)
        try: h.shot(f"/tmp/run8_{i}.png")
        except Exception as e: print("shot fail", i)
finally:
    h.close()
