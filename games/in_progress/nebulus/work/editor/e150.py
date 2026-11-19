"""Stage 2 gate: keyboard shortcuts in the edit view, trainer flags never change there, keys do not leak into the playtest, T/E work in the playtest."""
from ed import *
import sys
sys.path.insert(0,E)
gd=__import__('pathlib').Path
RS=0x77c80
GAMEDIR=sys.argv[1] if len(sys.argv)>1 else '/tmp/ne/g2'
WD=sys.argv[2] if len(sys.argv)>2 else '/tmp/ned150'
MACH=sys.argv[3] if len(sys.argv)>3 else 'ste'
kw=dict(machine='megaste',tos=__import__('stharness').TOS['2.06'],memsize_kb=4096) if MACH=='megaste' else (dict(machine='st',tos=__import__('stharness').TOS['1.04']) if MACH=='st' else {})
h=Nebulus(workdir=WD,game=gd(GAMEDIR),**kw)
def K(k,n=1,hold=0.1,gap=0.25):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def F(gap=0.8): K('Control_R',hold=0.35,gap=gap)
def rs(): return struct.unpack('>32H',grab(h,RS,64,'rs'))
def blob(): return grab(h,0x76c00,6,'nt').hex()
def cell(c,r): return grab(h,0x327f0+c*256+r,1,'c')[0]
def colv(c,r0,n): return ' '.join(f'{b:02x}' for b in grab(h,0x327f0+c*256+r0,n,'col'))
def msg(): return struct.unpack('>L',grab(h,0x77cc0+20,4,'m'))[0]
fails=[]
def chk(name,got,exp):
    ok=(got==exp); print(f"{'PASS' if ok else 'FAIL'} {name}: got {got} expected {exp}",flush=True)
    if not ok: fails.append(name)
try:
    print('title',h.boot_to_title(timeout=140),flush=True); time.sleep(3)
    print('blob at title (prev,pad frz noen):',blob()); b0=blob()
    h.key('F10',hold=0.5); time.sleep(2)
    K('Down',2,hold=0.2,gap=0.4); F(1.0); F(1.5)          # Levels > <new level>
    print('in editor:',rs()[3:5],rs()[10:12]); 
    K('Up',9)                                             # cursor row 10
    # T and E in the edit view (must not toggle trainers), then every shortcut key at its own column
    K('t'); K('e'); K('t'); K('e')
    chk('blob after T,E,T,E in edit view',blob(),b0)
    keys=['l','p','b','d','x','s','r','w','u','i','j','k','c']
    for k in keys: K(k); K('Right')
    exp={'l':0x81,'p':0x80,'b':0x82,'d':0,'x':0xc3,'s':0x10,'r':0x20,'w':0x30,'u':0x40,'i':0x50,'j':0x60,'k':0x70,'c':0}
    for i,k in enumerate(keys): chk(f'key {k} -> (col {i},row 10)',cell(i,10),exp[k])
    chk('door x3 col 3 rows 10..12: the first cell was overwritten by the eye k at (11,10) = its OPPOSITE cell (NebDoors: clearing/overwriting one door cell clears the partner)',colv(3,10,3),'00 83 83'); chk('opposite door col 11 rows 11..12 (row 10 holds the eye)',colv(11,10,3),'70 83 83'); chk('exit x3 col 4 rows 10..12',colv(4,10,3),'c3 c3 c3')
    # direction flip: s again at col 5
    K('Left',8); K('s'); chk('s again flips (col 5)',cell(5,10),0x11); K('s'); chk('s again flips back',cell(5,10),0x10)
        # repeat last: l at col 13, Return at 14, Space at 15
    K('Right',8); K('l'); K('Right'); K('Return'); K('Right'); K('space')
    chk('l, Return, space -> cols 13,14,15',[cell(13,10),cell(14,10),cell(15,10)],[0x81,0x81,0x81])
    K('Delete'); chk('Delete clears (col 15)',cell(15,10),0)   # Delete = clear key
    print('every key done; blob:',blob()); chk('blob after all shortcut keys',blob(),b0)
    h.shot(E+'e150_keys.png')
    def goto(c,r):
        w=rs(); cx,cy=w[10],w[11]
        dx=(c-cx)%16
        if dx>8: K('Left',16-dx)
        else: K('Right',dx)
        if r>cy: K('Up',r-cy)
        elif r<cy: K('Down',cy-r)
        w=rs(); print('  at',w[10],w[11])
    goto(2,2); K('a'); print('vLift',struct.unpack('>H',grab(h,0x77cc0+172,2,'vl'))[0]); goto(2,8); K('Return')
    chk('lift via a / Up / Return: col 2 rows 0..9',colv(2,0,10),'00 81 85 00 00 00 00 00 08 00')
    goto(2,5); K('z'); chk('z = lift stop (col 2 row 5)',cell(2,5),0x0c)
    goto(15,14); K('a'); goto(15,8); K('space')
    chk('lift end picked below: col 15 rows 6..14',colv(15,6,9),'00 81 85 00 00 00 00 00 08')
    goto(6,6); K('p'); goto(6,2); K('a'); goto(6,9); K('Return')
    chk('pillar-blocks-lift warning set (vMsg != 0)',msg()!=0,True); h.shot(E+'e150_pillar_warning.png')
    chk('col 6 rows 1..9',colv(6,1,9),'81 85 00 00 00 80 00 00 08')
    h.shot(E+'e150_lifts.png')
    # keys that are not shortcuts + every shortcut once more, then straight into the playtest  (N / M became the conveyor shortcuts in the conveyor build: e208.py gates them)
    for k in ['q','y','f','g','h','o','v','t','e']: K(k)
    for k in keys: K(k)
    chk('blob after unmapped + shortcut keys',blob(),b0)
    F(); import ui; ui.select(h,'Playtest',1.0); h.shot(E+'e150_menu_playtest.png')             # Playtest (by label: the root menu has grown since HEAD)
    t0=time.time()
    while time.time()-t0<60:
        time.sleep(1.5)
        if W(h,0x33a20)==0 and W(h,0x33938)==1: break
    ta=grab(h,0x3ad98,6).hex(); time.sleep(3); tb=grab(h,0x3ad98,6).hex()
    chk('playtest running, not paused/quit (timer moves)',ta!=tb,True); print('  timer',ta,tb,'blob',blob())
    chk('trainer flags still 0 on entering the playtest',blob()[4:],'00000000')
    K('e'); K('t'); b1=blob(); print('  blob after e,t in the playtest',b1)
    chk('T/E work in the playtest',b1[4:],'ffffffff')
    h.key('F10',hold=0.5); time.sleep(3)
    print('  back in editor',rs()[3:5])
    K('t'); K('e'); K('t'); K('e'); K('t')
    chk('T/E keys in the edit view after the playtest do not toggle',blob()[4:],'ffffffff')
    h.shot(E+'e150_back.png')
finally:
    pass
print('FAILS',fails)
h.close()
