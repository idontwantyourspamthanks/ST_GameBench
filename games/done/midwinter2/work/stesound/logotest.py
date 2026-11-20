# boot DISKDIR (STE 1.62) to the orange prompt and save the logo screenshot: python3 logotest.py NAME DISKDIR
import sys, os
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'probe.py')).read()
i = src.index("try:\n    t0 = time.time()")
head = src[:i]
body = '''try:
    t0 = time.time()
    while time.time() - t0 < 420:
        time.sleep(4)
        if sdiff(ins, (280, 360, 560, 420)) < 0.3:
            break
    else:
        raise RuntimeError('never saw the orange prompt')
    time.sleep(3)
    L('shot', h.shot(OUT / f'{name}_logo.png'))
finally:
    h.close()
'''
sys.argv = [sys.argv[0], sys.argv[1], 'ste', '162', '8', '1', sys.argv[2]]
exec(compile(head + body, 'logotest_gen', 'exec'))
