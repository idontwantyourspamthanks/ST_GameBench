import json,sys
for f in sys.argv[1:]:
    for l in open(f):
        d=json.loads(l)
        print(f"{d['machine']:8} {d['mode']:14} seed {d['seed']}: title={d['title']} marker={d['marker']} sites={d['sites']} v70={d['v70']} f10={ {k:v for k,v in d.items() if 'f10' in k.lower() or 'exc' in k.lower() or 'alive' in k or 'isr' in k or 'vbl' in k} }")
