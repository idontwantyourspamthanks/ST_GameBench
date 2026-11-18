from ed import *
sets=[[0x80,0x82,0x85],[0x91,0xb1,0x87],[0x89,0x8d,0xa1],[0xc3,0x83,0x08],[0x81,0x84,0x86]]
h=snap('/tmp/ned7')
try:
    time.sleep(1.5)
    while W(h,0x33a20)!=0: time.sleep(0.3)
    poke(h,0x3a4e6,bytes([0x4e,0x75]))
    poke(h,0x3792c,bytes([0x4e,0x75])); poke(h,0x3398c,bytes(8))
    for i,s in enumerate(sets):
        for c in range(3,6):
            for r in (3,4,5): poke(h,0x327f0+c*256+r,bytes([0]))
        for k,v in enumerate(s): poke(h,0x327f0+(3+k)*256+4,bytes([v]))
        time.sleep(1.2)
        h.shot(E+f'cell_{i}.png'); print(i,[hex(v) for v in s])
finally: h.close()
