from common import *
h = open_snap("map_idle", "sg")
try:
    h.click_st(36, 62, wait=6.0); h.click_st(97, 158, wait=0.8); h.click_st(229, 173, wait=6.0)
    print("moving", moving(h), flush=True); h.shot("/tmp/pmww1prof/get_men.png")
    h.savemem("/tmp/pmww1prof/get_men.sav"); print("saved")
finally:
    h.close()
