import pickle,sys
tag=sys.argv[1]
A=pickle.load(open(f'/tmp/p3b/t1_A_{tag}.pkl','rb')); B=pickle.load(open(f'/tmp/p3b/t1_B_{tag}.pkl','rb'))
Bg=[b for b in B[1:] if b['PH']==5]; Ag=A[1:]
keys=['X','Y','H','clk','cd','alt','bank','lean','thr','spd']
n=int(sys.argv[2]) if len(sys.argv)>2 else len(Ag)
print('groups A',len(Ag),'B',len(Bg))
bad=0
print('k | X Y H $eb8c $6290 $764c bank lean thr spd (A | B) ')
for k in range(min(n,len(Ag),len(Bg))):
    a,b=Ag[k],Bg[k]
    eq=[x for x in keys if a[x]!=b[x]]
    print(k+1,[a[x] for x in keys],[b[x] for x in keys],'EQ' if not eq else 'DIFF '+','.join(eq))
    bad+=bool(eq)
print('mismatching groups:',bad)
