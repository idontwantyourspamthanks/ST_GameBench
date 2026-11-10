import sys, cmp
tag=sys.argv[1]; n=int(sys.argv[2]) if len(sys.argv)>2 else 30
Ar,Br,Ag,Bg=cmp.compare(tag)
keys=sys.argv[3].split(',') if len(sys.argv)>3 else ['X','Y','alt','agl','g36','spd','thr','bank','blk','s767e','flg','type','r5a']
for i,r in enumerate(Ar[:n]): print('A',i,' '.join(f"{k}={r[k]}" for k in keys))
