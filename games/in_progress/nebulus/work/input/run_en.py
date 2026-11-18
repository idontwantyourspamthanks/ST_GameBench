"""Enemies-ON latency trials (real host key path). usage: run_en.py <tag> <scen jump|stand> <n> <fixes: none|jump|shoot|jumpshoot|jumpshoot+latch...>
Each Hatari restore (own_tower.sav: level intro, enemies spawning normally) yields up to 3 trials before the frog is hit."""
import sys, json
from tr import *
FIXES = {'none': [], 'jump': ['w $39ffa $60 $2a', 'w $3a024 $4e $71'], 'shoot': ['w $3a332 $4e $71'],
         'jumpshoot': ['w $39ffa $60 $2a', 'w $3a024 $4e $71', 'w $3a332 $4e $71'], 'turn': ['w $39e2c $4e $71']}
def go(tag, scen, n, fix, per=3, seed=3):
    rnd = random.Random(seed); runs = []
    while len(runs) < n:
        h = Nebulus(snapshot='snap/own_tower.sav', workdir='/tmp/strun-nin2e')
        try:
            for c in FIXES[fix]: h.debug(c, 0.2)
            # wait for the level to start: timer words ticking and state 0
            t0 = time.time()
            while time.time() - t0 < 20:
                if h.peekw(0x3ad98) != 0 and h.peekw(0x33a20) == 0 and h.peekw(0x3ad9c) not in (0,): break
            for k in range(per):
                if len(runs) >= n: break
                if h.peekw(0x33a20) != 0: time.sleep(0.8)
                if h.peekw(0x33a20) != 0 or h.peekw(0x3ad98) == 0: break
                time.sleep(rnd.uniform(0.15, 0.45))
                if scen == 'jump':
                    acts = [(0.0,'down','Right'), (0.3 + rnd.uniform(0, 0.04), 'down', 'Control_R'), (0.3, 'up', 'Control_R'), (0.0, 'up', 'Right')]
                elif scen == 'turn':
                    acts = [(0.0,'down','Left'), (0.4, 'up', 'Left')]
                else:
                    acts = [(0.0,'down','Control_R'), (0.3, 'up', 'Control_R')]
                order = arm(h, ['POLL','FLIP','STORE','ACIA'], [('JUMP','pc = $39fc8'),('SHOOT','pc = $3a2f8'),('JUMPB','pc = $39ffc'),('TURN','pc = $39e1e')])
                n0 = len(h._logtext())
                marker(h)
                for dt, op, key in acts:
                    time.sleep(dt); h._xdo('key'+op, '--window', h.win, key); marker(h)
                time.sleep(1.3)
                marker(h); time.sleep(0.4)
                txt = h._logtext()[n0:]
                h.debug('b all', 0.3)
                runs.append(parse(txt, order, 1)); print(tag, len(runs), len(runs[-1]), flush=True)
                time.sleep(0.6)
        finally:
            h.close()
    json.dump(runs, open(f'raw_{tag}.json', 'w'))
if __name__ == '__main__':
    go(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
