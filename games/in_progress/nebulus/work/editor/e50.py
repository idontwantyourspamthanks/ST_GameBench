from ed import *
import sys
sys.path.insert(0,E)
from stharness import TOS
gd=__import__('pathlib').Path
RS=0x77c80
machine=sys.argv[1] if len(sys.argv)>1 else 'megaste'
kw=dict(machine='megaste',tos=TOS['2.06'],memsize_kb=4096) if machine=='megaste' else {}
wd=f'/tmp/ned50_{machine}'
h=Nebulus(workdir=wd,game=gd(E+'build_final'),**kw)
def K(k,n=1,hold=0.2,gap=0.4):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def F(gap=0.8): K('Control_R',hold=0.35,gap=gap)
def rs(): return struct.unpack('>20H',grab(h,RS,40,'rs'))
try:
    print('title',h.boot_to_title(timeout=160),flush=True); time.sleep(3)
    print('marker',grab(h,0xB0020,4),'store',grab(h,0xBC000,8).hex(' '),'copy addr $ffd80',hex(L(h,0xffd80)))
    h.key('F10',hold=0.5); time.sleep(2); h.shot(E+f'e50_{machine}_main.png')
    K('Down'); F(1.0)                      # campaigns list
    K('Down'); F(1.0)                      # <new campaign> -> entry editor of the new campaign
    h.shot(E+f'e50_{machine}_newcamp.png')
    F(1.0)                                 # <add entry>
    K('Down'); F(1.0)                      # < back (list of entries has 1 entry + add + back: sel moves)
    h.shot(E+f'e50_{machine}_after_add.png')
    print('store header',grab(h,0xBC000,16).hex(' '))
    time.sleep(1)
finally:
    pass
try:
    # back to main: Down to '< back' in campaign list then Save
    K('Down',3); F(1.0); h.shot(E+f'e50_{machine}_main2.png')
    K('Down',3); F(1.0); time.sleep(4); h.shot(E+f'e50_{machine}_saved.png')
    print('vErr',hex(L(h,0x77cf4)))
finally: h.close()
os.system(f"cd {wd}; mcopy -n -o -i hd.img@@1024 ::NEBLEVEL.OVL /tmp/e50_{machine}.ovl && python3 {E}ovl.py dump /tmp/e50_{machine}.ovl")
