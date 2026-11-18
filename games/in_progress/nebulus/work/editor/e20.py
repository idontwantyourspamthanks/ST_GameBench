from ed import *
import shutil, sys
sys.path.insert(0,E)
import ovl
mode=sys.argv[1]     # test4 | zero | absent
machine=sys.argv[2] if len(sys.argv)>2 else 'ste'
gd=Path=__import__('pathlib').Path
src=gd(E+'build_ed'); dst=gd(f'/tmp/gd_{mode}_{machine}')
if dst.exists(): shutil.rmtree(dst)
shutil.copytree(src,dst)
if mode=='test4': shutil.copy('/tmp/test4.ovl',dst/'NEBLEVEL.OVL')
elif mode=='zero': (dst/'NEBLEVEL.OVL').write_bytes(bytes(4096))
kw={}
if machine=='megaste':
    from stharness import TOS
    kw=dict(machine='megaste',tos=TOS['2.06'],memsize_kb=4096)
h=Nebulus(workdir=f'/tmp/ned20_{mode}_{machine}',game=dst,**kw)
try:
    ok=h.boot_to_game(shots=gd(E+f'shots_{mode}_{machine}'),timeout=120)
    print('in tower',ok,flush=True)
    time.sleep(1)
    print('marker',grab(h,0xB0020,4),'nsites',W(h,0xB0024))
    st=grab(h,0x75730,16); print('store',st.hex(' '))
    g=grab(h,0x327f0,0x1000)
    print('rows $33912',W(h,0x33912),'tower',W(h,0x3390c),'mission',W(h,0x33910))
    open(f'/tmp/grid_{mode}_{machine}.bin','wb').write(g)
    print('cells (3,1) (4,1) (3,2) (4,2):',[hex(g[c*256+r]) for c,r in [(3,1),(4,1),(3,2),(4,2)]])
    og,rows=ovl.original(1,0)
    diff=[(a,r) for a in range(16) for r in range(rows+1) if g[a*256+r]!=(og[a][r] if r<len(og[a]) else 0)]
    print('cells differing from stock decode:',diff)
    h.shot(E+f'e20_{mode}_{machine}.png')
finally: h.close()
