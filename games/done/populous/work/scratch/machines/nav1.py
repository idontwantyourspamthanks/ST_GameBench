import sys, time
from mm import *
from nav import *
name, medium, path = sys.argv[1], sys.argv[2], sys.argv[3]
extra = sys.argv[4].split() if len(sys.argv) > 4 else []
home = HOME_TT
h = start(name, medium, path, extra=extra)
try:
    t0 = time.time()
    t = wait_menu(h)
    print("menu after", t)
    h.goto(*CONQUEST_XY, home_xy=home); h.shot("/tmp/nav_a.png")
    h.click(hold=0.4); time.sleep(6); h.shot("/tmp/nav_b.png")
    h.goto(*START_XY, home_xy=home); h.shot("/tmp/nav_c.png")
    h.click(hold=0.4); time.sleep(10); h.shot("/tmp/nav_d.png")
    print("in_play", h.in_play())
    print(mem(h, 0xb3000, 16))
finally:
    h.close()
