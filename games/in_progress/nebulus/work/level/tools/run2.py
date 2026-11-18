from nl import *
h=boot()
try:
    for c in 'helloiamjmp':
        h.key(c,hold=0.5); time.sleep(0.2)
        print(c, hex(words(grab(h,0x3d85e,2))[0]), hex(words(grab(h,0x33a40,2))[0]), hex(words(grab(h,0x38498,2))[0]),flush=True)
finally:
    h.close()
