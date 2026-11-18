"""Random-input trials from the pre-window snapshot. usage: r5.py VARIANT N SEED OUT.jsonl
Each trial draws 1-3 input events at uniform random times in [0, 3.0] s after the SR=$2700 window start (pc=$1b172); kinds: space, a, Return, Control_R (joystick fire via --joy1 keys), Right, MOUSE."""
import sys, json, random
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from r2 import trial
variant, n, seed, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
rng = random.Random(seed)
for i in range(n):
    k = rng.choice([1, 1, 2, 3])
    ev = sorted((round(rng.uniform(0.0, 3.0), 2), rng.choice(['space', 'a', 'Return', 'Control_R', 'Right', 'MOUSE'])) for _ in range(k))
    spec = ','.join(f'{t}:{key}:{rng.choice([0.04, 0.08, 0.15])}' for t, key in ev)
    r = trial(variant, spec)
    # window: events with 0 <= t <= 1.3 are inside the SR=$2700 window
    r['in_window'] = any(t <= 1.3 for t, _ in ev)
    print(json.dumps(r), flush=True)
    with open(out, 'a') as f: f.write(json.dumps(r) + '\n')
