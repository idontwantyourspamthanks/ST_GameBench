import sys, time
from mm import *
name, medium, path, secs = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
h = start(name, medium, path)
try:
    for i in range(secs//10):
        time.sleep(10)
        try:
            p = f"/tmp/pm_{name}_{medium}_{(i+1)*10}.png"
            h.shot(p); print("shot", p)
        except Exception as e:
            print("shot fail", e); break
    print(h.R)
    print(open(h.logpath).read()[-1500:])
finally:
    h.close()
