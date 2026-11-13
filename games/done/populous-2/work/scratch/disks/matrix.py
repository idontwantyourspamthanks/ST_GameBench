import sys, json
exec(open('/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2/work/scratch/disks/dl.py').read())
import struct
KIND={'ics':dict(vbl=0x18fa,T=0x3979c,drawer=None,quest=True),
      'elite':dict(vbl=0x128d8,T=0x8b41a,drawer='B:',quest=False),
      'sup':dict(vbl=0x13276,T=0x9971c,drawer=None,quest=True)}
def desktop_launch(h):
    time.sleep(10)
    h.goto(394,255,home_xy=(96,58)); time.sleep(0.5); h.click(hold=0.3); time.sleep(1.0)
    h.click(hold=0.3); time.sleep(1.0)
    h.goto(270,67,home_xy=(96,58)); time.sleep(0.5); h.click(hold=0.3); time.sleep(1.0)
    h.goto(290,88,home_xy=(96,58)); time.sleep(0.5); h.click(hold=0.3); time.sleep(4)
def to_menu(h,k,timeout=300):
    t0=time.time(); time.sleep(10)
    while time.time()-t0<timeout:
        h.key('space',0.6); time.sleep(6)
        if h.peekl(0x70)==k['vbl']:
            time.sleep(3); return True
    return False
def run(img, tag, mem, kind, machine='ste', tos='1.62'):
    k=KIND[kind]; res=dict(img=str(img),tag=tag,mem=mem,machine=machine,tos=tos)
    h=boot2(img,tag,mem=mem,machine=machine,tos=tos,second=D/'blank720.st')
    try:
        if kind!='ics': desktop_launch(h)
        res['menu']=to_menu(h,k)
        snap(h,'menu')
        if not res['menu']:
            res['pc']=h.debug('r')[-200:]; return res
        h._click(384,257,6); h._click(260,98,1.0)
        for ch in 'zeus': h.key(ch,0.3); time.sleep(0.4)
        h.key('Return',0.3); time.sleep(1.0)
        h._click(424,418,5); h._click(384,258,8)
        h._click(216,448,10)
        t1=time.time()
        while time.time()-t1<240:
            p=snap(h,'afterproceed')
            from PIL import Image
            im_=Image.open(p).convert('L').crop((96,58,736,458))
            if sum(1 for v in im_.getdata() if v>40)>2000: break
            time.sleep(4)
        time.sleep(6)
        def turn(): return h.peekw(k['T']) if k['T'] else None
        def moving():
            if k['T'] is None:
                from PIL import Image, ImageChops
                pa=snap(h,'m1'); time.sleep(2); pb=snap(h,'m2')
                A=Image.open(pa).convert('L').crop((96,58,736,458)); B=Image.open(pb).convert('L').crop((96,58,736,458))
                return sum(1 for v in ImageChops.difference(A,B).getdata() if v>8)>30
            a=turn(); time.sleep(2); return turn()!=a
        if k['quest'] and not moving():
            h._click(400,420,14)
        res['play']=moving(); snap(h,'play')
        if not res['play']: return res
        time.sleep(8)
        h._click(707,374,3); res['turn_at_save']=turn(); snap(h,'req')
        h._click(535,178,4); snap(h,'save1')
        if k['drawer']:
            h._click(470,338,1.0)
            for ch in ['b','shift+semicolon']: h.key(ch,0.3); time.sleep(0.3)
            h.key('Return',0.3); time.sleep(4)
        h._click(470,370,1.0)
        for ch in 't1': h.key(ch,0.3); time.sleep(0.3)
        h.key('Return',0.3); time.sleep(1)
        h._click(288,418,12); snap(h,'save3')
        res['save_returns_to_play']=moving()
        time.sleep(10); res['turn_before_load']=turn()
        h._click(707,374,3); h._click(318,178,4)
        if k['drawer']:
            h._click(470,338,0.5)
            for i in range(8): h.key('BackSpace',0.2)
            for ch in ['b','shift+semicolon']: h.key(ch,0.3); time.sleep(0.3)
            h.key('Return',0.3); time.sleep(4)
        snap(h,'load1')
        h._click(288,418,10); snap(h,'load3')
        res['turn_after_load']=turn(); res['load_play']=moving()
        h.cmd('hatari-shortcut quit'); time.sleep(3)
        res['dirA']=subprocess.run(['mdir','-i',str(h.cp),'::'],capture_output=True,text=True).stdout[-160:]
        res['dirB']=subprocess.run(['mdir','-i',str(h.cp2),'::'],capture_output=True,text=True).stdout[-160:]
        return res
    except Exception as e:
        res['error']=repr(e); return res
    finally:
        h.close()
if __name__=='__main__':
    img,tag,mem,kind=sys.argv[1:5]
    machine=sys.argv[5] if len(sys.argv)>5 else 'ste'
    tos=sys.argv[6] if len(sys.argv)>6 else '1.62'
    r=run(img,tag,int(mem),kind,machine,tos)
    print('RESULT',json.dumps(r))
