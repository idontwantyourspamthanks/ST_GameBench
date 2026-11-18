"""Attempts as (loop, pokes) lists shared by the Unicorn sim and real Hatari (scripted loop-top pokes, scripted2.py chain), so the two can be compared loop by loop."""
import sys, struct, json, random, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input')
from sim import *
W = '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/'
BASE = '/tmp/shot_ledge.bin'
VARIANT = {'stock': [], 'shoot': [(0x3a332, b'\x4e\x71')], 'fix': [(0x3b87a, b'\x66\x08\x48\x80')], 'shootfix': [(0x3a332, b'\x4e\x71'), (0x3b87a, b'\x66\x08\x48\x80')]}
TIMER_POKE = [(0x3ad98, struct.pack('>HHH', 0x48, 0x48, 0x48))]
SPAN = 26                      # loops per attempt
def W16(a, v): return (a, struct.pack('>H', v & 0xffff))
def B8(a, v): return (a, bytes([v & 0xff]))
def attempt_pokes(at, stack=False):
    """at: dict bx,y(optional),cnt,spd,fx,st(optional) -> list of (addr, bytes) applied at the loop top of the attempt"""
    p = []
    for r in (15, 16): p.append(B8(cell(12, r), 0x82 if stack else 0))
    for k in range(1, 4): p.append(W16(fld(k, F_ST), 0))
    for F, v in ((F_X, at['bx']), (F_Y, at.get('by', 60)), (F_FR, 0), (F_CNT, at['cnt']), (F_ST, at.get('st', 1)), (F_SPD, at['spd']), (F_TGT, 1), (F_AUX, 0)):
        p.append(W16(fld(0, F), v))
    p += [W16(fld(SHOT, F_ST), 0), W16(fld(SHOT, F_CNT), -1)]
    p += [W16(PX, at['fx']), W16(PY, at.get('fy', 60)), W16(PST, 0), W16(PSTEP, 0), W16(PDIR, at.get('dir', 0))]
    return p
def sim_chain(attempts, fixes=(), nloops_each=SPAN, stack=False, extra_pokes=()):
    """run the attempts back to back in the sim. returns (timers per loop top, per-loop log rows, attempt start loops)"""
    s = Sim(BASE); pr = Probe(s)
    for a, b in fixes: s.uc.mem_write(a, bytes(b))
    for a, b in extra_pokes: s.uc.mem_write(a, bytes(b))
    L = 0; rows = []; timers = []; starts = []
    for n, at in enumerate(attempts):
        starts.append(L)
        for a, b in attempt_pokes(at, stack): s.uc.mem_write(a, b)
        if n == 0:
            for a, b in TIMER_POKE: s.uc.mem_write(a, b)
        for i in range(nloops_each):
            timers.append((s.rw(0x3ad98), s.rw(0x3ad9a), s.rw(0x3ad9c)))
            s.wb(0x38498, 0x80 if i in (0, 1) else 0)        # fire pulse = 2 loops, like the Hatari chain
            pr.rows.clear(); pr.terr_hit = None
            loop(s, extra=True)
            b0 = slot(s, 0); sh = slot(s, SHOT)
            rows.append(dict(L=L, i=i, bx=b0['x'], by=b0['y'], bst=b0['st'], bcnt=b0['cnt'], bspd=b0['spd'], sx=sh['x'], sy=sh['y'], sst=sh['st'], scnt=sh['cnt'],
                             pst=s.rw(PST), px=s.rw(PX), ov=[(h, k) for h, k, e in pr.rows], ent=[e for h, k, e in pr.rows], terr=pr.terr_hit,
                             others=[slot(s, k)['st'] for k in (1, 2, 3)]))
            L += 1
    return timers, rows, starts
def poke_cmds(pokes):
    out = []
    for a, b in pokes:
        out.append('w $%x ' % a + ' '.join('$%02x' % x for x in b))
    return out

def hat_chain(attempts, tag, variant='stock', stack=False, snap=None, max_wait=300):
    """run the same attempts in real Hatari (restored ledge.sav) and return per-loop rows aligned by loop index.
    ev_0 fires at the first loop top after arming (not keyed on the timer: the snapshot keeps running while the harness arms) and pokes the timer words
    to a fixed triple, so every later event is keyed on the sim's timer sequence."""
    import scripted2 as S, time
    from pathlib import Path
    from nebulus import Nebulus
    base, _, pac = variant.partition('_p')
    fixes = VARIANT[base]
    live = poke_cmds(fixes) + (['w $3821c $00 $%02x' % int(pac)] if pac else [])
    timers, srows, starts = sim_chain(attempts, fixes=fixes, stack=stack)
    assert len(set(timers)) == len(timers), 'timer triples not unique'
    events = []
    for n, (at, L) in enumerate(zip(attempts, starts)):
        cmds = poke_cmds(attempt_pokes(at, stack))
        if n == 0: cmds += poke_cmds(TIMER_POKE)
        events.append((timers[L], (0x80, cmds)))
        events.append((timers[L + 2], (0x00, [])))
    S.W = Path(W + 'shotmiss'); d = S.W / 'sc' / tag
    for f in (d.glob('*') if d.exists() else []): f.unlink()
    S.write_chain(d, events, set())
    # first event: not keyed on the timer
    ev0 = (d / 'ev_0.txt').read_text()
    h = Nebulus(snapshot=snap or (W + 'shotmiss/ledge.sav'), workdir='/tmp/sr-at')
    try:
        time.sleep(1.0)
        for c in live: h.debug(c, 0.2)
        h.debug('b all', 0.2)
        h.cmd(f'hatari-debug b pc = $3868e :trace :file {d}/flip.txt'); time.sleep(0.15)
        h.cmd(f'hatari-debug b pc = $3dcf4 :once :trace :file {d}/ev_0.txt')
        t0 = time.time(); last = f'{d}/ev_{len(events)-1}.txt'
        while time.time() - t0 < max_wait and f"Reading debugger commands from '{last}'" not in h._logtext():
            time.sleep(0.5)
        time.sleep(3.0)
        txt = h._logtext(); (d / 'log.txt').write_text(txt)
    finally:
        h.close()
    return timers, S.parse_flips(txt), starts, srows
def hat_rows(timers, fl):
    """-> dict loop -> row (state after that loop, matched by timer of the NEXT loop top)"""
    idx = {t: i for i, t in enumerate(timers)}
    out = {}
    for f in fl:
        t = f['timer']
        if t in idx and idx[t] >= 1:
            L = idx[t] - 1
            b = f['blk']
            g = lambda a: int.from_bytes(b[a - 0x33900:][:2], 'big', signed=True)
            sl = lambda s, F: g(fld(s, F))
            out[L] = dict(bx=sl(0, F_X), by=sl(0, F_Y), bst=sl(0, F_ST), bcnt=sl(0, F_CNT), bspd=sl(0, F_SPD), sx=sl(SHOT, F_X), sy=sl(SHOT, F_Y), sst=sl(SHOT, F_ST), scnt=sl(SHOT, F_CNT),
                          pst=g(PST), px=g(PX), others=[sl(k, F_ST) for k in (1, 2, 3)])
    return out
KEYS = ('bx', 'by', 'bst', 'bcnt', 'bspd', 'sx', 'sy', 'sst', 'scnt', 'pst', 'px')
def compare(srows, hrows):
    nm = 0; nd = 0; first = None
    for r in srows:
        h = hrows.get(r['L'])
        if h is None: continue
        d = [k for k in KEYS if r[k] != h[k]]
        if d: nd += 1; first = first or (r['L'], d, {k: (r[k], h[k]) for k in d})
        else: nm += 1
    return nm, nd, first
