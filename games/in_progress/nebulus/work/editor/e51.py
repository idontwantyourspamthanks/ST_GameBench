from ed import *
import sys
from stharness import TOS
gd=__import__('pathlib').Path
machine=sys.argv[1] if len(sys.argv)>1 else 'megaste'
kw=dict(machine='megaste',tos=TOS['2.06'],memsize_kb=4096) if machine=='megaste' else {}
wd=f'/tmp/ned51_{machine}'
h=Nebulus(workdir=wd,game=gd(E+'build_final'),**kw)
def K(k,n=1,hold=0.2,gap=0.4):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def F(gap=0.8): K('Control_R',hold=0.35,gap=gap)
try:
    print('title',h.boot_to_title(timeout=160),flush=True); time.sleep(3)
    poke(h,0xBC00A,bytes([0xAB,0xCD]))
    h.key('F10',hold=0.5); time.sleep(2)
    K('Down',3); h.shot(E+f'e51_{machine}_sel.png'); F(1.0); time.sleep(4); h.shot(E+f'e51_{machine}_saved.png')
    print('vErr',hex(L(h,0x77cf4)),'msg',hex(L(h,0x77cdc)))
    # the game must still be healthy: leave the manager (Original game = sel 0) and look at the title
    K('Up',3); F(1.0); time.sleep(3); h.shot(E+f'e51_{machine}_title_after.png')
    print('vbl advancing:',h.vbl(),h.vbl())
finally: h.close()
os.system(f"cd {wd}; mcopy -n -o -i hd.img@@1024 ::NEBLEVEL.OVL /tmp/e51_{machine}.ovl; xxd -l 16 /tmp/e51_{machine}.ovl; ls -l /tmp/e51_{machine}.ovl")
