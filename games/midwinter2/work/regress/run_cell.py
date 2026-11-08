import sys, json, time, traceback
from pathlib import Path
sys.path.insert(0,'tools')
from mw2harness import Hatari
B=Path.home()/"Emulators/BIOS/AtariST"
TOS={'162':B/"TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img",
     '104':B/"TOS v1.04 (1989)(Atari Corp)(Mega ST)(GB)[Rainbow TOS].img",
     'etos':Path("/usr/lib/pist/share/emutos/etos1024k.img")}
name,machine,tos,mem,game,clk=sys.argv[1:7]
out=Path('work/regress'); res={'cell':name,'log':[]}
def L(*a):
    s=' '.join(str(x) for x in a); res['log'].append(s); print(s,flush=True)
h=None
import os
_ox,_oy=[int(v) for v in os.environ.get('OFFS','0,0').split(',')]
def _sm(self,ref,box,tol=8.0):
    from PIL import Image, ImageChops, ImageStat
    global _ox,_oy
    full=Image.open(self.shot()).convert('RGB'); r=Image.open(ref).convert('RGB')
    def df(ox,oy):
        c=full.crop((box[0]+ox,box[1]+oy,box[2]+ox,box[3]+oy))
        return sum(ImageStat.Stat(ImageChops.difference(c,r)).mean)/3
    if os.environ.get('AUTO') and df(_ox,_oy)>=tol:
        for ox in range(_ox-4,_ox+5):
            for oy in range(_oy-6,_oy+7):
                if df(ox,oy)<1: _ox,_oy=ox,oy; L('locked offset',ox,oy); return True
    return df(_ox,_oy)<tol
Hatari.screen_matches=_sm
try:
    h=Hatari(snapshot=None,memsize_kb=int(mem),game_dir=Path(game),machine=machine,tos=TOS[tos])
    import os
    if os.environ.get('LONG'):
        ref=Path('work/ref/mode_select.png'); time.sleep(25)
        for i in range(180):
            h.cmd("hatari-event keypress 57"); time.sleep(5)
            if h.screen_matches(ref,(280,350,560,420)): L('MJK reached after poll',i); break
        else: L('MJK not reached in 15 min'); h.shot(Path('work/regress')/f'{name}_long_exc.png')
    try:
        p=h.boot_to_game('M')
    except Exception as e:
        L('boot try1 failed:',e)
        if os.environ.get('RECOVER'):
            h.shot(Path('work/regress')/f'{name}_stuck.png')
            for _ in range(4):
                h.goto(140,415); h.click(); time.sleep(10)
                h.goto(625,92); h.click(); time.sleep(40)
                if h.peekw(0x6220)==0xD and h.peekw(0x700a)==2: break
            h.center(); p=h.shot(); L('recovered, 6220=%x'%h.peekw(0x6220))
        else:
            h.close()
            h=Hatari(snapshot=None,memsize_kb=int(mem),game_dir=Path(game),machine=machine,tos=TOS[tos])
            p=h.boot_to_game('M')
    import shutil; shutil.copy(p,out/f'{name}_3d.png'); L('3D view shot',out/f'{name}_3d.png')
    L('6220=%x 700a=%x'%(h.peekw(0x6220),h.peekw(0x700a)))
    L('MWPO check',h.debug('m $b2ff8 4'))
    if clk!='0': h.set_cpuclock(int(clk))
    h.rel(0,-200); h.center(); h.rel(0,-200); time.sleep(10)
    L('speed shot',h.shot(out/f'{name}_walk.png'))
    r=h.world_rate(vbls=500); L('world_rate',r)
    L('x66e6=%x 6888=%d'%(h.peekw(0x66e6),h.peekw(0x6888)))
    h.center(); time.sleep(1)
    hd=[h.peekw(0x6742)]; L('heading before',hex(hd[0]))
    h.rel(-150,0)
    for i in range(8):
        time.sleep(1.5); hd.append(h.peekw(0x6742))
    L('heading series',[hex(x) for x in hd])
    h.shot(out/f'{name}_turned.png')
except Exception as e:
    L('EXC',repr(e)); L(traceback.format_exc())
    try: h.shot(out/f'{name}_exc.png')
    except Exception: pass
finally:
    if h: res['workdir']=str(h.R); h.close()
    (out/f'{name}.json').write_text(json.dumps(res,indent=1,default=str))
