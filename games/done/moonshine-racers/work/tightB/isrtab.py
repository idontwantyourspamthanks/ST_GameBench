import json, sys
print(f"{'variant':44s} {'TB n':>5s} {'late>50':>8s} {'late>100':>9s} {'max late':>9s} | {'VBL n':>5s} {'VBL LC median':>13s} {'max':>5s}")
for f in sys.argv[1:]:
    d = json.load(open(f)); v = f.split('/')[-1][:-5].replace('isr2_', '').replace('isr_', '')
    late = sorted(((lc - 480 + 256) % 512) - 256 for lc, _, _ in d['tb']); n = len(late)
    vl = sorted(x[0] for x in d['vbl'])
    print(f"{v:44s} {n:5d} {sum(1 for x in late if x > 50):8d} {sum(1 for x in late if x > 100):9d} {late[-1]:9d} | {len(vl):5d} {vl[len(vl)//2]:13d} {vl[-1]:5d}")
