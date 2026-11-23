"""End-to-end input latency: host key (xdotool) -> game action, counted in VBLs and presented frames (flips)."""
import sys, json, random
from lib2 import *
EV['WAIT'] = 'pc = $3868a'
BASE2 = ['VBL','POLL','FLIP','CONS','ACIA','STORE','WAIT']

def analyze(toks, act):
    """toks after the first marker M(inject). act = action token ('JUMP','SHOOT','WALK')."""
    try:
        i0 = next(i for i,t in enumerate(toks) if t.startswith('<M'))
    except StopIteration:
        return None
    t = toks[i0+1:]
    # cut at the 2nd marker (release)
    try:
        j = next(i for i,x in enumerate(t) if x.startswith('<M'))
        t = t[:j]
    except StopIteration:
        pass
    vbl = 0; res = {'inject_phase': None}
    seen = {}
    last_poll_vbl = None; last_flip_vbl = None
    first_joy = None
    for k,x in enumerate(t):
        if x == 'VBL': vbl += 1
        elif x == 'S80' and 'joy' not in seen: seen['joy']=vbl
        elif x == 'S1d' and 'key' not in seen: seen['key']=vbl
        elif x == 'POLL': last_poll_vbl = vbl
        elif x == 'FLIP':
            if 'act' in seen and 'flip' not in seen: seen['flip']=vbl
        elif x == act and 'act' not in seen:
            seen['act']=vbl; seen['poll']=last_poll_vbl
    return seen

def run(snap, tag, key_set, act, n=12, mhz=8, hold=0.35, seed=1):
    h = Nebulus(snapshot=snap, workdir='/tmp/strun-nin2e')
    rnd = random.Random(seed); rows=[]
    try:
        time.sleep(1.5)
        if mhz != 8:
            h.set_cpuclock(mhz)
        time.sleep(1.0)
        for k in range(n):
            # wait for ground state
            for _ in range(10):
                if h.peekw(0x33a20) == 0: break
                time.sleep(0.5)
            time.sleep(rnd.uniform(0.05, 0.12))
            acts = [(0.0,'down',key) for key in key_set] + [(hold,'up',key) for key in key_set]
            toks = trial(h, acts, tail=0.9, names=BASE2)
            r = analyze(toks, act)
            rows.append(r); print(tag, k, r, flush=True)
            time.sleep(1.2)
    finally:
        h.close()
    return rows

if __name__ == '__main__':
    snap, tag, keys, act, n, mhz = sys.argv[1], sys.argv[2], sys.argv[3].split(','), sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
    rows = run(snap, tag, keys, act, n, mhz)
    json.dump(rows, open(f'e2e_{tag}.json','w'))
