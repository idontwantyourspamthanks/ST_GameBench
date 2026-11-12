"""gate_play.py GAMEDIR TAG [machine tos mem]: cold boot, Game Options, toggle every option (screenshot after each click: the credit must
survive the redraw), PLAY -> Team -> Stark -> Decisions -> Skiing; prints marker, options flags, ski state."""
import sys, time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/done/midwinter/tools')
from mw1 import *
from pathlib import Path
from PIL import Image
game=Path(sys.argv[1]).resolve(); tag=sys.argv[2]
machine=sys.argv[3] if len(sys.argv)>3 else 'ste'; tos=sys.argv[4] if len(sys.argv)>4 else '1.62'; mem=int(sys.argv[5]) if len(sys.argv)>5 else 1024
out=Path('/home/ryan/Code/AtariST/gamebench/games/done/midwinter/work/credit')
h=MW1(game_dir=game,snapshot=None,machine=machine,tos=TOS[tos],memsize_kb=mem)
def credit_px(png):
    im=Image.open(png).convert('RGB')
    # credit rect in screenshot coordinates: ST x 9..65, y 180..197 -> (96+2x, 58+2y)
    n=0
    for y in range(58+2*180,58+2*198):
        for x in range(96+2*9,96+2*66):
            if im.getpixel((x,y))!=(0,0,0): n+=1
    return n
try:
    print('options', h.boot_to_options(), flush=True)
    print('marker', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    time.sleep(2); h.shot(str(out/f'{tag}_t0.png')); print('credit px (screenshot) at start:', credit_px(out/f'{tag}_t0.png'))
    seq=[('J',MODE_XY['J']),('K',MODE_XY['K']),('M',MODE_XY['M']),('mortars',MORTARS_XY),('bombers',BOMBERS_XY),('training',TRAINING_XY)]
    for i,(nm,xy) in enumerate(seq,1):
        h.click_at(xy, 2.0); time.sleep(2); h.shot(str(out/f'{tag}_t{i}.png'))
        print(f'after click {nm}: credit px', credit_px(out/f'{tag}_t{i}.png'), h.options_flags(), h.control_mode(), flush=True)
    # final state like boot_to_game default: mortars/bombers OFF, training ON
    for want, xy, key in ((False, MORTARS_XY,'mortars'),(False, BOMBERS_XY,'bombers')):
        pass
    fl=h.options_flags(); print('flags before PLAY', fl)
    # bring to mortars off, bombers off, training on
    for key,xy,want in (('mortars',MORTARS_XY,False),('bombers',BOMBERS_XY,False),('training',TRAINING_XY,True)):
        if fl[key]!=want: h.click_at(xy,2.0)
    fl=h.options_flags(); print('flags set', fl)
    h.click_at(PLAY_XY, 12); h.click_at(STARK_XY, 6); h.click_at(DECISIONS_XY, 6); h.click_at(SKIING_XY, 10); h.center()
    print('marker', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    print('gstate', h.gstate()); print('in_ski', h.in_ski())
    h.shot(str(out/f'{tag}_ski.png'))
finally:
    h.close()
