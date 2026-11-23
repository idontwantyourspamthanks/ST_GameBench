from ed import *
h=snap('/tmp/ned12')
try:
    time.sleep(1.5)
    while W(h,0x33a20)!=0: time.sleep(0.3)
    poke(h,0x3a4e6,bytes([0x4e,0x75])); poke(h,0x3792c,bytes([0x4e,0x75])); poke(h,0x3398c,bytes(8))
    poke(h,0x327f0+1*256+2,bytes([0x85]))
    for i in range(6):
        poke(h,0x38498,bytes([0x00])); time.sleep(0.3)
        poke(h,0x38498,bytes([0x80])); 
        for k in range(3):
            time.sleep(0.2)
            print(i,k,'fire',W(h,0x338f0),'st',W(h,0x33a20),'cell',hex(grab(h,0x327f0+258,1)[0]),'q',grab(h,0x339ee,10).hex(),'cnt',W(h,0x33918),'shot',W(h,0x33944+8*0+0x48+8),flush=True)
        if i==1: h.shot(E+'sh2.png')
finally: h.close()
