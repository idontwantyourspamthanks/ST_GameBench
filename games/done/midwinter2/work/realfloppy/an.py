import struct,sys,glob
def bpb(b):
    g=lambda o,n:int.from_bytes(b[o:o+n],'little')
    return dict(jmp=b[0:2].hex(), oem=b[2:8], serial=b[8:11].hex(), bps=g(0xb,2), spc=b[0xd], res=g(0xe,2), nfat=b[0x10], ndir=g(0x11,2), nsec=g(0x13,2), media=hex(b[0x15]), spf=g(0x16,2), spt=g(0x18,2), sides=g(0x1a,2), hidden=g(0x1c,2))
for f in sorted(glob.glob('v1[45]/*.st'))+['../../FILES/FFA','../../FILES/FFB','../../FILES/FFC','../../FILES/FFD']:
    b=open(f,'rb').read()
    s=sum(struct.unpack('>256H',b[:512]))&0xffff
    print(f,len(b),len(b)/512,len(b)%512,'bootsum=%04x'%s)
    print('  ',bpb(b))
    # nonzero/F6 stats per track-side
    ts=[]
    for i in range(160):
        c=b[i*4608:(i+1)*4608]
        if len(c)<4608: break
        if c==b'\xf6'*4608: ts.append('F')
        elif c==bytes(4608): ts.append('0')
        else: ts.append('d')
    print('  ',''.join(ts))
