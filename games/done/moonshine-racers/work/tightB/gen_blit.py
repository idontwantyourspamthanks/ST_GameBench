#!/usr/bin/env python3
"""Generates patches/tb_blit.s (or an experiment variant) from one template.
   python3 gen_blit.py OUT.s [BUDGET=1800] [GUARD=0] [GTH=2] [MINR=10,6,12] [NAME=tb_blit] [DEFAULT=no]"""
import sys
args = dict(a.split('=') for a in sys.argv[2:])
BUDGET = int(args.get('BUDGET', 1800)); GUARD = int(args.get('GUARD', 0)); GTH = int(args.get('GTH', 2))
MINR = [int(x) for x in args.get('MINR', '10,6,12').split(',')]; NAME = args.get('NAME', 'tb_blit'); DEFAULT = args.get('DEFAULT', 'no')
T = open(__file__.replace('gen_blit.py', 'blit_template.s')).read()
T = T.replace('@NAME@', NAME).replace('@DEFAULT@', DEFAULT).replace('@BUDGET@', str(BUDGET)).replace('@GUARD@', str(GUARD)).replace('@GTH@', str(GTH))
VAR = args.get('VARIANTS', '').split(',') if args.get('VARIANTS') else []
FINAL = args.get('FINAL', '0') == '1'
def conf_for(nm):
    if FINAL: return ''
    others = [x + sfx for x in VAR + ['tb_blit'] if x != NAME for sfx in ('', '11', '13', '15')]
    return ' '.join(others)
T = T.replace('@CONF@', conf_for(NAME))
if not conf_for(NAME): T = T.replace('; conflicts: \n', '')
T = T.replace('@REQ@', ' '.join(NAME + s for s in ('11', '13', '15')))
T = T.replace('@MIN1@', str(MINR[0])).replace('@MIN2@', str(MINR[1])).replace('@MIN3@', str(MINR[2]))
out = sys.argv[1]
open(out, 'w').write(T)
S = open(__file__.replace('gen_blit.py', 'blit_site.s')).read()
base = out[:-2] if out.endswith('.s') else out
for sfx, site, ptrs in (('11', 0x39b4, '$B4540,$B4550,$B4560'), ('13', 0x39c8, '$B4570,$B4580,$B4590'), ('15', 0x3a18, '$B45A0,$B45B0,$B45C0')):
    t = S.replace('@NAME@', NAME + sfx).replace('@DEFAULT@', DEFAULT).replace('@SITE@', '$%x' % site).replace('@MAIN@', NAME).replace('@PTRS@', ptrs).replace('@WHAT@', 'nibble ' + sfx)
    c = conf_for(NAME)
    t = t.replace('@CONFL@', ('; conflicts: ' + c + '\n') if c else '')
    open(base + sfx + '.s', 'w').write(t)
