import pickle,sys
sc=sys.argv[1]; b=sys.argv[2] if len(sys.argv)>2 else 'B2'; lim=int(sys.argv[3]) if len(sys.argv)>3 else 99
A=pickle.load(open(f't6_A_768_{sc}.pkl','rb')); B=pickle.load(open(f't6_{b}_768_{sc}.pkl','rb'))
Ag=A[1:]; Bg=[x for x in B[1:] if x['PH']==5]
keys=['X','Y','H','clk','cd','alt','blk','spd','bank','type']
bad=0; shown=0
for k in range(min(len(Ag),len(Bg))):
    a,c=Ag[k],Bg[k]
    d=[x for x in keys if a[x]!=c[x]]
    bad+=bool(d)
    if shown<lim and (d or k<4 or k%8==0 or a['blk']):
        print(k+1,[a[x] for x in keys],[c[x] for x in keys],'EQ' if not d else 'DIFF '+','.join(d)); shown+=1
print(sc,b,'groups',min(len(Ag),len(Bg)),'mismatching',bad)
