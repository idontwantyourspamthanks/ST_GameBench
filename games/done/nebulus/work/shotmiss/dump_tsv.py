"""Per-attempt, per-loop trajectories of the real-Hatari runs (stock / shoot / fix / shootfix / *_p3) -> work/shotmiss/traj_<variant>.tsv.
Columns: attempt, loop (0 = fire pressed), frog x, ball x y state hopcounter speed, shot x y state counter, player state, hit-test result of sub_03b7d6 (from the sim, which equals Hatari in every loop)."""
import sys, json
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss')
from hatt import *
import scripted2 as S
d = json.load(open(W + 'shotmiss/attempts.json')); ats = [{k: v for k, v in a.items() if k != 'sim_stock'} for a in d['random'] + d['targeted_miss']]
for variant in sys.argv[1:]:
    base = variant.partition('_p')[0]
    timers, srows, starts = sim_chain(ats, fixes=VARIANT[base])
    import gzip, os
    lp = W + f'shotmiss/sc/hm_{variant}/log.txt'
    txt = (gzip.open(lp + '.gz', 'rt', errors='replace') if os.path.exists(lp + '.gz') else open(lp)).read()
    fl = S.parse_flips(txt); hr = hat_rows(timers, fl)
    with open(W + f'shotmiss/traj_{variant}.tsv', 'w') as f:
        f.write('attempt\tloop\tfrog_x\tball_x\tball_y\tball_st\tball_cnt\tball_spd\tshot_x\tshot_y\tshot_st\tshot_cnt\tplayer_st\toverlap_test_hit\tsim_equal\n')
        for k, (at, L) in enumerate(zip(ats, starts)):
            for r in srows:
                if not (L <= r['L'] < L + SPAN): continue
                h = hr.get(r['L'])
                if h is None: continue
                ov = ''.join('H' if x else 'm' for x, _ in r['ov']) or '-'
                f.write(f"{k}\t{r['L']-L}\t{at['fx']}\t{h['bx']}\t{h['by']}\t{h['bst']}\t{h['bcnt']}\t{h['bspd']}\t{h['sx']}\t{h['sy']}\t{h['sst']}\t{h['scnt']}\t{h['pst']}\t{ov}\t{int(all(r[q]==h[q] for q in KEYS))}\n")
    print(variant, 'rows', sum(1 for _ in open(W + f'shotmiss/traj_{variant}.tsv')) - 1)
