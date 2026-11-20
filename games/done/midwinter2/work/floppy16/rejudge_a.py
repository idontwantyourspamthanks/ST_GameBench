"""Re-judge every gate (a) trace still in /tmp/mw2f with the final fdctrace.gate_first_restore; writes out/RESULTS_A.txt (raw gate lines)."""
import sys, io
sys.path.insert(0, '.')
import fdctrace as F
RUNS = [  # name, stock FDC wait?, expected verdict
    ('g_ste8_v16', False, 'PASS'), ('g_mste8_v16', False, 'PASS'), ('g_mste16_v16', False, 'PASS'),
    ('g_ste8_v14', True, 'FAIL'), ('g_mste16_v14', True, 'FAIL'), ('g_mste16_nowait', True, 'FAIL'),
    ('g_ste8_v15', True, 'info'), ('g_mste16_v15', True, 'info'), ('g_mste16_nopark', False, 'info'),
    ('sg_ste8_v16', False, 'PASS'), ('sg_mste8_v16', False, 'PASS'), ('sg_mste16_v16', False, 'PASS')]
out = []
for n, stock, exp in RUNS:
    buf = []
    ok, _ = F.gate_first_restore(n, f'/tmp/mw2f/{n}/fdc.trace', stock, buf.append)
    verdict = 'PASS' if ok else 'FAIL'
    out.append(f'=== {n} (expected {exp})')
    out += [l for l in buf if not l.startswith('  game type I')]
    out.append(f'RESULT {n}: {verdict}' + ('' if exp == 'info' else (' (as expected)' if verdict == exp else ' (UNEXPECTED)')))
open('out/RESULTS_A.txt', 'w').write('\n'.join(out) + '\n')
print('\n'.join(out))
