import sys, time
from mm import *
from nav import *
from pm_cells import goto_shot, CONQUEST
name, medium, path, mode = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]   # mode: click | wait
h = start(name, medium, path)
try:
    if mode == "click":
        wait_menu_f = None
        t0=time.time()
        # falcon menu detection
        from pm_cells import wait_for_crop, REF
        t = wait_for_crop(h, REF/"falcon_menu_buttons.png", (500,310,680,395), 150); print("menu", t)
        goto_shot(h, name, *CONQUEST); h.click(hold=0.4)
        time.sleep(50)
    else:
        time.sleep(70)
    h.shot(f"/tmp/run7_{mode}.png")
    for a,n in ((0xff8240,32),(0xff9800,64),(0xff8260,4),(0xff8266,2),(0xff82c0,4),(0xff820a,2),(0xff8006,2)):
        print(hex(a), mem(h,a,n))
finally:
    h.close()
