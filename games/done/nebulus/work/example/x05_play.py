"""play a level from its start snapshot with a plan; print a trace, the final state, screenshots.
usage: x05_play.py LEVEL(spiral|lifts|blocks) SNAP WD GAMEDIR [E] [T] [tail]"""
import sys, threading; sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/example')
from drv import *
import plan
lvl, snap, wd, gd = sys.argv[1:5]; tr = tuple(a for a in sys.argv[5:] if a in ('E', 'T'))
r = Run(snap, wd, gd, trainers=tr)
stop = False
def shots():
    n = 0
    while not stop:
        time.sleep(float(os.environ.get('SHOTEVERY', '12')))
        try: r.h.shot(X + f'play_{lvl}_{n:02d}.png'); n += 1
        except Exception as e: print('shot failed', e)
th = threading.Thread(target=shots, daemon=True); th.start()
try:
    ev = getattr(plan, lvl)()
    ok, fl, txt = r.go(ev, max_wait=float(os.environ.get('MAXWAIT', '600')), tail=float(os.environ.get('TAIL', '3')))
    stop = True
    print('chain finished', ok, 'flips', len(fl))
    import json; json.dump(fl, open(X + f'trace_{lvl}.json', 'w'))
    prev = None
    for i, f in enumerate(fl):
        key = (f['st'], f['y'] // 4 if f['st'] == 0 else 0)
        if i % 25 == 0 or i == len(fl) - 1: print(i, {k: f.get(k) for k in ('x', 'y', 'st', 'stp', 't', 'tower', 'done', 'rs')})
    r.h.shot(X + f'play_{lvl}_end.png')
finally:
    stop = True; r.close()
