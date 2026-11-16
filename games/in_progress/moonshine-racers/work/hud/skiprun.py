"""Skip experiments: python3 work/hud/skiprun.py SCENE NPASS CONFIG...  (config = + joined call names, 'stock' = none)
Saves work/hud/res/skip_<scene>_<config>.json (stage cycles per pass + state subset) and a full gate-state pickle + shots."""
import sys, pickle
sys.path.insert(0, 'work/hud')
from hudlab import *

def go(scene, npass, cfg, at_pass=None, shots=(), gate=True, tag=None):
    names = [] if cfg == 'stock' else cfg.split('+')
    pk = skip(*names)
    tag = tag or f"{scene}_{cfg}"
    r = run(scene, pk, npass, state=GATE_STATE if gate else HUD_STATE, at_pass=at_pass, shots_at=shots, shotdir=OUT / 'res' / f'shots_{tag}')
    save(r, f"skip_{tag}")
    if gate:
        pickle.dump({k: bytes(m.get(a, 0) for a in sorted(m)) if False else m for k, m in r.state.items()}, open(OUT / 'res' / f"gate_{tag}.pkl", 'wb'))
    return r

if __name__ == '__main__':
    scene, npass = sys.argv[1], int(sys.argv[2])
    for cfg in sys.argv[3:]:
        import os
        sh = tuple(int(x, 16) for x in os.environ.get('SHOTS', '').split(',') if x)
        r = go(scene, npass, cfg, shots=sh)
        print(cfg, len(r), 'passes', f"mean work {sum(x['work'] for x in r.values())/len(r):,.0f}", flush=True)
