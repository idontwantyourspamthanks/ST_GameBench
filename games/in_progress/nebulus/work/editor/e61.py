from ed import *
import re
gd=__import__('pathlib').Path
h=Nebulus(workdir='/tmp/ned61',game=gd(E+'build_final'))
try:
    print('in tower',h.boot_to_game(timeout=120),flush=True); time.sleep(3)
    while W(h,0x33a20)!=0: time.sleep(0.5)
    poke(h,0x3a4e6,bytes([0x4e,0x75]))
    for c,r in [(8,5),(9,10),(9,15),(7,20),(12,20)]: poke(h,0x327f0+c*256+r,bytes([0]))
    cmdf='/tmp/bp61.txt'; open(cmdf,'w').write("m $33998 2\nm $3399a 2\n")
    for v in (0x20,0x21,0x10,0x11,0x60,0x61,0x40,0x41,0x30,0x31):
        poke(h,0x3398c,bytes(8))
        h.debug('b all',0.3)
        n=len(open('/tmp/ned61/log.txt',errors='replace').read())
        h.cmd(f"hatari-debug b pc = $37a98 :once :trace :file {cmdf}")
        time.sleep(0.3)
        poke(h,0x327f0+8*256+2,bytes([v])); poke(h,0x3393c,struct.pack('>L',0x327f0+2))
        time.sleep(2.0)
        log=open('/tmp/ned61/log.txt',errors='replace').read()[n:]
        m=re.findall(r"00033998:\s+([0-9a-f]{2}) ([0-9a-f]{2})",log,re.I)
        print(f"marker {v:02x}: slot0 speed word at spawn =",m[-1] if m else None,flush=True)
        poke(h,0x327f0+8*256+2,bytes([0]))
finally: h.close()
