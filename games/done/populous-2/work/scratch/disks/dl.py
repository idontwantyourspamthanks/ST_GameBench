
import sys, time, shutil, subprocess, json
from pathlib import Path
G=Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/populous-2')
sys.path[:0]=['/home/ryan/Code/AtariST/gamebench/tools', str(G/'tools')]
from stharness import TOS
from populous2 import Populous2
D=G/'work/scratch/disks'
empty=D/'emptyC'; empty.mkdir(exist_ok=True)
def boot2(img, tag, mem=1024, machine='ste', tos='1.62', second=None, extra=None):
    w=D/'run'; w.mkdir(exist_ok=True)
    cp=w/f'{tag}_a.st'; shutil.copy(img,cp)
    ex=['--disk-a',str(cp),'--protect-floppy','off']
    cp2=None
    if second:
        cp2=w/f'{tag}_b.st'; shutil.copy(second,cp2); ex+=['--disk-b',str(cp2)]
    ex+=extra or []
    h=Populous2(game_dir=empty, machine=machine, tos=TOS[tos], memsize_kb=mem, autorun=None, extra=ex)
    h.cp=cp; h.cp2=cp2; h.tag=tag
    return h
def snap(h,name):
    p=D/'shots'/f'{h.tag}_{name}.png'; h.shot(str(p)); return p

def to_play(h, timeout=300, quest_ok=True):
    r={}
    r['menu']=h.boot_to_menu(timeout)
    if not r['menu']: return r
    snap(h,'menu')
    h._click(384,257,6)           # conquest -> deity
    h._click(260,98,1.0)
    for ch in 'zeus':
        h.key(ch,0.3); time.sleep(0.4)
    h.key('Return',0.3); time.sleep(1.0)
    h._click(424,418,5)           # proceed -> menu
    h._click(384,258,8)           # conquest -> battle sheet
    snap(h,'sheet')
    h._click(216,448,25)          # proceed, load
    snap(h,'afterproceed')
    if not h.in_play():
        h._click(400,420,14)      # manual question OK
    snap(h,'play0')
    r['play']=h.in_play()
    return r
def save_load(h, name='T1'):
    r={}
    time.sleep(10)
    h._click(707,374,3)           # requester
    snap(h,'req')
    r['turn_at_req']=h.peekw(h.TURN)
    h._click(535,178,4)           # SAVE GAME
    snap(h,'save1')
    h._click(470,370,1.0)
    for ch in name:
        h.key(ch.lower(),0.3); time.sleep(0.3)
    h.key('Return',0.3); time.sleep(1)
    snap(h,'save2')
    h._click(288,418,8)           # SAVE
    snap(h,'save3')
    r['after_save_play']=h.in_play()
    time.sleep(12)
    r['turn_before_load']=h.peekw(h.TURN)
    h._click(707,374,3)
    h._click(318,178,4)           # LOAD GAME
    snap(h,'load1')
    h._click(288,418,6)           # LOAD
    snap(h,'load2')
    r['turn_after_load']=h.peekw(h.TURN)
    r['load_play']=h.in_play()
    return r
