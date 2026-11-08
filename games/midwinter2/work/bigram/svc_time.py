"""VBLs spent inside PP's HAGA service ($fc4 entry .. $1164 rts) from a <cell>_events.txt log,
up to the M/J/K screen (v_mjk from <cell>.json) and for the whole run."""
import re, sys, json
for cell in sys.argv[1:]:
    t = open(f'work/bigram/{cell}_events.txt').read()
    j = json.load(open(f'work/bigram/{cell}.json'))
    ev = re.findall(r'> e VBL\n= [^\n]*#(\d+) \(dec\)[^\n]*\n> e (1111|2222)\n', t)
    pairs, ent = [], None
    for v, k in ev:
        v = int(v)
        if k == '1111': ent = v
        elif ent is not None: pairs.append((ent, v)); ent = None
    def s(ps): return len(ps), sum(b - a for a, b in ps)
    pre = [p for p in pairs if p[1] <= j['v_mjk']]
    print(f"{cell}: until M/J/K (VBL {j['v_mjk']}): calls %d, VBL in service %d | whole run: calls %d, VBL %d | max call %d"
          % (*s(pre), *s(pairs), max((b - a for a, b in pairs), default=0)))
