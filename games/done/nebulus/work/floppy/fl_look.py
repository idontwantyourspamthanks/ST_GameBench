"""Floppy build look gate (NebLooksBuild): boot the floppy build (STE TOS 1.62 1 MB), load the 15-cell look file over the store ($BC000, as e180: loadbin + rsOk=0),
play looks cells from the level list, and compare the level-start RAM with the HD run of the same cells.  The floppy game is at PP's addresses -8 after the text:
palette $351ac and the buffers below $33b1c are identical, the raster colours are at $40390.
usage: fl_look.py DISK.st OUTDIR LOOKS.ovl REFDIR(run_look dump dir of the HD base8) [cells e.g. 0,4,9]"""
import sys, time, re, struct, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nebfloppy import NebFloppy
disk, out, ovlf, REFDIR = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4]
CELLS = [int(x) for x in (sys.argv[5] if len(sys.argv) > 5 else '0,4,9').split(',')]
SPEC = [(2, c, 2) for c in range(1, 9)] + [(0, 3, e) for e in range(1, 5)] + [(5, 0, 0), (1, 0, 3), (6, 4, 0)]
out.mkdir(parents=True, exist_ok=True)
h = NebFloppy(disk, machine='ste', mem=1024, workdir=str(out / 'wd'), trace='fdc')
def words(a, n):
    o = h.debug(f"m ${a:x} {n}", 0.6)
    b = bytes(int(x, 16) for l in o.splitlines() if re.match(r'^[0-9a-f]{8}:', l, re.I) for x in re.findall(r'(?<=\s)[0-9a-f]{2}(?=\s)', l.split(':', 1)[1][:48]))
    return b[:n]
def W(a): return int.from_bytes(words(a, 2), 'big')
def grab(a, n):
    p = f'/tmp/fl_{os.getpid()}.bin'
    for _ in range(5):
        if os.path.exists(p): os.remove(p)
        h.debug(f"savebin {p} ${a:x} ${n:x}", 0.4)
        for _ in range(30):
            if os.path.exists(p) and os.path.getsize(p) == n: time.sleep(0.05); d = open(p, 'rb').read(); os.remove(p); return d
            time.sleep(0.1)
    raise RuntimeError('grab')
def K(k, hold=0.2, gap=0.5): h.key(k, hold=hold); time.sleep(gap)
V = 0x77cc0; RS = 0x77c80
def menu():
    p = int.from_bytes(grab(V + 4, 4), 'big'); d = grab(p, 700); n = d[0]; items = []; i = 1
    for _ in range(n):
        j = i + 2
        while d[j]: j += 1
        items.append(d[i + 2:j].decode('latin1')); i = j + 1
    return items, W(V + 8)
def pick(what, gap=1.3):
    items, sel = menu(); idx = what if isinstance(what, int) else [i for i, t in enumerate(items) if t.startswith(what)][0]
    for _ in range(40):
        items, sel = menu()
        if sel == idx: break
        K('Down' if idx > sel else 'Up', 0.2, 0.5)
    K('Control_R', 0.35, gap)
fails = 0
def chk(n, g, e=True):
    global fails
    ok = g == e; print(('PASS ' if ok else 'FAIL ') + n + ': ' + repr(g) + ('' if ok else ' expected ' + repr(e)), flush=True); fails += not ok
try:
    t = h.boot_to_title(timeout=400, space_at=20); print('floppy title', bool(t), flush=True)
    time.sleep(2)
    print('hook bytes: $3dbf0 floppy site', hex(W(0x3dbf0)), flush=True)
    h.debug(f'loadbin {ovlf} $bc000', 0.8); h.debug(f'w ${RS + 40:x} $00 $00', 0.3)
    K('F10', 0.6, 2.5)
    print('manager open (VBL vec != game):', hex(int.from_bytes(grab(0x70, 4), 'big')), flush=True)
    for cell in CELLS:
        b, c, e = SPEC[cell]
        pick('Levels', 1.3); pick(cell, 1.0); pick('Play', 1.5)
        for _ in range(120):
            time.sleep(1.0)
            if W(0x33a20) == 0 and W(0x33938) == 1: break
        time.sleep(2.5)
        ct = c - 1 if c else b; et = e - 1 if e else b
        ref = open(f'{REFDIR}/lvl{ct}.bin', 'rb').read(); refe = open(f'{REFDIR}/lvl{et}.bin', 'rb').read()
        pal = grab(0x351ac, 32); ras = grab(0x40390, 8); sky = grab(0x100e0, 4096); eye = grab(0x24be0, 0xaf00)
        chk(f'floppy cell {cell} (b=T{b+1} c={c} e={e}): palette == stock tower {ct+1}', pal, ref[0x351ac:0x351ac + 32])
        chk(f'floppy cell {cell}: raster colours == stock tower {ct+1}', ras, ref[0x40398:0x40398 + 8])
        chk(f'floppy cell {cell}: skyline buffer == stock tower {ct+1}', sky, ref[0x100e0:0x100e0 + 4096])
        chk(f'floppy cell {cell}: eye frames == stock tower {et+1} design', eye, refe[0x24be0:0x24be0 + 0xaf00])
        chk(f'floppy cell {cell}: caches rsCol/rsEye, tower word = base', (W(RS + 62), W(RS + 50) & 3, W(0x3390c)), (ct, et & 3, b))
        h.shot(str(out / f'floppy_cell{cell}.png'))
        K('q', 0.3, 2.0)
        for _ in range(40):
            time.sleep(1.0)
            if W(0x33938) == 9: break
        time.sleep(1.5); K('F10', 0.6, 2.5)
finally:
    h.close()
log = (out / 'wd' / 'log.txt').read_text(errors='replace')
print('crash lines in Hatari log:', len(re.findall(r'Address error|Illegal|double bus|CPU halted|bus error', log, re.I)))
print('FAILS', fails)
