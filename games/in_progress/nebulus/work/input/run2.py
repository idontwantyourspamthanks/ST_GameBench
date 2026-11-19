import sys
from e2e2 import *
def go(snap, tag, what, key, n, mhz, hold=0.4, seed=7, pre=None):
    h = Nebulus(snapshot=snap, workdir='/tmp/strun-nin2e')
    rnd=random.Random(seed); rows=[]
    try:
        time.sleep(1.5)
        if mhz!=8: h.set_cpuclock(mhz)
        time.sleep(1.0)
        for k in range(n):
            for _ in range(12):
                if h.peekw(0x33a20)==0: break
                time.sleep(0.4)
            time.sleep(rnd.uniform(0.3,0.6))
            acts=[(0,'down',key),(hold,'up',key)]
            toks=trace(h, acts)
            r=analyze(toks, what); rows.append(r); print(tag,k,r,flush=True)
            time.sleep(0.8)
    finally:
        h.close()
    return rows
if __name__=='__main__':
    snap,tag,what,key,n,mhz = sys.argv[1:7]
    rows=go(snap,tag,what,key,int(n),int(mhz))
    json.dump(rows,open(f'e2e_{tag}.json','w'))
