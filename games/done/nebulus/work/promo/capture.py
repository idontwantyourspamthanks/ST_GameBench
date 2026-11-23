#!/usr/bin/env python3
"""Release-video capture: stock Nebulus vs v1.2, same scene, same input, recorded as Hatari AVI (PNG frames, 640x400 = 2x the ST screen).

    python3 capture.py bullet stock|v12 [OUTDIR]
    python3 capture.py lift   stock|v12 [OUTDIR]

Both variants restore the SAME stock-code snapshot (Hatari 2.6.1, STE 1 MB, TOS 1.62, 8 MHz, 50 Hz) and apply the fix LIVE in the event
file (executed at a loop-top poll, `pc=$3dcf4`, so the patch lands between two game loops): `tools/nepatch.py live --only np_shot|np_lift`,
the same bytes the shipped release writes (np_shot 4 bytes in place, np_lift 6 sites in place, no blob).  The scene and the input are a
pure function of the loop index (breakpoint hit counts, never host time), as in work/shotmiss and work/liftperf; the AVI is started with the
`recanim` shortcut just before arming (`--avirecord` on the command line makes the harness lose the Hatari window) and cut afterwards by post.py using the per-flip VBL log written here.

bullet: work/shotmiss/ledge.sav (tower 1, frog on ledge row 14).  The ball is the tower's OWN waiting ball: the spawner is re-enabled and
        its scan pointer reset to row 15, so the marker `$30` at col 9 row 15 spawns it (x=76) with the game's own sprite fields (a slot poked by
        hand showed the shot sprite).  It hops in place until the frog is within 32 units.  The frog starts at x=110 (34 away), walks left
        4 loops (x=106), and fires at loop 24 while the ball is rolling at it.  Stock (found with spawn_search.py, sim == Hatari): the shot
        misses (np_shot's missing `andi.w #$3ff`, shotmiss.md), the ball hits the frog and knocks it off the ledge; v1.2: the ball dies.
lift:   tower 6 stock snapshot (frog at the tower start), enemies ON with extra markers beside the ride path (LIFT_MARKERS), a lift in
        column 0 from row 1 to row 24, Up held for 4 loops (liftperf.md: stock 23.00 fps, 16 of 92 ride loops take 3 VBL; v1.2 25.00 fps, none).
"""
import json, re, subprocess, sys, time
from pathlib import Path

BENCH = Path(__file__).resolve().parents[5]
NEB = BENCH / 'games/done/nebulus'
sys.path.insert(0, str(BENCH / 'tools')); sys.path.insert(0, str(NEB / 'tools'))
sys.path.insert(0, str(NEB / 'work/shotmiss')); sys.path.insert(0, str(NEB / 'work/input'))
from nebulus import Nebulus, ORIGIN   # noqa: E402

OUT_DEFAULT = Path('/home/ryan/Videos/AtariST/Nebulus-promos/release')
LOOP_TOP, FLIP = 0x3dcf4, 0x3868e
MARK_EVENT, MARK_END = 1000001, 1000002
AVI_ARGS = ['--avi-vcodec', 'png', '--avi-fps', '50', '--statusbar', 'false', '--borders', 'false', '--crop', 'true', '--zoom', '1']


def live_cmds(name):
    """`w` debugger commands for one patch of tools/nepatch.py, chunked to 24 bytes, high RAM first."""
    out = []
    for c in subprocess.run([sys.executable, str(NEB / 'tools/nepatch.py'), 'live', '--only', name], capture_output=True, text=True, check=True).stdout.splitlines():
        if not c.startswith('w '):
            continue
        p = c.split(); a = int(p[1][1:], 16); bs = p[2:]
        for i in range(0, len(bs), 24):
            out.append(f'w ${a+i:x} ' + ' '.join(bs[i:i+24]))
    out.sort(key=lambda c: -int(c.split()[1][1:], 16))
    return out


def scene_bullet(variant):
    G = 0x327f0
    w = lambda a, v: f'w ${a:x} ${(v >> 8) & 255:02x} ${v & 255:02x}'
    cmds = ['w $3ad98 $00 $48 $00 $48 $00 $48', 'w $338fc $00 $00']
    if variant == 'v12':
        cmds += live_cmds('np_shot')
    cmds += ['w $3792c $30 $39',                        # spawner back on (the snapshot has `rts`)
             'w $3393c $00 $03 $27 $ff',                # scan pointer = grid (col 0, row 15) = $327ff
             f'w ${G+12*256+15:x} 0', f'w ${G+12*256+16:x} 0']             # the 2-block stack beside the frog is gone
    cmds += [w(0x33944 + 0x48 + 2 * k, 0) for k in range(4)]               # creature slots free
    cmds += [w(0x33944 + 0x48 + 8, 0), w(0x33944 + 0x3c + 8, 0xffff)]      # shot slot idle
    cmds += [w(0x33a16, 110), w(0x33a18, 60), w(0x33a20, 0), w(0x33a1e, 0), w(0x33a1c, 0)]   # frog x y state step dir (facing left)
    return dict(snap=NEB / 'work/shotmiss/ledge.sav', event=cmds, inputs={8: 0x04, 12: 0x00, 24: 0x80, 26: 0x00}, loops=110)


# extra creature markers for the lift ride: (col, row, marker value); cells must be empty in the tower-6 map (work/level/tools/nebedit.py dump)
import os
LIFT_MARKERS = [tuple(int(x, 0) for x in m.split(',')) for m in os.environ.get('MARKERS', '3,21,0x10;15,23,0x10;3,23,0x10').split(';') if m]

def scene_lift(variant, snap, markers):
    COL = 0x327f0
    END = 24
    cmds = ['w $3ad98 $00 $20 $00 $00 $00 $00', 'w $3b0aa $60', 'w $338fc $00 $00']
    if variant == 'v12':
        cmds += live_cmds('np_lift')
    cmds += [f'w ${COL+1:x} $85'] + [f'w ${COL+r:x} 0' for r in range(2, END)] + [f'w ${COL+END:x} 8']
    cmds += [f'w ${COL+c*256+r:x} ${m:02x}' for c, r, m in markers]
    cmds.append('w $3792c $30 $39')        # undo the snapshot's `rts` on the enemy spawner (stock bytes): enemies ON
    return dict(snap=snap, event=cmds, inputs={3: 0x01, 7: 0x00}, loops=110)



def main():
    scenario, variant = sys.argv[1], sys.argv[2]
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else OUT_DEFAULT
    raw = out / 'raw'; raw.mkdir(parents=True, exist_ok=True)
    tag = f'{scenario}_{variant}'
    if scenario == 'bullet':
        sc = scene_bullet(variant)
    else:
        snap = out / 'snap/ste_stock_t6.sav'
        sc = scene_lift(variant, snap, [] if scenario == 'liftbare' else LIFT_MARKERS)
    wd = Path('/tmp/promo') / tag
    wd.mkdir(parents=True, exist_ok=True)
    for f in wd.glob('*.cmd'):
        f.unlink()
    avi = raw / f'{tag}.avi'
    if avi.exists():
        avi.unlink()
    # event file: runs at the first loop-top after arming = loop index 0 of the clip
    ev = [f'e {MARK_EVENT}', 'e VBL'] + sc['event']
    ev.append(f'b pc = ${FLIP:x} :trace :file {wd}/flip.cmd')
    for i, byte in sc['inputs'].items():
        (wd / f'in{i}.cmd').write_text(f'w $38498 ${byte:02x}\n')
        ev.append(f'b pc = ${LOOP_TOP:x} :{i} :once :trace :file {wd}/in{i}.cmd')
    (wd / 'end.cmd').write_text(f'e {MARK_END}\ne VBL\nb all\n')
    ev.append(f'b pc = ${LOOP_TOP:x} :{sc["loops"]} :once :trace :file {wd}/end.cmd')
    (wd / 'event.cmd').write_text('\n'.join(ev) + '\n')
    (wd / 'flip.cmd').write_text('e VBL\n')
    for attempt in range(4):         # Hatari intermittently misses the 10 s window wait of the harness on a loaded host: start again
        try:
            h = Nebulus(snapshot=str(sc['snap']), workdir=str(wd / 'run'), game=ORIGIN,
                        extra=['--avi-file', str(avi)] + AVI_ARGS)
            break
        except RuntimeError:
            if attempt == 3:
                raise
            time.sleep(2.0)
    try:
        time.sleep(1.0)
        h.cmd('hatari-shortcut recanim')           # starts the AVI
        time.sleep(1.0)
        h.debug('b all', 0.3)
        site = h.debug('m $37d5a 16', 0.5)         # stock np_lift site bytes (4240102310350000b03c002864000022) prove the snapshot code is unpatched
        h.cmd(f'hatari-debug b pc = ${LOOP_TOP:x} :once :trace :file {wd}/event.cmd')
        t0 = time.time()
        while time.time() - t0 < 180 and f'#{MARK_END}' not in h._logtext():
            time.sleep(0.5)
        time.sleep(1.0)
        h.cmd('hatari-shortcut recanim')           # stops the AVI
        time.sleep(1.5)
        log = h._logtext()
    finally:
        h.close()
    (raw / f'{tag}.log').write_text(log)
    nums = [int(x) for x in re.findall(r'#(\d+) \(dec\)', log)]
    i0 = nums.index(MARK_EVENT)
    event_vbl = nums[i0 + 1]
    j = nums.index(MARK_END)
    flips = nums[i0 + 2:j]
    end_vbl = nums[j + 1]
    meta = dict(scenario=scenario, variant=variant, event_vbl=event_vbl, end_vbl=end_vbl, flips=flips, loops=sc['loops'],
                inputs={str(k): v for k, v in sc['inputs'].items()}, site_37d5a=re.findall(r'00037D5A:\s+((?:[0-9a-f]{2} ?)+)', site, re.I))
    (raw / f'{tag}.json').write_text(json.dumps(meta))
    gaps = [b - a for a, b in zip(flips, flips[1:])]
    print(tag, 'event VBL', event_vbl, 'end', end_vbl, 'flips', len(flips), 'VBL/flip mean %.3f' % (sum(gaps) / max(len(gaps), 1)), 'gaps>2', sum(1 for g in gaps if g > 2), 'site', meta['site_37d5a'])


if __name__ == '__main__':
    main()
