"""Which RUNME paths run on a cold boot to the M/J/K screen?  Counts hits of breakpoints in RUNME's TPA text.

    python3 work/payload32k/bp_runme.py NAME MACHINE TOS MEM_KB GAME_DIR

RUNME's text base in the TPA is $149F2 on every cell seen so far (A0 at the boot-stub breakpoint = text base +
$4536 + 34 + $8000 = $20F4A, work/payload32k/h1*.out), so text offset X is RAM $149F2+X.
Breakpoints: $22A (`jsr $43d2.l`, d2 == 4 path), $232 (`jsr $abe.l`, other path), $230 (the `bra.b $238` whose word
the old build corrupted), $4476 (`move.w #$ef,d3`: entry of the intro-picture plane loop), $4514 (`lea $40(a2),a2`, the
instruction whose displacement the old build corrupted), $4518 (the loop's `dbra d3`).
"""
import sys, time, re, json
from pathlib import Path
sys.path.insert(0, 'tools')
from mw2harness import Hatari

name, machine, tos, mem, game = sys.argv[1:6]
TOS = {'206': Path('tos/TOS_2_06.img').resolve(), '104': Path('tos/TOS_1_04.img').resolve(),
       '162': Path.home() / 'Emulators/BIOS/AtariST/TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img'}
BASE = 0x149F2
POINTS = {0x22A: 'jsr $43d2 (d2==4)', 0x232: 'jsr $abe (else)', 0x230: 'bra.b $238 after jsr $43d2', 0x4476: 'plane loop entry',
          0x4514: 'lea $40(a2),a2', 0x4518: 'plane loop dbra d3'}
h = Hatari(snapshot=None, memsize_kb=int(mem), game_dir=Path(game), machine=machine, tos=TOS[tos])
try:
    h.cmd('hatari-debug b all'); time.sleep(0.3)
    for off in POINTS:
        h.cmd(f'hatari-debug b pc = ${BASE + off:x} :trace'); time.sleep(0.3)
    time.sleep(25)
    ref = Path('work/ref/mode_select.png')
    for _ in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)):
            break
    else:
        raise RuntimeError('never reached the M/J/K screen')
    log = h._logtext()
    print('M/J/K screen reached; $3bb (text, byte) =', h.debug(f'm ${BASE + 0x3bb:x} 1').strip().splitlines()[-1])
    for i, (off, what) in enumerate(POINTS.items(), 1):
        n = re.findall(rf'^{i}\. CPU breakpoint condition\(s\) matched (\d+) times', log, re.M)
        print(f'bp {i}: text ${off:x} (RAM ${BASE + off:x}) {what}: hits {n[-1] if n else 0}')
    (Path('work/payload32k') / f'{name}.hlog').write_text(log)
finally:
    h.close()
