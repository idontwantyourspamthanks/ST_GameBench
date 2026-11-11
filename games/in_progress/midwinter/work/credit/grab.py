import sys, time
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/tools')
from mw1 import MW1, TOS, GAME
from pathlib import Path
game=Path(sys.argv[1]).resolve(); tag=sys.argv[2]; machine=sys.argv[3] if len(sys.argv)>3 else 'ste'
tos=sys.argv[4] if len(sys.argv)>4 else '1.62'; mem=int(sys.argv[5]) if len(sys.argv)>5 else 1024
out=Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/work/credit'); 
h=MW1(game_dir=game,snapshot=None,machine=machine,tos=TOS[tos],memsize_kb=mem)
try:
    print('options', h.boot_to_options())
    time.sleep(3)
    h.shot(str(out/f'{tag}.png'))
    print(h.debug('m $ff8240 32').strip())
    print(h.debug('m $ff8200 16').strip())
    print(h.debug('m $b2ff8 4').strip())
    print(h.debug('m $2c376 12').strip())
    h.debug(f'savebin {out}/{tag}_ram.bin $0 $100000', wait=3)
finally:
    h.close()
