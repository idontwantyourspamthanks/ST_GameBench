#!/usr/bin/env python3
"""Run lbs.s in a plain TOS desktop Hatari (STE, 1 MB, 8 MHz) and print cycles per call per case.
usage: run_lbs.py [--clock 8] [--reps 8] [--src lbs.s]"""
import argparse, os, re, struct, subprocess, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[5]
sys.path.insert(0, str(BENCH / 'tools'))
from stharness import Hatari

def assemble(src):
    out = src.with_suffix('.bin'); lst = src.with_suffix('.lst')
    r = subprocess.run(['vasmm68k_mot', '-Fbin', '-m68000', '-no-opt', '-o', str(out), '-L', str(lst), '-nosym', str(src)], capture_output=True, text=True)
    if r.returncode: sys.exit(r.stdout + r.stderr)
    syms = {}
    t = lst.read_text(); i = t.find('Symbols by name')
    for ln in t[i:].splitlines()[1:]:
        m = re.match(r'^(\S+)\s+\S*:([0-9A-Fa-f]+)\s*$', ln.strip())
        if m: syms[m.group(1)] = int(m.group(2), 16)
    return out, syms

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--clock', type=int, default=8); ap.add_argument('--reps', type=int, default=8)
    ap.add_argument('--src', default='lbs.s'); ap.add_argument('--cases', default='default')
    a = ap.parse_args()
    out, syms = assemble(HERE / a.src)
    cases = []
    if a.cases == 'default':
        for np_ in (3,):
            for cols in (1, 2, 3, 4):
                for rows in (10, 16, 30):
                    for x in (100, 103):
                        cases.append((cols, rows, x, np_))
        cases.append((2, 16, 103, 4)); cases.append((4, 30, 103, 4))
    else:
        cases = eval(a.cases)
    ctab = struct.pack('>H', len(cases) + 1)
    ctab += struct.pack('>6H', 1, 1, 100, 3, a.reps, 0)       # calibration/warm case first
    for c, r, x, n in cases: ctab += struct.pack('>6H', c, r, x, n, a.reps, 0)
    (HERE / 'cases.bin').write_bytes(ctab)
    (HERE / 'src.bin').write_bytes(os.urandom(0x8000))
    E = Hatari(game_dir=str(HERE / 'emptyhd'), autorun='', extra=[])
    (HERE / 'emptyhd').mkdir(exist_ok=True)
    try:
        time.sleep(12)
        if a.clock != 8: E.set_cpuclock(a.clock)
        marks = {syms['m_case']: 'm_case', syms['m_end']: 'm_end'}
        for pc in marks: (E.R / f'mk_{pc:x}.txt').write_text('e CycleCounter\n')
        cmds = [f"loadbin {out.resolve()} $20000", f"loadbin {(HERE/'cases.bin').resolve()} $30000", f"loadbin {(HERE/'src.bin').resolve()} $40000"]
        cmds += [f"b pc = ${pc:x} :trace :file {E.R}/mk_{pc:x}.txt" for pc in marks] + ["r pc=$20000"]
        (E.R / 'apply.txt').write_text('\n'.join(cmds) + '\n')
        E.debug('b all', 0.3)
        n0 = len(E._logtext())
        # execute the apply script through a one-shot breakpoint at the next VBL
        v = E.vbl()
        E.cmd(f"hatari-debug b VBL > {v + 2} :trace :once :file {E.R}/apply.txt")
        t0 = time.time()
        while time.time() - t0 < 300:
            time.sleep(2)
            o = E.debug('m $20ff0 4', 0.5)
            if '44 4f 4e 45' in o: break
        else:
            print('TIMEOUT'); print(E._logtext()[-1500:])
        log = E._logtext()[n0:]
    finally:
        E.close()
    (HERE / 'last_log.txt').write_text(log)
    tl = []
    parts = re.split(r"\n\t(pc = \$[0-9a-f]+) :trace :file [^\n]*\nReading debugger commands from[^\n]*\n", log)
    for i in range(1, len(parts) - 1, 2):
        pc = int(parts[i].split('$')[1], 16)
        m = re.search(r"#(\d+)(?:/-?\d+)? \(dec\)", parts[i + 1])
        if m: tl.append((marks.get(pc, hex(pc)), int(m.group(1))))
    cyc = []; mc = None
    for n, c in tl:
        if n == 'm_case': mc = c
        elif n == 'm_end' and mc is not None: cyc.append((c - mc) & 0xffffffff); mc = None
    print('cases measured', len(cyc), 'of', len(cases) + 1)
    base = cyc[0] / a.reps
    print(f'calibration case (1x1, x=100): {base:.0f} cycles/call')
    res = []
    for (c, r, x, n), cy in zip(cases, cyc[1:]):
        res.append((c, r, x & 15, n, cy / a.reps))
        print(f'cols {c} rows {r:2d} shift {x&15:2d} planes {n}: {cy / a.reps:8.0f} cycles/call')
    (HERE / f'res_{a.src}_{a.clock}.txt').write_text('\n'.join(f'{c} {r} {s} {n} {cy:.0f}' for c, r, s, n, cy in res) + '\n')
main()
