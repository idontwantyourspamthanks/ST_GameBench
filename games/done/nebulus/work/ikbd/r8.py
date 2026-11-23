"""Timeline with the exact dist/run_ste.sh options (no --fast-boot, no --joy1): VBL + wall seconds at START's NEPATCH stub call (S+$34c = $1b162), the end of the stub /
128-Vsync wait = window start ($1b172, SR=$2700), game entry ($38624) and the drain point ($38486). No input. usage: r8.py BUILD"""
import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/ikbd')
from lib import *
build = sys.argv[1]
h = boot(build, f'r8-{build}', extra=['--fast-boot', 'no', '--joy1', 'none'])
try:
    ev = Path(h.R)/'ev.txt'; ev.write_text('e VBL\n')
    t0 = time.time(); seen = {}
    for name, addr in (('stub call S+$34c', 0x1b162), ('window start S+$35c', 0x1b172), ('game entry $38624', 0x38624), ('drain/SR=$2300 $38486', 0x38486)):
        h.cmd(f'hatari-debug b pc = ${addr:x} :trace :once :file {ev}')
        time.sleep(0.2)
    n0 = 0; end = time.time() + 300
    while time.time() < end and len(seen) < 4:
        txt = h._logtext()
        for m in re.finditer(r'matched 1 times\.\n\tpc = \$([0-9a-f]+)[^\n]*:file[^\n]*\n(?:[^\n]*\n){0,6}?= [^\n]*#(\d+) \(dec\)', txt):
            a = int(m.group(1), 16); seen.setdefault(a, (int(m.group(2)), round(time.time() - t0, 1)))
        time.sleep(0.3)
    for a, (v, t) in sorted(seen.items(), key=lambda kv: kv[1][0]): print(f'{build}: pc=${a:x} at VBL {v}')
    if 0x1b172 in seen and 0x38486 in seen: print(f'{build}: masked window VBL {seen[0x38486][0]-seen[0x1b172][0]} = {(seen[0x38486][0]-seen[0x1b172][0])/50:.2f} s; stub call -> window start {seen[0x1b172][0]-seen[0x1b162][0]} VBL (reads + 128 Vsync)')
finally:
    h.close()
