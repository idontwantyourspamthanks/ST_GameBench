import sys, time
sys.path.insert(0, 'tools')
from stharness import Hatari

def read_counts(h):
    raw = h.debug('m $25dde 16', wait=0.3)
    for line in raw.splitlines():
        if line.startswith('00025DDE:'):
            parts = line.split(':')[1].strip().split()[:16]
            return [int(x, 16) for x in parts]
    return None

h = Hatari(game_dir='games/in_progress/player-manager/originals/PLAYERME',
           snapshot='games/in_progress/player-manager/work/newgame_0.sav',
           machine='ste', memsize_kb=1024,
           extra=['--fast-forward', 'true'])
try:
    v_init = h.vbl()
    print(f'init vbl={v_init}', flush=True)
    h.debug('b pc = $10cc0 :trace :once')
    h.debug('b pc = $10d42 :trace :once')
    h.debug('b pc = $108ae :trace :once')
    h.click()
    t0 = time.time()
    hit_done = False
    hit_edit = False
    v_start = None
    v_done = None
    v_edit = None
    saved_late = False
    while time.time() - t0 < 120:
        time.sleep(2.0)
        log = h._logtext()
        if v_start is None and '1. CPU breakpoint condition(s) matched' in log:
            # Find VBL or just record
            v_start = h.vbl()
            print(f'  [hit 10cc0] wall={time.time()-t0:.1f}s', flush=True)
        if not hit_done and '2. CPU breakpoint condition(s) matched' in log:
            hit_done = True
            v_done = h.vbl()
            print(f'  [hit 10d42] wall={time.time()-t0:.1f}s vbl={v_done}', flush=True)
        if not hit_edit and '3. CPU breakpoint condition(s) matched' in log:
            hit_edit = True
            v_edit = h.vbl()
            print(f'  [hit 108ae] wall={time.time()-t0:.1f}s vbl={v_edit}', flush=True)
            break
        counts = read_counts(h)
        v = h.vbl()
        if counts:
            # Check how many buckets are at/above quota
            quotas = [23,76,73,51, 21,65,67,47, 24,78,66,54, 24,73,65,54]
            done_n = sum(1 for c, q in zip(counts, quotas) if c >= q)
            full_n = sum(1 for c, q in zip(counts, quotas) if c >= q + 15)
            tot_c = sum(counts)
            print(f't={time.time()-t0:5.1f}s vbl={v:6d} ({(v-v_init)/50.0:6.1f}s ST) tot={tot_c:4d} done={done_n:2d}/16 full={full_n:2d}/16 counts={counts}', flush=True)
            if done_n >= 12 and not saved_late:
                h.savemem('games/in_progress/player-manager/work/setup_late.sav')
                saved_late = True
    h.shot('games/in_progress/player-manager/work/after_setup.png')
    # Also parse exact VBLs from Hatari breakpoint lines if present
    print('=== Matching breakpoint log lines ===')
    for line in h._logtext().splitlines():
        if 'matched' in line or 'pc = $10' in line:
            print(' ', line)
finally:
    h.close()
