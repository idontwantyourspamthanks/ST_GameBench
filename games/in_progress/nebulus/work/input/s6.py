"""K4: shot at a creature moved into range (kill); K5: stand shots around the moment the frog is hit (state 7). usage: s6.py <scenario> <tag> <live>"""
from scripted2 import *
from s5 import timeline, REF
import sys
def k4():
    p = {14: (0x00, ['w $33944 $00 $10']),            # vertical eye (slot 0) X 68 -> 16: inside the shot's reach (shot X runs 13..29)
         37: 0x80, 40: 0x00, 56: 0x80, 59: 0x00, 80: 0x80, 83: 0x00}
    return p, 110
def k5():
    p = {}
    for a in (186, 190, 194, 198, 202, 206): p[a] = 0x80; p[a + 2] = 0x00
    return p, 215
def k4b():
    # eye moved to X=16 at loop 14 and Y=10 at loop 41 so that the first shot (X 7..29, Y 8..12) crosses it; second shot later
    p = {14: (0x00, ['w $33944 $00 $10']), 37: 0x80, 40: 0x00, 41: (0x00, ['w $33950 $00 $0a']), 60: 0x80, 63: 0x00, 80: 0x80, 83: 0x00}
    return p, 110
SC = {'k4': k4, 'k5': k5, 'k4b': k4b}
if __name__ == '__main__':
    scen, tag, live = sys.argv[1], sys.argv[2], sys.argv[3]
    p, end = SC[scen]()
    spec = dict(p)
    ev = build_script(REF, spec)
    fl, txt = run(tag, ev, caps=[], live=LIVE[live], tail_s=3.0, max_wait=70)
    json.dump({'caps_loops': [], 'idx_of': {}}, open(f'sc/{tag}.meta', 'w'))
    open(f'sc/{tag}.tok', 'w').write(' '.join(tokens(txt)))
    print(tag, len(fl))
