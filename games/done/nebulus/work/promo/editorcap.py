#!/usr/bin/env python3
"""Editor footage of a nightmare level, recorded as one Hatari AVI: the level opened with Edit from the Levels list, a cursor sweep over the map, the Colours
list scrolled (the whole editor takes each look live), then Playtest with the scripted run of lvltest.py, until the frog dies.

    python3 editorcap.py LEVEL_INDEX "LOOP:BYTE,..." [OUTDIR]

The game folder is the shipped v1.2 HD release (dist/Nebulus_hd_v1.2.zip) with the nightmare.ovl as NEBLEVEL.OVL.  Menu steps use the editor's own menu table in RAM
(work/editor/ulib_ui.py); the playtest inputs are IKBD bytes poked at loop-top polls (loop index counted from arming), as in lvltest.py.  Host-timed parts (menu keys)
are logged to <OUTDIR>/editor/<name>.json as seconds from the start of the recording (x50 = AVI frame).
"""
import json, shutil, subprocess, sys, time, zipfile
from pathlib import Path
BENCH = Path(__file__).resolve().parents[5]
NEB = BENCH / 'games/done/nebulus'
sys.path.insert(0, str(NEB / 'work/editor'))
from ulib_ui import *      # noqa: E402,F401  (Nebulus, menu, pick, open_manager, wait_running, W, L, grab ...)

OUT = Path('/home/ryan/Videos/AtariST/Nebulus-promos/release')
LOOP_TOP = 0x3dcf4
AVI_ARGS = ['--avi-vcodec', 'png', '--avi-fps', '50', '--statusbar', 'false', '--borders', 'false', '--crop', 'true', '--zoom', '1']


def game_dir(ovl):
    d = Path('/tmp/promo/edgame')
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    with zipfile.ZipFile(NEB / 'dist/Nebulus_hd_v1.2.zip') as z:
        for n in z.namelist():
            base = n.split('/')[-1]
            if base and base not in ('Nebulus_campaign_disk.st', 'PATCHES.TXT'):
                (d / base).write_bytes(z.read(n))
    (d / 'NEBLEVEL.OVL').write_bytes(Path(ovl).read_bytes())
    return d


def hold(h, key, secs):
    h._xdo('keydown', '--window', h.win, key); time.sleep(secs); h._xdo('keyup', '--window', h.win, key)


def main():
    idx = int(sys.argv[1])
    inputs = {}
    for x in (sys.argv[2].split(',') if len(sys.argv) > 2 and sys.argv[2] else []):
        a, b = x.split(':'); inputs[int(a)] = int(b, 0)
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else OUT
    name = ['squeeze', 'escalator', 'nomansland'][idx]
    (out / 'editor').mkdir(parents=True, exist_ok=True)
    avi = out / 'editor' / f'{name}.avi'
    if avi.exists():
        avi.unlink()
    gd = game_dir(out / 'nightmare/nightmare.ovl')
    wd = Path('/tmp/promo/edcap') / name
    for f in list(wd.glob('*.cmd')):
        f.unlink()
    wd.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            h = Nebulus(workdir=str(wd / 'run'), game=gd, extra=['--avi-file', str(avi)] + AVI_ARGS)
            break
        except RuntimeError:
            if attempt == 3:
                raise
            time.sleep(2)
    ev = {}
    t0 = None

    def mark(n):
        ev[n] = round(time.time() - t0, 2)
        print(f'{ev[n]:6.2f}s {n}', flush=True)
    try:
        assert h.boot_to_title(timeout=150)
        time.sleep(3)
        assert open_manager(h)
        pick(h, 'Levels >', 1.0)
        pick(h, idx, 1.0)
        h.cmd('hatari-shortcut recanim'); t0 = time.time(); time.sleep(1.0)       # AVI starts on the Levels > level menu
        mark('record_start')
        pick(h, 'Edit', 2.5); mark('editor_open')
        time.sleep(2.0); mark('map_hold_end')
        hold(h, 'Right', 1.6); time.sleep(0.6); hold(h, 'Left', 1.6); time.sleep(0.6); mark('sweep_end')
        hold(h, 'Up', 1.2); time.sleep(0.5); hold(h, 'Down', 1.2); time.sleep(0.8); mark('vsweep_end')
        h.key('Control_R', hold=0.35); time.sleep(1.2); mark('menu_open')
        pick(h, 'Level >', 1.0)
        pick(h, 'Colours >', 1.2); mark('colours_open')
        for k in range(6):                                                         # live preview: the editor takes each tower's look in turn
            h.key('Up', hold=0.2); time.sleep(0.55)
        mark('colours_end')
        pick(h, '< back', 1.2)
        pick(h, '< back', 1.2)
        mark('back_to_editor')
        for i, b in inputs.items():
            (wd / f'in{i}.cmd').write_text(f'w $38498 ${b:02x}\n')
        (wd / 'end.cmd').write_text('e 1000002\n')
        last = max(inputs) + 120 if inputs else 150
        # armed BEFORE Playtest: the first loop top with the frog at the level start (x=4, y=8) runs start.cmd, which arms the scripted inputs counted from that loop
        start = ['e 1000003'] + [f'b pc = ${LOOP_TOP:x} :{i} :once :trace :file {wd}/in{i}.cmd' for i in inputs]
        start.append(f'b pc = ${LOOP_TOP:x} :{last} :once :trace :file {wd}/end.cmd')
        (wd / 'start.cmd').write_text('\n'.join(start) + '\n')
        h.debug('b all', 0.3)
        h.cmd(f'hatari-debug b pc = ${LOOP_TOP:x} && ($33a16).w = 4 && ($33a18).w = 8 && ($33938).w = 1 && ($33a20).w = 0 :once :trace :file {wd}/start.cmd'); time.sleep(0.3)
        pick(h, 'Playtest', 3.0); mark('playtest_press')
        t1 = time.time()
        while time.time() - t1 < 60 and '#1000003' not in h._logtext():
            time.sleep(0.3)
        mark('playtest_running')
        t1 = time.time()
        while time.time() - t1 < 60 and '#1000002' not in h._logtext():
            time.sleep(0.4)
        mark('playtest_end')
        time.sleep(1.0)
        h.cmd('hatari-shortcut recanim'); time.sleep(1.5)
    finally:
        h.close()
    (out / 'editor' / f'{name}.json').write_text(json.dumps(ev))


if __name__ == '__main__':
    main()
