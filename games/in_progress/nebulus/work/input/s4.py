from scripted2 import *
import sys
txt=open('sc/s1/log.txt').read(); REF=parse_flips(txt)
def spec_j2():
    spec = {j: 0x08 for j in range(45, 60)}
    for k in range(4): spec[60+k] = 0x88          # jump at x~15 into the (poked) solid pillar: blocked-jump entry $39ffc
    for j in range(64, 80): spec[j] = 0x08
    for k in range(4): spec[80+k] = 0x88          # second blocked jump
    for j in range(84, 100): spec[j] = 0x08
    spec[100] = 0x00
    return spec
if __name__=='__main__':
    tag, live = sys.argv[1], sys.argv[2]
    spec = spec_j2(); ev = build_script(REF, spec)
    keys = sorted(spec); caps = [keys.index(j) for j in range(58, 72)]
    fl, txt = run(tag, ev, caps=caps, live=(LIVE[live] + ['w $329f2 $81 $81 $81']), tail_s=3.0, max_wait=60)
    open(f'sc/{tag}.tok','w').write(' '.join(tokens(txt)))
    print(tag, len(fl))
