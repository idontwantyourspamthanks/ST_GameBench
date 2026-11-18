from nt import *
h=snapshot_open()
try:
    time.sleep(1)
    for i in range(10):
        d=grab(h,0x33944,0x6c+12,'e')
        w=words(d)
        print(i)
        for f in range(0,len(w)//6):
            print(f'  +{f*12:02x}',[f'{x:04x}' for x in w[f*6:f*6+6]])
        h.shot(T+f'shots/s1_{i}.png')
        time.sleep(1.5)
finally:
    h.close()
