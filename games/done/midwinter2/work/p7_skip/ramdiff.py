import sys, numpy as np
a=np.fromfile(sys.argv[1],dtype=np.uint8); b=np.fromfile(sys.argv[2],dtype=np.uint8)
lo=int(sys.argv[3],16) if len(sys.argv)>3 else 0
d=np.nonzero(a!=b)[0]
# skip screens
d=[x for x in d if not (0x60000<=x<0x80000)]
iv=[]
for x in d:
    if iv and x-iv[-1][1]<=3: iv[-1][1]=x
    else: iv.append([x,x])
for s,e in iv:
    print(f'{s:06x}-{e:06x} {e-s+1:4d}  {a[s:e+1][:16].tobytes().hex()} -> {b[s:e+1][:16].tobytes().hex()}')
print(len(d),'bytes differ,',len(iv),'ranges')
