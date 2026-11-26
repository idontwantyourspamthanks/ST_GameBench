import os, re
L = '/tmp/nlcv/x/logs/'
rows = [('e208.py (conveyors)', 'e208_{m}'), ('e200.py (pickers, crumble item, playtest of the pick, store round trip)', 'e200_{m}'), ('e201.py (crumble in play, conveyor levels from the manager)', 'e201_{m}'),
        ('e203.py (door pairs, tunnel, original tower)', 'e203_{m}'), ('e150.py (shortcut keys, lifts, playtest, T/E)', 'e150_{m}'), ('e170.py (cold boot: NEPO, site count 33, hooks, F10 / D)', 'e170_{m}'),
        ('e180.py --quick (odd records; STE odd2+stress01+stress05, Mega STE odd2+stress05)', 'e180q_{m}'), ('fl_ui.py (floppy game disk cold boot, real FDC)', 'fl_ui_{m}')]
def cell(n):
    p = L + n + '.log'
    if not os.path.exists(p): return 'not run'
    t = open(p, errors='replace').read()
    ps = len(re.findall(r'^PASS', t, re.M)); fl = len(re.findall(r'^FAIL ', t, re.M)); m = re.search(r'^FAILS (.*)$', t, re.M)
    if not m: return f'INCOMPLETE ({ps} PASS, {fl} FAIL, no FAILS line)'
    return f'{ps} PASS, {fl} FAIL' + ('' if m.group(1).strip() == '[]' else ' ' + m.group(1)[:200])
print('| gate | STE 1 MB TOS 1.62 | Mega STE 4 MB TOS 2.06 | ST 1 MB TOS 1.04 |\n|---|---|---|---|')
for name, pat in rows:
    print(f'| `{name}` | ' + ' | '.join(cell(pat.format(m=m)) for m in ('ste', 'megaste', 'st')) + ' |')
