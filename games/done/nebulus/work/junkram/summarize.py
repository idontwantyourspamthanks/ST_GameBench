"""summarize.py FILE.jsonl...: count per (build, machine, mode): boots, NEPO, NEPF, self-opening editors, trainers active, dead input, VBL stopped, exceptions, F10 ok."""
import sys, json, collections
rows = [json.loads(l) for f in sys.argv[1:] for l in open(f) if l.strip().startswith('{')]
g = collections.OrderedDict()
for r in rows:
    k = (r.get('build'), r.get('machine'), r.get('mode'))
    g.setdefault(k, []).append(r)
print(f"{'build':14}{'machine':8}{'mode':22}{'boots':>6}{'NEPO':>6}{'NEPF':>6}{'selfopen':>9}{'trainers':>9}{'deadinput':>10}{'novbl':>6}{'exc':>5}{'f10ok':>6}{'reused':>8}{'err':>5}")
for (b, m, mo), rs in g.items():
    n = len(rs)
    f10 = sum(1 for r in rs if r.get('f10_open') and r.get('f10_close'))
    reused = sorted({r['sites'][4:8] for r in rs if r.get('sites')})
    print(f"{b:14}{m:8}{mo:22}{n:6}{sum(r.get('marker')=='NEPO' for r in rs):6}{sum(r.get('marker')=='NEPF' for r in rs):6}{sum(bool(r.get('self_open')) for r in rs):9}"
          f"{sum(bool(r.get('trainers_active')) and r.get('marker')=='NEPO' for r in rs):9}{sum(not r.get('input_ok') for r in rs):10}{sum(not r.get('vbl_runs') for r in rs):6}"
          f"{sum(bool(r.get('exc')) for r in rs):5}{f10:6}{','.join(reused):>8}{sum('error' in r for r in rs):5}")
