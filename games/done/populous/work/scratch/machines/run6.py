import sys, time
from mm import *
name, medium, path = sys.argv[1], sys.argv[2], sys.argv[3]
times = [int(x) for x in sys.argv[4].split(",")]
extra = sys.argv[5].split() if len(sys.argv) > 5 else []
h = start(name, medium, path, extra=extra)
try:
    t0 = time.time()
    for t in times:
        time.sleep(max(0, t - (time.time() - t0)))
        print(t, "b3000:", mem(h, 0xb3000, 16), "| b3100:", mem(h, 0xb3100, 8))
        try: h.shot(f"/tmp/pm6_{name}_{medium}_t{t}.png")
        except Exception as e: print("shot fail", e)
    print(open(h.logpath).read()[-600:])
finally:
    h.close()
