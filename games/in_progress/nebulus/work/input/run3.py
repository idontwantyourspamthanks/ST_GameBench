"""Latency trials. usage: run3.py <tag> <scenario> <n> <mhz> <fix: none|deadloop|...>
scenarios: jump (Right held, fire pressed at random phase), walk (Right pressed from standing), stand (fire pressed standing)."""
import sys, json
from tr import *
FIXES = {
    'none': [],
    # run the jump-state handler in the same loop the state is set (rts -> bra.s/nop falling into $3a026)
    'deadloop': ['w $39ffa $60 $2a', 'w $3a024 $4e $71'],
}
def apply(h, fix):
    for c in FIXES[fix]:
        h.debug(c, 0.3)
    for a in (0x39ffa, 0x3a024):
        h.debug(f'm ${a:x} 2', 0.3)

def go(tag, scen, n, mhz, fix, snap='snap/play_noenemy.sav', seed=11):
    h = Nebulus(snapshot=snap, workdir='/tmp/strun-nin2e')
    rnd = random.Random(seed); runs = []
    try:
        time.sleep(1.5)
        if mhz != 8: h.set_cpuclock(mhz)
        time.sleep(1.0)
        apply(h, fix)
        for k in range(n):
            for _ in range(15):
                if h.peekw(0x33a20) == 0: break
                time.sleep(0.4)
            time.sleep(rnd.uniform(0.2, 0.5))
            if scen == 'jump':
                acts = [(0.0,'down','Right'), (0.3 + rnd.uniform(0, 0.04), 'down', 'Control_R'), (0.35, 'up', 'Control_R'), (0.15, 'up', 'Right')]
            elif scen == 'walk':
                acts = [(0.0,'down','Right'), (0.4, 'up', 'Right')]
            else:
                acts = [(0.0,'down','Control_R'), (0.35, 'up', 'Control_R')]
            ev = capture(h, acts, names=['POLL','FLIP','STORE','ACIA'],
                         extra=[], tail=0) if False else None
            order = arm(h, ['POLL','FLIP','STORE','ACIA'], [('JUMP','pc = $39fc8'),('SHOOT','pc = $3a2f8'),('JUMPB','pc = $39ffc')])
            n0 = len(h._logtext())
            marks=[]
            marker(h)
            for dt, op, key in acts:
                time.sleep(dt)
                marker(h)                       # just before the host key event
                h._xdo('key'+op, '--window', h.win, key)
                marker(h)                       # just after
            time.sleep(1.4 if scen=='jump' else 0.8)
            marker(h); time.sleep(0.4)
            txt = h._logtext()[n0:]
            h.debug('b all', 0.3)
            runs.append(parse(txt, order, 1))   # fpc=1: keep (vbl, fc) raw; T recomputed below
            print(tag, k, len(runs[-1]), flush=True)
    finally:
        h.close()
    json.dump(runs, open(f'raw_{tag}.json','w'))
    return runs

if __name__=='__main__':
    tag, scen, n, mhz, fix = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    go(tag, scen, n, mhz, fix)
