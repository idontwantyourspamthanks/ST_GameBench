from ed import *
h=snap('/tmp/ned13')
def shoot(h):
    poke(h,0x33a1e,bytes([0,0])); poke(h,0x33a20,bytes([0,5]))
try:
    time.sleep(1.5)
    while W(h,0x33a20)!=0: time.sleep(0.3)
    poke(h,0x3a4e6,bytes([0x4e,0x75])); poke(h,0x3792c,bytes([0x4e,0x75])); poke(h,0x3398c,bytes(8))
    print('facing 33a1c',hex(W(h,0x33a1c)),'frog',W(h,0x33a16),W(h,0x33a18))
    for val in (0x82,0x86,0x85,0x89,0x80,0x81):
        poke(h,0x327f0+1*256+2,bytes([val])); poke(h,0x327f0+2*256+2,bytes([val])); 
        for n in range(3):
            shoot(h)
            for k in range(5):
                time.sleep(0.25)
                c1=grab(h,0x327f0+258,1)[0]; c2=grab(h,0x327f0+514,1)[0]
                print(f"val {val:02x} shot{n}+{k}: cell(1,2)={c1:02x} cell(2,2)={c2:02x} cnt={W(h,0x33918)} q={grab(h,0x339ee,10).hex()} st={W(h,0x33a20)}",flush=True)
        if val==0x82: h.shot(E+'shot82.png')
finally: h.close()
