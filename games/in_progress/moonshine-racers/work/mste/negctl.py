"""Negative control: msrpatch with a temporary patch dir holding zz_ramtest (a `; ram:` that crosses the $E2BFF ceiling); the real patches/ is untouched.
python3 work/mste/negctl.py LO HI   (hex, e.g. e2000 e3fff)"""
import sys, re
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/tools')
import msrpatch
lo, hi = sys.argv[1], sys.argv[2]
d = Path('/tmp/mste_patches'); t = (d / 'zz_ramtest.s').read_text()
(d / 'zz_ramtest.s').write_text(re.sub(r'; ram: \S+', f'; ram: ${lo}-${hi}', t))
msrpatch.PATCHDIR = d
sys.argv = ['msrpatch.py', 'build', '--only', 'pp_bigram_cache', 'rd_geom', 'rd_draw', 'zz_ramtest', '--out', '/tmp/mste_negbuild']
sys.exit(msrpatch.main())
