"""Snapshot-based trials (START ~VBL 2500, before the SR=$2700 depack/hand-over window).
usage: r2.py VARIANT OUT.jsonl SPEC...   SPEC = dt[:key[:hold]][,dt2[:key[:hold]]...] relative to the pc=$1b172 hit (window start), seconds.
'none' = no input. Prints one line per trial and appends JSON to OUT. Each trial = restore snapshot, inject taps, wait for title, probe."""
import sys, json
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *

def trial(variant, spec, extra=None, post_wait=4.0, snap=None):
    taps = []
    if spec != 'none':
        for part in spec.split(','):
            f = part.split(':'); taps.append((float(f[0]), f[1] if len(f) > 1 else 'space', float(f[2]) if len(f) > 2 else 0.08))
    h = boot(variant, '', snapshot=str(snap or G/f'work/ikbd/snap_{variant}.sav'), extra=extra)
    res = {'variant': variant, 'spec': spec}
    try:
        ev = Path(h.R)/'ev.txt'; ev.write_text('e VBL\n')
        h.cmd(f'hatari-debug b pc = $1b172 :trace :once :file {ev}')
        m, n = wait_log(h, r'#(\d+) \(dec\)', 0, timeout=60, step=0.005)
        t0 = time.time()
        res['win_vbl'] = int(m.group(1)) if m else None
        for dt, key, hold in sorted(taps):
            while time.time() - t0 < dt: time.sleep(0.002)
            tap(h, key, hold)
        # wait for title/game up: 'High' marker, then settle
        time.sleep(max(0.0, 2.6 + post_wait - (time.time() - t0)))
        res['marker'] = h._marker_present()
        res['isr_hits'] = probe(h)
        res['alive'] = res['isr_hits'] >= 2
    finally:
        h.close()
    return res

if __name__ == '__main__':
    variant, out = sys.argv[1], sys.argv[2]
    for spec in sys.argv[3:]:
        r = trial(variant, spec)
        print(json.dumps(r), flush=True)
        with open(out, 'a') as f: f.write(json.dumps(r) + '\n')
