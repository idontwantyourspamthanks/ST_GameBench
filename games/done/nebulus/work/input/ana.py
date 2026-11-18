import json, sys, statistics
def T(e, fpc): return e['vbl']*fpc + e['fc']
def pres(t, fpc): return (t//fpc + 1)*fpc      # base regs latch at HBL 310 (video.c Video_RestartVideoCounter) -> shown from next frame start

def analyze_run(run, scen, fpc):
    ev = [e for e in run if e['n'] != 'M']
    # fire key-make (Ctrl scancode $1d) and joystick fire packet; direction packet
    def stores(pred): return [e for e in ev if e['n']=='STORE' and pred(e['d0'])]
    flips = [e for e in ev if e['n']=='FLIP']
    polls = [e for e in ev if e['n']=='POLL']
    out = {}
    if scen == 'jump':
        fire = [e for e in stores(lambda d: d & 0xf0 == 0x80 and d & 0x80)]   # joystick bytes with fire
        fire = [e for e in fire if T(e,fpc) > 0]
        # first fire packet after the Right-only packets: the first byte with bit7 set and (d&0x70)==0
        f0 = next((e for e in stores(lambda d: d & 0xf0 == 0x80)), None)
        j = next((e for e in ev if e['n'] in ('JUMP','JUMPB')), None)
        if not (f0 and j): return None
        # ctrl make
        k0 = next((e for e in stores(lambda d: d == 0x1d)), None)
        i_j = ev.index(j)
        poll = [e for e in ev[:i_j] if e['n']=='POLL'][-1]
        pre = [e for e in flips if T(e,fpc) < T(poll,fpc)][-1]['st']
        after = [e for e in flips if T(e,fpc) > T(poll,fpc)]
        f_state = next((e for e in after if e['st']['state']==1), None)
        f_move = next((e for e in after if e['st']['state']==1 and (e['st']['y']!=pre['y'] or e['st']['pose']!=pre['pose'])), None)
        out = dict(key_to_poll=(T(poll,fpc)-T(k0,fpc))/fpc if k0 else None,
                   joy_to_poll=(T(poll,fpc)-T(f0,fpc))/fpc,
                   poll_to_state=(pres(T(f_state,fpc),fpc)-T(poll,fpc))/fpc if f_state else None,
                   poll_to_move=(pres(T(f_move,fpc),fpc)-T(poll,fpc))/fpc if f_move else None,
                   key_to_move=(pres(T(f_move,fpc),fpc)-T(k0,fpc))/fpc if (f_move and k0) else None,
                   joy_to_move=(pres(T(f_move,fpc),fpc)-T(f0,fpc))/fpc if f_move else None,
                   flips_state_to_move=(flips.index(f_move)-flips.index(f_state)) if (f_state and f_move) else None)
    elif scen == 'walk':
        d0 = next((e for e in stores(lambda d: d==0x08)), None)
        k0 = next((e for e in stores(lambda d: d==0x4d)), None)
        if not d0: return None
        poll = next((e for e in polls if T(e,fpc) > T(d0,fpc)), None)
        pr = [e for e in flips if T(e,fpc) < T(poll,fpc)]
        if not pr: return None
        pre = pr[-1]['st']
        f_move = next((e for e in flips if T(e,fpc) > T(poll,fpc) and e['st']['x']!=pre['x']), None)
        out = dict(key_to_move=(pres(T(f_move,fpc),fpc)-T(k0,fpc))/fpc if (f_move and k0) else None,
                   joy_to_poll=(T(poll,fpc)-T(d0,fpc))/fpc, joy_to_move=(pres(T(f_move,fpc),fpc)-T(d0,fpc))/fpc if f_move else None,
                   poll_to_move=(pres(T(f_move,fpc),fpc)-T(poll,fpc))/fpc if f_move else None)
    else:   # stand fire
        f0 = next((e for e in stores(lambda d: d & 0xf0 == 0x80)), None)
        k0 = next((e for e in stores(lambda d: d == 0x1d)), None)
        s = next((e for e in ev if e['n']=='SHOOT'), None)
        if not (f0 and s): return None
        i_s = ev.index(s)
        poll = [e for e in ev[:i_s] if e['n']=='POLL'][-1]
        pre = [e for e in flips if T(e,fpc) < T(poll,fpc)][-1]['st']
        f_state = next((e for e in flips if T(e,fpc) > T(poll,fpc) and (e['st']['state']!=pre['state'] or e['st']['pose']!=pre['pose'])), None)
        f_shot = next((e for e in flips if T(e,fpc) > T(poll,fpc) and e['st'].get('shot',0) not in (0,)), None)
        out = dict(key_to_shot=(pres(T(f_shot,fpc),fpc)-T(k0,fpc))/fpc if (f_shot and k0) else None,
                   joy_to_shot=(pres(T(f_shot,fpc),fpc)-T(f0,fpc))/fpc if f_shot else None,
                   poll_to_shot=(pres(T(f_shot,fpc),fpc)-T(poll,fpc))/fpc if f_shot else None,
                   key_to_state=(pres(T(f_state,fpc),fpc)-T(k0,fpc))/fpc if (f_state and k0) else None,
                   joy_to_poll=(T(poll,fpc)-T(f0,fpc))/fpc, joy_to_state=(pres(T(f_state,fpc),fpc)-T(f0,fpc))/fpc if f_state else None,
                   poll_to_state=(pres(T(f_state,fpc),fpc)-T(poll,fpc))/fpc if f_state else None)
    return out

def summarize(tag, scen, fpc):
    runs = json.load(open(f'raw_{tag}.json'))
    rows = [analyze_run(r, scen, fpc) for r in runs]
    keys = [k for k in rows[0]] if rows and rows[0] else []
    print(f'== {tag} ({scen}) n={len([r for r in rows if r])}/{len(rows)}  [units: frames of {fpc} cycles = 20 ms]')
    for r in rows: print('  ', {k:(round(v,2) if isinstance(v,float) else v) for k,v in (r or {}).items()})
    for k in keys:
        v = [r[k] for r in rows if r and r.get(k) is not None]
        if v: print(f'  {k:22s} min {min(v):.2f} med {statistics.median(v):.2f} mean {statistics.mean(v):.2f} max {max(v):.2f}  (ms: {min(v)*20:.0f}/{statistics.median(v)*20:.0f}/{statistics.mean(v)*20:.0f}/{max(v)*20:.0f})')
if __name__=='__main__':
    summarize(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv)>3 else 160256)

def summarize_turn(tag, fpc=160256):
    import json
    runs = json.load(open(f'raw_{tag}.json')); rows = []
    for run in runs:
        ev = [e for e in run if e['n'] != 'M']; flips = [e for e in ev if e['n'] == 'FLIP']
        t = next((e for e in ev if e['n'] == 'TURN'), None)
        if not t: rows.append(None); continue
        poll = [e for e in ev[:ev.index(t)] if e['n'] == 'POLL'][-1]
        pre = [e for e in flips if T(e, fpc) < T(poll, fpc)][-1]['st']
        after = [e for e in flips if T(e, fpc) > T(poll, fpc)]
        fp = next((e for e in after if e['st']['pose'] != pre['pose'] or e['st']['face'] != pre['face']), None)
        fx = next((e for e in after if e['st']['x'] != pre['x']), None)
        rows.append(dict(poll_to_pose=(pres(T(fp, fpc), fpc) - T(poll, fpc)) / fpc if fp else None, poll_to_x=(pres(T(fx, fpc), fpc) - T(poll, fpc)) / fpc if fx else None))
    print(f'== {tag} (turn) n={len([r for r in rows if r])}/{len(rows)}')
    for k in ('poll_to_pose', 'poll_to_x'):
        v = [r[k] for r in rows if r and r.get(k) is not None]
        if v: print(f'  {k:14s} min {min(v):.2f} med {statistics.median(v):.2f} max {max(v):.2f} frames  (ms {min(v)*20:.0f}/{statistics.median(v)*20:.0f}/{max(v)*20:.0f})  n={len(v)}')
