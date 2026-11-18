from ed import *
import sys
types=[int(x,16) for x in sys.argv[1].split(',')]
col=int(sys.argv[2]) if len(sys.argv)>2 else 8
row=int(sys.argv[3]) if len(sys.argv)>3 else 2
h=snap('/tmp/ned5')
try:
    time.sleep(1.5)
    while W(h,0x33a20)!=0: time.sleep(0.3)
    poke(h,0x3a4e6,bytes([0x4e,0x75]))      # player never hit
    for c,r in [(8,5),(9,10),(9,15),(7,20),(12,20)]: poke(h,0x327f0+c*256+r,bytes([0]))
    for v in types:
        poke(h,0x3398c,bytes(8))
        # keep the stock markers out: only my marker; scan pointer to (col0,row)
        poke(h,0x327f0+col*256+row,bytes([v]))
        a=0x327f0+row  # col 0
        poke(h,0x3393c,struct.pack('>L',a))
        t0=time.time(); shots=0
        print(f'--- marker {v:02x} at col {col} row {row}',flush=True)
        for n in range(4):
            d=struct.unpack('>60H',grab(h,0x33944,0x78,'s'))
            out=[]
            for s in range(4):
                if d[0x48//2+s]==0: continue
                sp=d[0x54//2+s]; sp=sp-65536 if sp>32767 else sp
                out.append(f"s{s} x{d[s]:3d} y{d[6+s]:3d} st{d[0x48//2+s]} sp{sp:2d} k{d[0x6c//2+s]} f{d[0x18//2+s]}")
            print(f"{time.time()-t0:4.1f} frogx {W(h,0x33a16)} st{W(h,0x33a20)} scan {L(h,0x3393c):x} | "+" | ".join(out),flush=True)
            if n in (1,3): h.shot(E+f'en2_{v:02x}_{n}.png')
        poke(h,0x327f0+col*256+row,bytes([0]))
finally: h.close()
