"""grab2.py KIND DIR TAG [MACHINE TOS MEM]: KIND hd (game dir) | fl (dir with MWA.st MWB.st).
Boots to the Game Options screen, saves screenshot, palette, displayed screen base, full RAM to work/credit/TAG.*"""
import sys, time, shutil, tempfile, re, json
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/done/midwinter/tools')
from mw1harness import MW1, TOS, REF
from pathlib import Path
kind, d, tag = sys.argv[1:4]
machine=sys.argv[4] if len(sys.argv)>4 else 'ste'
tos=sys.argv[5] if len(sys.argv)>5 else '1.62'
mem=int(sys.argv[6]) if len(sys.argv)>6 else 1024
out=Path('/home/ryan/Code/AtariST/gamebench/games/done/midwinter/work/credit')
if kind=='hd':
    h=MW1(game_dir=Path(d).resolve(),snapshot=None,machine=machine,tos=TOS[tos],memsize_kb=mem)
else:
    scratch=Path(tempfile.mkdtemp(prefix='mw1fl-'))
    for s,t in (('MWA.st','mwboot.st'),('MWB.st','mwgfx.st')): shutil.copy(Path(d)/s, scratch/t)
    (scratch/'empty').mkdir()
    h=MW1(game_dir=scratch/'empty',snapshot=None,machine=machine,tos=TOS[tos],memsize_kb=mem,autorun='',extra=['--disk-a',str(scratch/'mwboot.st')])
try:
    if kind=='hd':
        ok=h.boot_to_options()
    else:
        t0=time.time(); ok=False; swapped=False
        while time.time()-t0<300:
            time.sleep(4)
            if h.at_options(): ok=True; break
            if not swapped and h.matches(REF/'insert_graphics.png',(320,255,510,285)):
                h.cmd(f"hatari-option --disk-a {scratch/'mwgfx.st'}"); time.sleep(2); swapped=True
            if time.time()-t0>20: h.keypress(57)
    print('options',ok, flush=True)
    if not ok:
        h.shot(str(out/f'{tag}_fail.png')); sys.exit(1)
    time.sleep(3)
    h.shot(str(out/f'{tag}.png'))
    pal=h.debug('m $ff8240 32').strip(); vid=h.debug('m $ff8200 16').strip(); mk=h.debug('m $b2ff8 4').strip()
    print(pal); print(vid); print(mk)
    m=re.search(r'00FF8200: (\w\w) (\w\w) (\w\w) (\w\w)',vid)
    base=(int(m.group(2),16)<<16)|(int(m.group(4),16)<<8)
    (out/f'{tag}.base').write_text(hex(base))
    print('base',hex(base))
    h.debug(f'savebin {out}/{tag}_ram.bin $0 ${mem*1024:x}', wait=3)
finally:
    h.close()
