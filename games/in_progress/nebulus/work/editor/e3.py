from ed import *
h=snap('/tmp/ned3')
try:
    time.sleep(2)
    # hold Right to climb? just sample
    t0=time.time(); n=0
    while time.time()-t0<45:
        d=grab(h,0x33944,0x78,'s')
        w=struct.unpack('>60H',d)
        out=[]
        for s in range(4):
            x,y,st,sp,k=w[s],w[6+s],w[0x48//2+s],w[0x54//2+s],w[0x6c//2+s]
            out.append(f"s{s} x{x:3d} y{y:4d} st{st} sp{sp-65536 if sp>32767 else sp:2d} k{k}")
        print(f"{time.time()-t0:5.1f} "+" | ".join(out),flush=True)
finally: h.close()
