import sys; sys.path.insert(0,'work/hud'); sys.path.insert(0,'tools')
from hudlab import *
import os
LIVE=Path('work/render/ab/live/edge+map+digit').resolve()
scene=sys.argv[1]; npass=int(sys.argv[2])
for cfg in sys.argv[3:]:
    names=[] if cfg=='stock' else cfg.split('+')
    r=run(scene, skip(*names), npass, state=HUD_STATE, live=LIVE)
    save(r, f"live3_{scene}_{cfg}")
    print(cfg, len(r), 'mean work', sum(x['work'] for x in r.values())/len(r), flush=True)
