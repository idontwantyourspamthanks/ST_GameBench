from scripted2 import *
import sys, json
txt=open('sc/s1/log.txt').read(); REF=parse_flips(txt)
def spec_j1(extra=None):
    spec = {j: 0x08 for j in range(45, 50)}
    for k in range(4): spec[50+k] = 0x88          # jump while walking right from x~8 (lands on ground col 2)
    spec[54] = 0x08; spec[55] = 0x08
    for j in range(56, 62): spec[j] = 0x00        # stop
    for k in range(3): spec[90+k] = 0x80          # fire standing = shoot
    spec[93] = 0x00
    spec[105] = 0x08                               # walk right again ...
    for k in range(4): spec[108+k] = 0x88          # ... jump at x~24: lands on the crumble tiles -> death sequence
    spec[112] = 0x08
    for k in range(113, 120): spec[k] = 0x08
    for k in range(120, 128): spec[k] = 0x88      # fire held through the landing on the crumble tile (state 2 -> 8 death)
    if extra: spec.update(extra)
    return spec
if __name__=='__main__':
    tag, live = sys.argv[1], sys.argv[2]
    extra = json.loads(sys.argv[3]) if len(sys.argv)>3 else None
    extra = {int(k):v for k,v in extra.items()} if extra else None
    spec = spec_j1(extra); ev = build_script(REF, spec)
    keys = sorted(spec); caps = [keys.index(j) for j in range(48, 62)]
    extra_live = ['w $3792c $4e $75'] if 'noen' in tag else []
    fl, txt = run(tag, ev, caps=caps, live=(LIVE[live] + extra_live), tail_s=3.0, max_wait=60)
    open(f'sc/{tag}.tok','w').write(' '.join(tokens(txt)))
    print(tag, len(fl))
