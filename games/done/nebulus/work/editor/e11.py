from ed import *
import sys
val=int(sys.argv[1],16) if len(sys.argv)>1 else 0x85
h=snap('/tmp/ned11')
try:
    time.sleep(1.5)
    while W(h,0x33a20)!=0: time.sleep(0.3)
    poke(h,0x3a4e6,bytes([0x4e,0x75])); poke(h,0x3792c,bytes([0x4e,0x75])); poke(h,0x3398c,bytes(8))
    poke(h,0x327f0+1*256+2,bytes([val]))
    def S(tag):
        c=grab(h,0x327f0+256+2,1)[0]
        q=grab(h,0x339ee,0x28,'q')
        sc=grab(h,0x33918,2).hex()
        print(f"{tag:10s} cell {c:02x} q0={q[:10].hex()} frogst {W(h,0x33a20)} cnt33918 {sc}",flush=True)
    S('start'); h.shot(E+f'sh_{val:02x}_0.png')
    for i in range(3):
        h.key('Control_R',hold=0.6); 
        for k in range(4):
            time.sleep(0.35); S(f'fire{i}+{k}')
            if k==1: h.shot(E+f'sh_{val:02x}_{i+1}.png')
        time.sleep(0.5)
finally: h.close()
