import sys, vh, pickle
from concurrent.futures import ThreadPoolExecutor
snap = sys.argv[1]; n = int(sys.argv[2]); tag = sys.argv[3]
pokes = sys.argv[4].split(';') if len(sys.argv) > 4 and sys.argv[4] else []
live = vh.W / 'live' / (sys.argv[5] if len(sys.argv) > 5 else 'p3b_all')
def A(): return vh.trace(vh.ROOT / 'work/snapshots' / snap, None, pokes, 'pc = $3158c', n, tag + '_A')
def B(): return vh.trace(vh.ROOT / 'work/snapshots' / snap, str(live), pokes, 'pc = $3158c', n * 5 + 8, tag + '_B')
with ThreadPoolExecutor(2) as ex:
    fa = ex.submit(A); fb = ex.submit(B)
    a = fa.result(); b = fb.result()
pickle.dump(([s.m for s in a], [s.m for s in b]), open(vh.OUT / (tag + '.pkl'), 'wb'))
print(len(a), len(b))
