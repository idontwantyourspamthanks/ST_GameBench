import re, sys, json
import os
CYC = int(os.environ.get("CYC", 160256))
def parse(path):
    txt = open(path, errors='replace').read()
    # records: tag, VBL, FrameCycles (+ m dump after tag 17)
    pat = re.compile(r"> e \$([0-9a-f]+)\n= [^\n]*#(\d+) \(dec\)[^\n]*\n> e VBL\n= [^\n]*#(\d+) \(dec\)[^\n]*\n> e FrameCycles\n= [^\n]*#(\d+) \(dec\)[^\n]*\n((?:> m [^\n]*\n(?:[0-9A-Fa-f]{8}:[^\n]*\n)+)*)")
    ev = []
    for m in pat.finditer(txt):
        tag = int(m.group(2)); vbl = int(m.group(3)); fc = int(m.group(4)); extra = m.group(5)
        mem = {}
        for ln in extra.splitlines():
            mm = re.match(r"([0-9A-Fa-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln)
            if mm:
                a = int(mm.group(1), 16)
                for i, x in enumerate(bytes.fromhex(mm.group(2).replace(' ', ''))): mem[a + i] = x
        ev.append((tag, vbl, fc, mem))
    return ev
if __name__ == '__main__':
    ev = parse(sys.argv[1])
    print(len(ev))
    from collections import Counter
    print(Counter(e[0] for e in ev))
    # ISR latch events: FrameCycles distribution
    l = [e[2] for e in ev if e[0] == 10]
    print('latch FC min/max', min(l), max(l), sorted(l)[len(l)//2])
    for e in ev[:60]: print(e[:3])
