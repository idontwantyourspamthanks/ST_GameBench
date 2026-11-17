import struct,re,sys
def parse(b,o=0):
    t=b[o:o+20].split(b'\0')[0]
    smp=[]
    for i in range(31):
        s=b[o+20+i*30:o+20+i*30+30]
        name=s[:22].split(b'\0')[0]
        ln,ft,vol,rs,rl=struct.unpack('>HBBHH',s[22:30])
        smp.append((name.decode('latin1'),ln*2,ft,vol,rs*2,rl*2))
    sl=b[o+950]; pos=list(b[o+952:o+952+128]); npat=max(pos)+1
    tot=sum(s[1] for s in smp)
    return dict(title=t,songlen=sl,npat=npat,smp=smp,tot=tot,size=1084+npat*1024+tot,pos=pos[:sl])
if __name__=='__main__':
    for f,o in (('work/amiga/d2/s0175.bin',0x6f8),('work/amiga/d2/s0361.bin',0x6f8)):
        b=open(f,'rb').read(); m=parse(b,o)
        print(f,m['title'],'songlen',m['songlen'],'npat',m['npat'],'samples',sum(1 for s in m['smp'] if s[1]>2),'sample bytes',m['tot'],'modsize',m['size'],'end',hex(o+m['size']),'chunk',len(b))
        for i,s in enumerate(m['smp']):
            if s[1]>2: print('  ',i+1,s)
