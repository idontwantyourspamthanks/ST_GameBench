import sys, time
from mm import *
name, medium, path = sys.argv[1], sys.argv[2], sys.argv[3]
times = [int(x) for x in sys.argv[4].split(",")]
h = start(name, medium, path)
try:
    t0 = time.time()
    for t in times:
        time.sleep(max(0, t - (time.time() - t0)))
        print(t, "b3000:", mem(h, 0xb3000, 16), "| b6f4:", mem(h, 0xb6f4, 6), "| ee16:", mem(h,0xee16,2), "| pc/sr:", end=" ")
        o = h.debug("r", 0.8); print(re.findall(r"PC[:=]\s*\$?[0-9a-f]+", o, re.I)[:1])
        h.shot(f"/tmp/pm_{name}_{medium}_t{t}.png")
    print(open(h.logpath).read()[-800:])
finally:
    h.close()
