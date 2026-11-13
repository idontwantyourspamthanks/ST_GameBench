import sys, time, subprocess
from mm import *
name, medium, path = sys.argv[1], sys.argv[2], sys.argv[3]
step=int(sys.argv[4]); n=int(sys.argv[5])
extra = sys.argv[6].split() if len(sys.argv) > 6 else []
h = start(name, medium, path, extra=extra)
fs=[]
try:
    for i in range(n):
        time.sleep(step)
        p=f"/tmp/pm4_{name}_{i:02d}.png"
        try:
            h.shot(p); fs.append(p)
        except Exception as e:
            print("shot failed", i, e)
            q=f"/tmp/pm4_{name}_{i:02d}_root.png"
            subprocess.run(["import","-window","root",q],env=h.env)
            fs.append(q); break
    try: print(mem(h,0xb3000,16))
    except Exception as e: print("mem fail", e)
    print(open(h.logpath).read()[-1500:])
finally:
    h.close()
subprocess.run(["python3","sheet.py",f"/tmp/pm4_{name}_sheet.png"]+fs)
