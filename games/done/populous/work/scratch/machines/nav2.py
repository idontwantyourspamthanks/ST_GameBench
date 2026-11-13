import sys, time
from mm import *
from nav import *
name, medium, path = sys.argv[1], sys.argv[2], sys.argv[3]
extra = sys.argv[4].split() if len(sys.argv) > 4 else []
h = start(name, medium, path, extra=extra)
fs=[]
try:
    t = wait_menu(h); print("menu after", t)
    h.goto(*CONQUEST_XY, home_xy=HOME_TT)
    h.click(hold=0.4)
    for i in range(14):
        time.sleep(5)
        p=f"/tmp/nav2_{i:02d}.png"; h.shot(p); fs.append(p)
    print(mem(h, 0xb3000, 16))
finally:
    h.close()
import subprocess
subprocess.run(["python3","sheet.py","/tmp/nav2_sheet.png"]+fs)
