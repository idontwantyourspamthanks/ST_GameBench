from ed import *
vals=[0x80,0x81,0x82,0x83,0x85,0x87,0x89,0x8d,0x91,0xa1,0xb1,0xc3,0x08,0x0c]
h=snap('/tmp/ned10')
try:
    time.sleep(1.5)
    while W(h,0x33a20)!=0: time.sleep(0.3)
    poke(h,0x3a4e6,bytes([0x4e,0x75])); poke(h,0x3792c,bytes([0x4e,0x75])); poke(h,0x3398c,bytes(8))
    for c in (15,0,1,2): 
        for r in range(2,12): poke(h,0x327f0+c*256+r,bytes([0]))
    for i,v in enumerate(vals):
        for c in (15,0,1,2): poke(h,0x327f0+c*256+7,bytes([v]))
        time.sleep(1.0)
        h.shot(E+f'cl_{v:02x}.png'); print(hex(v),flush=True)
finally: h.close()
