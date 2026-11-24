"""python3 ext_summary.py res/ext_X_8.json ... : extras per tick histogram from the pass records (NEXTRA of record i+1 = extras of the pass of record i)."""
import json, sys, collections
for f in sys.argv[1:]:
    d = json.load(open(f)); R = d['rows']
    if len(R) < 5: print(f, 'too few rows', len(R)); continue
    mhz = d['args'][2]; setn = d['args'][1]
    # pass i's extras are visible in record i+1
    per = []
    for a, b in zip(R, R[1:]):
        if b['p'] == a['p'] + 1: per.append(dict(p=a['p'], ex=b['nextra'], speech=b['speech'] != 0, vbl=a['vbl'], mode=a['mode'], t=a['t1226']))
    n = len(per)
    dv = R[-1]['vbl'] - R[0]['vbl']; npass = len(R) - 1
    fr = R[-1]['frames'] - R[0]['frames']; gr = R[-1]['groups'] - R[0]['groups']; tk = R[-1]['ticks'] - R[0]['ticks']
    print(f"== {f.split('/')[-1]}: set {setn} {mhz} MHz, {len(R)} pass records over {dv} VBL ({dv/50:.0f} s @50Hz): {npass/dv*50:.3f} passes/s, {dv/max(npass,1):.2f} VBL/pass")
    print(f"   counters over the window: extra frames {fr}, ticks with >=1 extra (groups) {gr}, ticks that entered the group code {tk}; displayed fps (passes+extras)/time = {(npass+fr)/dv*50:.2f}")
    h = collections.Counter(x['ex'] for x in per)
    print("   extras per tick histogram (pass records):", dict(sorted(h.items())), " -> frames per tick (main+extras):", {k + 1: f"{100*v/n:.1f}%" for k, v in sorted(h.items())})
    print(f"   mean extras/tick {sum(x['ex'] for x in per)/n:.3f}; ticks with >= 1 extra {100*sum(1 for x in per if x['ex']>0)/n:.1f} %; with exactly 1 extra (2 frames) {100*h.get(1,0)/n:.1f} %")
    for nm, sel in (('speech passes', [x for x in per if x['speech']]), ('no-speech passes', [x for x in per if not x['speech']])):
        if sel: print(f"   {nm}: n {len(sel)} mean extras {sum(x['ex'] for x in sel)/len(sel):.3f}  hist {dict(sorted(collections.Counter(x['ex'] for x in sel).items()))}")
    rs = [i for i, (a, b) in enumerate(zip(R, R[1:])) if b['p'] + 20 < a['p']]
    for i in rs:
        w = [x['ex'] for x in per if abs(x['p']) >= 0][max(0, i - 6):i + 14]
        print(f"   restart at record {i} (pass {R[i]['p']} -> {R[i+1]['p']}, VBL {R[i]['vbl']}): extras of the passes around it {w}; $1226 around: {[r['t1226'] for r in R[max(0,i-4):i+3]]}")
    tos = [r for r in R if r['t1226'] != 0]
    print(f"   passes with $1226 != 0 (time-out sequence): {len(tos)}; non-race mode ($1021 != 2) records {sum(1 for r in R if r['mode'] != 2)}")
    print("   skip reasons RSN (0 no slot copy, 1 off, 2 standing, 3 too fast, 4 $1024, 5 $1021) first/last:", R[0]['rsn'], R[-1]['rsn'])
