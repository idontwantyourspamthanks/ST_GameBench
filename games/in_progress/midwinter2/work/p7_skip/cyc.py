import sys
sys.path.insert(0,'/home/ryan/Code/AtariST/work/p7_ck')
sys.path.insert(0,'/home/ryan/Code/AtariST/midwinter2/work/p7_ck')
import ck
from concurrent.futures import ThreadPoolExecutor
snap=sys.argv[1]; k1=int(sys.argv[2]); k2=int(sys.argv[3])
sets=[(None if x=='-' else x) for x in sys.argv[4:]]
import os
os.makedirs('/tmp/ck',exist_ok=True)
with ThreadPoolExecutor(1) as ex:
    fs=[ex.submit(ck.cyc, snap, s, k1, k2, 'sk%d'%i) for i,s in enumerate(sets)]
    print([f.result() for f in fs])
