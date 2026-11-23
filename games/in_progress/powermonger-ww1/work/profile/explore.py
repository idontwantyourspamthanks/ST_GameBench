from common import *
h = open_snap("map_idle", "ex")
try:
    h.click_st(36, 62, wait=6.0); h.shot("/tmp/pmww1prof/ex1.png"); print("iter", hex(h.counter()), flush=True)
    h.click_st(97, 158, wait=0.8)
    h.click_st(229, 173, wait=6.0); h.shot("/tmp/pmww1prof/ex2.png")
    for i in range(3):
        print("moving", moving(h), "iter", hex(h.counter()), flush=True)
finally:
    h.close()
