import sys; sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from e160_lib import *
U=sys.argv[1]; mode=sys.argv[2]; OUT=sys.argv[3]
h=mk(U,'/tmp/ge_67'+mode); t=T(h)
try:
    print('title',h.boot_to_title(timeout=240),flush=True); time.sleep(1)
    if mode=='shots':
        for i in range(14):
            h.shot(f'{OUT}/title_{i:02d}.png'); time.sleep(1.8)
    elif mode=='orig':
        h.key('F10',hold=0.2); time.sleep(2)
        print('manager VBL',hex(struct.unpack('>L',grab(h,0x70,4,'v'))[0]))
        h.shot(f'{OUT}/manager.png')
        t.F(2.0)   # first item = Original game
        print('after fire VBL',hex(struct.unpack('>L',grab(h,0x70,4,'v'))[0]),'rs',t.rs()[:12],flush=True)
        time.sleep(3); h.shot(f'{OUT}/after_orig.png')
        h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0); time.sleep(8)
        h.shot(f'{OUT}/orig_game.png')
        open(f'{OUT}/tower_orig.bin','wb').write(grab(h,0x327f0,0x1000,'tw')); print('rs',t.rs()[:12],'mark',grab(h,0xb0020,6,'mk').hex())
    elif mode=='plain':
        h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0); time.sleep(8)
        h.shot(f'{OUT}/plain_game.png')
        open(f'{OUT}/tower_plain.bin','wb').write(grab(h,0x327f0,0x1000,'tw')); print('rs',t.rs()[:12])
finally: h.close()
