from ed import *
h=snap('/tmp/ned1')
try:
    time.sleep(3)
    for a,n in [(0x80,0x40),(0x400,0x40),(0x4a0,0x10),(0x4c0,0x10),(0x4f0,0x10),(0x70,0x10),(0x110,0x20)]:
        d=grab(h,a,n); print(hex(a),' '.join(f'{x:08x}' for x in struct.unpack('>%dL'%(n//4),d)))
    h.shot(E+'e1.png')
finally: h.close()
