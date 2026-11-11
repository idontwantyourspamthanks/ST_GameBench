import sys,time; sys.path.insert(0,'tools')
from pathlib import Path
from mw2harness import Hatari
h=Hatari(snapshot=None,memsize_kb=1024,game_dir=Path('build/game'),machine='falcon',tos=Path('/usr/lib/pist/share/emutos/etos1024k.img'))
try:
    time.sleep(60); h.shot('work/regress/falcon_probe.png'); print(h.debug('m $b2ff8 4'))
finally: h.close()
