from ed import *
gd=__import__('pathlib').Path
h=Nebulus(workdir='/tmp/ned60',game=gd(E+'build_final'))
try:
    print('in tower',h.boot_to_game(timeout=120),flush=True); time.sleep(3)
    while W(h,0x33a20)!=0: time.sleep(0.5)
    poke(h,0x3a4e6,bytes([0x4e,0x75]))
    for c,r in [(8,5),(9,10),(9,15),(7,20),(12,20)]: poke(h,0x327f0+c*256+r,bytes([0]))
    for v in (0x20,0x21,0x60,0x61,0x40,0x41):
        poke(h,0x3398c,bytes(8))
        poke(h,0x327f0+8*256+2,bytes([v])); poke(h,0x3393c,struct.pack('>L',0x327f0+2))
        time.sleep(1.2)
        d=struct.unpack('>60H',grab(h,0x33944,0x78,'s'))
        s=[(d[0x54//2+i] if d[0x54//2+i]<32768 else d[0x54//2+i]-65536, d[0x6c//2+i], d[0x48//2+i]) for i in range(4) if d[0x48//2+i]]
        print(f"marker {v:02x}: (speed,kind,state) of live slots {s}",flush=True)
        poke(h,0x327f0+8*256+2,bytes([0]))
finally: h.close()
