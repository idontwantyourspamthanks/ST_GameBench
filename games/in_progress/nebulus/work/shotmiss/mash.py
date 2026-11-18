"""Tower-1 situation, sim (Hatari-validated engine): frog on the ledge at x=106 (right of the stack), 2-block stack at col 12, ball waiting at its marker x=76 (hop phase varies),
fire pressed every 6 loops (a player tapping fire).  Per shot: what it hit.  Counts over all 11 hop phases x 6 tap phases, stock vs np_shot."""
import sys, collections
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
from hatt import *
def play(cnt, tap_phase, fixes, fx=106, nloops=150, period=6, bx=76):
    s = Sim(BASE); pr = Probe(s)
    for a, b in fixes: s.uc.mem_write(a, bytes(b))
    for a, b in attempt_pokes(dict(bx=bx, cnt=cnt, spd=0, fx=fx), stack=True): s.uc.mem_write(a, b)
    for a, b in TIMER_POKE: s.uc.mem_write(a, b)
    events = []; shots = 0; stack_gone = None; ball_dead = None; frog_hit = None; prev_sst = 0
    for i in range(nloops):
        s.wb(0x38498, 0x80 if (i - tap_phase) % period in (0, 1) and i >= tap_phase else 0)
        pr.rows.clear(); loop(s, extra=True)
        b0 = slot(s, 0); sh = slot(s, SHOT)
        if prev_sst == 0 and sh['st'] == 1: shots += 1; events.append(['shot%d' % shots, i, sh['x']])
        if sh['st'] == 0 and prev_sst == 1: events[-1] += ['ended x=%d' % sh['x'], 'ball x=%d y=%d' % (b0['x'], b0['y']), 'ball_st=%d' % b0['st'], 'hits=%s' % [h for h, _, _ in pr.rows]]
        prev_sst = sh['st']
        if stack_gone is None and s.rb(cell(12, 15)) == 0: stack_gone = i
        if ball_dead is None and b0['st'] in (4, 5): ball_dead = (i, shots)
        if frog_hit is None and s.rw(PST) == 7: frog_hit = i
        if ball_dead and i > ball_dead[0] + 2: break
    return dict(shots=shots, stack_gone=stack_gone, ball_dead=ball_dead, frog_hit=frog_hit, events=events)
if __name__ == '__main__':
    for name, fixes in (('stock', []), ('np_shot', VARIANT['fix'])):
        res = collections.Counter(); shots_to_kill = []
        for cnt in range(11):
            for tp in range(6):
                r = play(cnt, tp, fixes)
                res['ball killed' if r['ball_dead'] else ('frog hit first' if r['frog_hit'] else 'ball alive at end')] += 1
                if r['ball_dead']: shots_to_kill.append(r['ball_dead'][1])
        print(name, dict(res), 'shots fired until the ball died (killed runs): mean %.2f max %d' % (sum(shots_to_kill) / max(1, len(shots_to_kill)), max(shots_to_kill or [0])))
    r = play(0, 0, [])
    print('example run (stock, hop phase 0, tap phase 0):'); [print('  ', e) for e in r['events']]; print('  stack gone at loop', r['stack_gone'], 'ball dead', r['ball_dead'], 'frog hit', r['frog_hit'])
