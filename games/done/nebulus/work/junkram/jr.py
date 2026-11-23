"""Junk-RAM cold-boot matrix (NebJunkRam).  The MiSTer does not clear RAM between runs, Hatari does: this fills RAM with a seeded random pattern at START's
stub call (S+$34c, BEFORE the loader stub reads NEPATCH.BIN / NEBLEVEL.OVL), then lets the boot run and reports one JSON line per boot.
usage: jr.py BUILD MACHINE(ste|megaste) MODE SEED [SEED...]     (BUILD = dir under work/junkram/build or any path)
MODE: all  = junk over the dead zone $75728..$77ec0 (gap, blobs, RS, V) + non-game $AA000..$C0000 (editor scratch, payload area, store, TREC)
      rs   = junk only over RS+V ($77c80..$77dc0)
      zone = junk only over the dead zone $75728..$77ec0
      none = no junk (control)
      zero = (relaunch control) nothing
Reported per boot: marker (NEPO/NEPF), site count $b0024, reused count $b0026 (sites found already in their NEW state), $70 (editor VBL = self-opened editor),
RS+V, trainer cells $76c00.., latch $76d00.., ISR hits for a key tap (2 = input alive), VBL advancing, F10 opens/closes the manager, exception lines in the log."""
import sys, random, json, time, re
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *

J = G / 'work/junkram'


def rdh(h, a, n):
    out = h.debug(f'm ${a:x} {n}', 0.6)
    rows = re.findall(r'^([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?)+)', out, re.I | re.M)
    d = b''.join(bytes.fromhex(''.join(r[1].split())) for r in rows if a <= int(r[0], 16) < a + n)
    return d.hex()[:2 * n] if d else None


def ranges(mode, machine):
    if mode.startswith('leftover'):
        return [(0x75728, 0x77ec0), (0xAA000, 0xC0000)]
    if mode == 'all':
        return [(0x75728, 0x77ec0), (0xAA000, 0xC0000)]
    if mode == 'rs':
        return [(0x77c80, 0x77dc0)]
    if mode == 'zone':
        return [(0x75728, 0x77ec0)]
    return []


def one(build, machine, mode, seed, f10=True):
    t0 = time.time()
    ste = machine == 'ste'
    kw = {} if ste else dict(machine='megaste', tos=TOS['2.06'], memsize_kb=4096)
    bp = 0x1b162 if ste else 0x213de               # S+$34c (START text base: STE $1AE16, Mega STE $21092 [obs: `jmp $33b00` at $21444 = S+$3b2]): the `bsr stub` that replaced `move.w #$7f,d7`
    rng = random.Random(seed)
    path = Path(build)
    if not path.is_absolute():
        path = J / 'build' / build
    h = Nebulus(game=path, workdir=f'/tmp/strun-jr-{machine}', **kw)
    res = dict(build=path.name, machine=machine, mode=mode, seed=seed)
    try:
        rg = ranges(mode, machine)
        if rg:
            ev = Path(h.R) / 'ev.txt'; lines = []
            for i, (lo, hi) in enumerate(rg):
                jf = Path(h.R) / f'junk{i}.bin'
                if mode.startswith('leftover'):               # leftover:<tag> = RAM of an earlier patched run (capture.py), not random bytes
                    jf = J / f'leftover_{mode.split(":", 1)[1]}_{i}.bin'
                    assert jf.stat().st_size == hi - lo, jf
                else:
                    jf.write_bytes(bytes(rng.randrange(256) for _ in range(hi - lo)))
                lines.append(f'loadbin {jf} ${lo:x}')
            ev.write_text('\n'.join(lines) + '\ne VBL\n')
            h.cmd(f'hatari-debug b pc = ${bp:x} :trace :once :file {ev}')
            m, n = wait_log(h, r'#(\d+) \(dec\)', 0, timeout=240, step=0.005)
            res['junked'] = bool(m)
        got = False
        tt = time.time()
        while time.time() - tt < (100 if ste else 330):
            time.sleep(2)
            if h._marker_present():
                got = True; break
            if time.time() - tt > (14 if ste else 20) and time.time() - tt < (24 if ste else 200):
                h.keypress(57)
        res['title'] = got
        n_title = len(h._logtext())            # exceptions are counted from the title on (TOS/START probe bus errors during the boot are normal)
        time.sleep(3)
        mk = rd(h, 0xb0020, 4)
        res['marker'] = mk.decode(errors='replace') if mk else None
        res['sites'] = rdh(h, 0xb0024, 4)           # site count word + reused word
        res['v70'] = rdh(h, 0x70, 4)
        res['rs'] = rdh(h, 0x77c80, 64)
        res['v'] = rdh(h, 0x77cc0, 32)
        res['trainers'] = rdh(h, 0x76c00, 8)
        res['latch'] = rdh(h, 0x76d00, 4)
        res['store'] = rdh(h, 0xbc000, 16)
        v70 = res['v70']
        res['self_open'] = bool(v70) and v70 != '000382d8' and res['marker'] == 'NEPO'
        res['trainers_active'] = bool(res['trainers']) and res['trainers'][4:12] != '00000000'
        v1 = h.vbl(); time.sleep(0.6); v2 = h.vbl()
        res['vbl_runs'] = v2 > v1
        res['isr_hits'] = probe(h)
        res['input_ok'] = res['isr_hits'] == 2
        if f10 and not res['self_open'] and res['marker'] == 'NEPO':
            h.key('F10', hold=0.12); time.sleep(2.0)
            o = rdh(h, 0x70, 4); res['f10_open'] = o not in (None, '000382d8')
            h.key('F10', hold=0.12); time.sleep(2.0)
            c = rdh(h, 0x70, 4); res['f10_close'] = c == '000382d8'
            res['v70_after'] = c
        txt = h._logtext()[n_title:]
        res['exc'] = sorted(set(re.findall(r'(?i)(bus error|address error|illegal instruction|double bus|cpu halted|privilege violation)', txt)))
        h.shot(str(J / f'shots/{path.name}_{machine}_{mode}_{seed}.png'))
    except Exception as e:
        res['error'] = repr(e)
    finally:
        h.close()
    res['secs'] = round(time.time() - t0)
    return res


if __name__ == '__main__':
    (J / 'shots').mkdir(exist_ok=True)
    build, machine, mode = sys.argv[1:4]
    for s in sys.argv[4:]:
        r = one(build, machine, mode, int(s))
        print(json.dumps(r), flush=True)
