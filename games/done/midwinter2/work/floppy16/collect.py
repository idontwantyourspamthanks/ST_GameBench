"""collect.py LABEL PREFIX [PREFIX...]  -> out/RESULTS_LABEL.txt: the raw gate lines of every out/<PREFIX>*.log (GATE / SWAP / CELL / key facts)."""
import sys, re
from pathlib import Path
out = Path(__file__).resolve().parent / 'out'
label, prefixes = sys.argv[1], sys.argv[2:]
keep = re.compile(r'^(GATE|SWAP|CELL|VERDICT|first game restore|game type I commands|_nflops|insert-graphics|M/J/K|\$6220|world_rate|heading series|REACHED|soak|prompt |EXC|security-check|longest|  CUT)')
lines = []
for p in prefixes:
    for f in sorted(out.glob(f'{p}*.log')):
        if f.name.startswith('batch'):
            continue
        lines.append(f'=== {f.name}')
        lines += [l.rstrip() for l in f.read_text(errors='replace').splitlines() if keep.match(l)]
(out / f'RESULTS_{label}.txt').write_text('\n'.join(lines) + '\n')
print('\n'.join(lines))
