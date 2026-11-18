"""Stage 1 gate: Lift > flow built with the editor on a new level, playtest ride, save + validate."""
from ed import *
import sys, threading, subprocess
sys.path.insert(0,E)
gd=__import__('pathlib').Path
RS=0x77c80
GAMEDIR=sys.argv[1] if len(sys.argv)>1 else '/tmp/ne/g1'
WD=sys.argv[2] if len(sys.argv)>2 else '/tmp/ned140'
MACH=sys.argv[3] if len(sys.argv)>3 else 'ste'
import stharness
kw=dict(machine='megaste',tos=stharness.TOS['2.06'],memsize_kb=4096) if MACH=='megaste' else (dict(machine='st',tos=stharness.TOS['1.04']) if MACH=='st' else {})
h=Nebulus(workdir=WD,game=gd(GAMEDIR),**kw)
def K(k,n=1,hold=0.2,gap=0.4):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def F(gap=0.8): K('Control_R',hold=0.35,gap=gap)
def rs(): return struct.unpack('>20H',grab(h,RS,40,'rs'))
def V(): return struct.unpack('>96H',grab(h,0x77cc0,192,'v'))
def col(c,n=14): g=grab(h,0x327f0+c*256,n,'col'); return ' '.join(f'{b:02x}' for b in g)
def S(tag):
    w=rs(); v=V()
    print(f"{tag:14s} rsEd {w[3]} rsTest {w[4]} cx {w[10]} cy {w[11]} vLift {v[86]} | col2 {col(2,14)}",flush=True)
    h.shot(E+f'e140_{tag}.png')
try:
    print('title',h.boot_to_title(timeout=100),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    K('Down',2); F(1.0); F(1.5)                      # Levels > <new level>
    K('Right',2); K('Up',1); S('cursor22')
    F(); K('Down',4); S('menu_lift'); F(1.0); S('submenu')   # Lift >
    F(1.0); S('from_here')                           # Lift: from here
    K('Right',2); K('Up',8); S('picking')
    F(1.0); S('lift_set')
    # a lift whose end is below: new slab at row 20 via from here, then fire at row 14 (above the first lift's end row 10 is free)
    F(); K('Down',9); S('playtest_item'); F(1.0)         # Playtest
    t0=time.time()
    while time.time()-t0<60:
        time.sleep(1.5)
        if W(h,0x33a20)==0 and W(h,0x33938)==1: break
    K('e',hold=0.3,gap=0.4); K('t',hold=0.3,gap=0.4)
    h.key('Right',hold=0.6); time.sleep(0.5)
    print('frog before ride x %#x y %#x st %d'%(W(h,0x33a16),W(h,0x33a18),W(h,0x33a20)))
    th=threading.Thread(target=lambda:h.key('Up',hold=7)); th.start()
    for i in range(7):
        time.sleep(0.8)
        print(f"ride {i}: x {W(h,0x33a16):#x} y {W(h,0x33a18):#x} st {W(h,0x33a20)} col2 {col(2,14)}",flush=True)
        if i==2: h.shot(E+'e140_ride.png')
    th.join(); time.sleep(8)
    print(f"after ride: x {W(h,0x33a16):#x} y {W(h,0x33a18):#x} st {W(h,0x33a20)} col2 {col(2,14)}")
    h.key('F10',hold=0.5); time.sleep(3); S('back_in_editor')
    h.key('F10',hold=0.5); time.sleep(2); S('level_list')
    # save to a blank campaign disk in drive A:, flush the image by inserting another one, validate the file
    import shutil; shutil.copy('/tmp/ne/d/blank.st','/tmp/ne/d/lift_save_'+MACH+'.st')
    h.cmd('hatari-option --disk-a /tmp/ne/d/lift_save_'+MACH+'.st'); time.sleep(2)
    K('Left',1,gap=1.0)                                  # level list -> main menu (left = < back)
    K('Down',4); F(1.0); F(4.0); time.sleep(1); S('saved_to_disk')
    h.cmd('hatari-option --disk-a /tmp/ne/d/blank.st'); time.sleep(3)
finally: h.close()
os.system(f"cd {E} && python3 ../../tools/nebcampaign.py extract /tmp/ne/d/lift_save_{MACH}.st /tmp/e140_{MACH}.ovl && python3 ovl.py validate /tmp/e140_{MACH}.ovl && python3 ovl.py dump /tmp/e140_{MACH}.ovl | head -20")
