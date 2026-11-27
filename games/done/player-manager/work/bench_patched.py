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

# Cold boot patched build/game/ on 1MB 8MHz STE (TOS 1.62)
h = Hatari(game_dir='games/in_progress/player-manager/build/game',
           snapshot=None, machine='ste', memsize_kb=1024)
try:
    # Boot through intro to title screen
    for i in range(4):
        time.sleep(2.5)
        h.keypress(57)
    time.sleep(2.0)

    # Check marker at $b2ff8!
    marker = h.peekl(0xb2ff8)
    mstr = marker.to_bytes(4, 'big').decode('ascii', 'replace')
    print(f'Boot marker at $b2ff8: {marker:#010x} ({mstr!r})', flush=True)
    assert mstr == 'PMOK', f'Patch marker failed: {mstr!r}'

    # Click title -> Load Game -> Cancel -> Credits -> Main Menu -> New Game
    h.click()
    time.sleep(2.5)
    h.rel(150, 120)
    time.sleep(0.3)
    h.click()
    time.sleep(2.5)
    h.click()
    time.sleep(2.5)
    h.rel(-150, -210)
    time.sleep(0.3)
    h.savemem('games/in_progress/player-manager/work/patched_newgame_ready.sav')
    h.shot('games/in_progress/player-manager/work/patched_menu.png')

    # Arm breakpoints at $10cc0 (setup start) and $10d42 (setup end -> actually setup_bucket_tail rts!)
    # Wait: our patched setup_bucket_tail returns via rts at $b3xxx, so break on $10898 (caller right after jsr $10cc0!)
    h.debug('b pc = $10cc0 :trace :once')
    h.debug('b pc = $10898 :trace :once')
    h.debug('b pc = $108ae :trace :once')

    v_before_click = h.vbl()
    h.click()
    t0 = time.time()
    v_start = None
    v_end = None
    # Run at REAL 1x 8MHz speed (or wait until $108ae hits, polling every 2s)
    while time.time() - t0 < 180:
        time.sleep(2.0)
        log = h._logtext()
        v = h.vbl()
        if v_start is None and 'pc = $10cc0 :once :trace' in log:
            v_start = v
            print(f'  [entered setup] wall={time.time()-t0:.1f}s vbl~{v}', flush=True)
        if 'pc = $10898 :once :trace' in log:
            v_end = v
            print(f'  [exited setup $10898] wall={time.time()-t0:.1f}s vbl~{v}', flush=True)
            break
        counts = read_counts(h)
        if counts:
            quotas = [23,76,73,51, 21,65,67,47, 24,78,66,54, 24,73,65,54]
            done_n = sum(1 for c, q in zip(counts, quotas) if c >= q)
            full_n = sum(1 for c, q in zip(counts, quotas) if c >= q + 15)
            print(f'  t={time.time()-t0:5.1f}s vbl={v:6d} tot={sum(counts):4d} done={done_n:2d}/16 full={full_n:2d}/16 counts={counts}', flush=True)

    time.sleep(1.5)
    h.shot('games/in_progress/player-manager/work/patched_after_setup.png')
    # Also read exact VBLs? Actually print elapsed ST time from v_before_click to v_end
    if v_end:
        print(f'PATCHED SETUP TOTAL: ~{(v_end - v_before_click)/50.0:.1f}s ST ({v_end - v_before_click} VBLs)')
    counts = read_counts(h)
    print('Final counts:', counts, 'total:', sum(counts) if counts else None)
    # Check marker still intact!
    m2 = h.peekl(0xb2ff8).to_bytes(4, 'big').decode('ascii', 'replace')
    print('Post-setup marker:', repr(m2))
finally:
    h.close()
