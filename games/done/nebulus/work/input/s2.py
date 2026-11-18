from scripted2 import *
import sys
txt=open('sc/s1/log.txt').read(); ref=parse_flips(txt)
def spec_s2():
    spec = {45: 0x08}
    for st in (65, 95, 125, 155, 185):
        for k in range(4): spec[st+k] = 0x88
        spec[st+4] = 0x08
    spec[200] = 0x00
    return spec
if __name__=='__main__':
    tag, live = sys.argv[1], sys.argv[2]
    ev = build_script(ref, spec_s2())
    fl, txt = run(tag, ev, live=live, tail_s=6.0)
    open(f'sc/{tag}.tok','w').write(' '.join(tokens(txt)))
    print(tag, len(fl)); print(' '.join(tokens(txt))[:700])
