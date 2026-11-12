import sys
sys.path.insert(0,'.')
def px(buf,base,x,y):
    o=base+y*160+(x//16)*8
    w=[(buf[o+2*p]<<8)|buf[o+2*p+1] for p in range(4)]
    b=15-(x%16)
    return sum(((w[p]>>b)&1)<<p for p in range(4))
def cmp(a,b,tag):
    A=open(a,'rb').read(); B=open(b,'rb').read()
    for nm,base in (('$60000',0x10000),('$70000',0x20000)):
        bd=[i for i in range(32000) if A[base+i]!=B[base+i]]
        pd=[(x,y) for y in range(200) for x in range(320) if px(A,base,x,y)!=px(B,base,x,y)]
        if pd:
            xs=[p[0] for p in pd]; ys=[p[1] for p in pd]
            cols=sorted({px(B,base,*p) for p in pd}); old=sorted({px(A,base,*p) for p in pd})
            print(tag,nm,'bytes differ',len(bd),'pixels',len(pd),'bbox x',min(xs),max(xs),'y',min(ys),max(ys),'old colours',old,'new colours',cols)
        else: print(tag,nm,'identical')
cmp('/tmp/cr/f5_1f620.scr','/tmp/cr/cr_fl.scr','floppy @1f620')
cmp('/tmp/cr/h5_1f644.scr','/tmp/cr/cr_hd.scr','HD     @1f644')
