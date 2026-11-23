"""Relaunch test (NebJunkRam): a patched run, dirty the state a real session leaves (editor opened/left, trainer flag cells, latch), then restart
WITHOUT clearing RAM (KIND warm = Hatari warm reset, memory is kept; f9 = Gamex F9 on the title: Pterm, the machine restarts and START runs again),
and report the second run.  usage: relaunch.py BUILD MACHINE KIND [SEED]"""
import sys, json, time, re, random
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/junkram')
from jr import *


def snap(h, res, tag):
    mk = rd(h, 0xb0020, 4)
    res[tag + '_marker'] = mk.decode(errors='replace') if mk else None
    res[tag + '_sites'] = rdh(h, 0xb0024, 4)
    res[tag + '_v70'] = rdh(h, 0x70, 4)
    res[tag + '_trainers'] = rdh(h, 0x76c00, 8)
    res[tag + '_latch'] = rdh(h, 0x76d00, 4)
    res[tag + '_rs'] = rdh(h, 0x77c80, 64)


def wait_title(h, ste, limit):
    tt = time.time()
    while time.time() - tt < limit:
        time.sleep(2)
        if h._marker_present():
            return True
        if (14 if ste else 20) < time.time() - tt < (24 if ste else 200):
            h.keypress(57)
    return False


def run(build, machine, kind, seed=1):
    ste = machine == 'ste'
    kw = {} if ste else dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096)
    path = Path(build)
    if not path.is_absolute():
        path = J / 'build' / build
    h = Nebulus(game=path, workdir=f'/tmp/strun-jr-{machine}', **kw)
    res = dict(build=path.name, machine=machine, kind=kind)
    t0 = time.time()
    try:
        res['title1'] = wait_title(h, ste, 100 if ste else 330)
        time.sleep(3)
        snap(h, res, 'r1')
        h.key('F10', hold=0.12); time.sleep(2.0)                 # open + leave the manager: V and RS are dirtied by real use
        res['r1_f10_open'] = rdh(h, 0x70, 4) != '000382d8'
        h.key('F10', hold=0.12); time.sleep(2.0)
        rng = random.Random(seed)
        # more leftover state: trainer flags (T and E on), latch, RS words (rsOk, rsLast, rsTosP/N/MfpP), V
        h.debug('w $76c02 $ff $ff $ff $ff', 0.3)
        h.debug('w $76d00 $00 $01 $00 $01', 0.3)
        h.debug('w $77ca8 $00 $01', 0.3)                          # rsOk = 1 (store "already validated")
        h.debug('w $77cb4 $de $ad $be $ef $00 $07 $11 $22 $33 $44', 0.3)   # rsTosP junk pointer, rsTosN, rsMfpP junk
        h.debug('w $77cc4 ' + ' '.join('$%02x' % rng.randrange(256) for _ in range(40)), 0.3)
        res['dirty_trainers'] = rdh(h, 0x76c00, 8); res['dirty_rs'] = rdh(h, 0x77c80, 64)
        h.debug('w $b0020 $58 $58 $58 $58', 0.3)                 # canary: the marker must be rewritten by the second run
        h.debug('w $3d00f $00 $00 $00 $00', 0.3)                 # title marker 'High' gone until the second run unpacked the game again
        if kind == 'warm':
            h.cmd('hatari-shortcut warmreset')
        else:
            h.key('F9', hold=0.15)
        time.sleep(4)
        res['title2'] = wait_title(h, ste, 150 if ste else 330)
        time.sleep(3)
        snap(h, res, 'r2')
        res['r2_ram_kept'] = None
        res['r2_isr_hits'] = probe(h)
        if res['r2_marker'] == 'NEPO' and res['r2_v70'] == '000382d8':
            h.key('F10', hold=0.12); time.sleep(2.0)
            res['r2_f10_open'] = rdh(h, 0x70, 4) not in (None, '000382d8')
            h.key('F10', hold=0.12); time.sleep(2.0)
        res['secs'] = round(time.time() - t0)
        h.shot(str(J / f'shots/relaunch_{path.name}_{machine}_{kind}.png'))
    except Exception as e:
        res['error'] = repr(e)
    finally:
        h.close()
    return res


if __name__ == '__main__':
    (J / 'shots').mkdir(exist_ok=True)
    if sys.argv[2] == 'megaste' and sys.argv[3] == 'warm':       # Hatari's warm reset zeroes RAM (see junkram.md): uninformative, skipped
        print(json.dumps(dict(skipped='megaste warm')), flush=True); sys.exit(0)
    print(json.dumps(run(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else 1)), flush=True)
