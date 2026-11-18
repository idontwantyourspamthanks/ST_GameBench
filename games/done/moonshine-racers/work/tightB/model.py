"""Python model of the compiled player-car draw (tightB).  Generates the code bytes the 68k generator must produce."""
import struct
GAME='/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
def rows_words(mem, p, rows):
    out=[]
    for r in range(rows):
        W=struct.unpack('>12H', mem[p+r*24:p+r*24+24])
        P=[[W[0],W[1],W[6],W[9]],[W[2],W[3],W[7],W[10]],[W[4],W[5],W[8],W[11]]]
        out.append(P)
    return out
def shifted(P,s):
    res=[]
    for pl in range(3):
        src=[0]+P[pl]+[0]
        d=[(((src[c]<<16)|src[c+1])>>s)&0xffff for c in range(5)]
        res.append(d)
    return res
def gen(mem,p,rows,s):
    code=bytearray()
    for r,P in enumerate(rows_words(mem,p,rows)):
        d=shifted(P,s)
        for c in range(5):
            p0,p1,p2=d[0][c],d[1][c],d[2][c]
            M=p0|p1|p2
            off=r*160+c*8
            if M==0: continue
            if M==0xffff:
                code+=struct.pack('>HIH',0x277c,(p0<<16)|p1,off)
                if p2==0: code+=struct.pack('>HH',0x42ab,off+4)
                else: code+=struct.pack('>HIH',0x277c,p2<<16,off+4)
            else:
                nm=(~M)&0xffff; imm=(nm<<16)|nm
                code+=struct.pack('>HIH',0x02ab,imm,off)
                code+=struct.pack('>HIH',0x02ab,imm,off+4)
                if p0 and p1: code+=struct.pack('>HIH',0x00ab,(p0<<16)|p1,off)
                elif p0: code+=struct.pack('>HHH',0x006b,p0,off)
                elif p1: code+=struct.pack('>HHH',0x006b,p1,off+2)
                if p2: code+=struct.pack('>HHH',0x006b,p2,off+4)
    code+=struct.pack('>H',0x4e75)
    return bytes(code)
def cycles(code):
    # rough: count by opcode
    i=0;cy=0
    while i<len(code):
        op=struct.unpack('>H',code[i:i+2])[0]
        if op==0x277c: cy+=28;i+=8
        elif op==0x42ab: cy+=30;i+=4
        elif op==0x02ab or op==0x00ab: cy+=32 if True else 0;i+=8
        elif op==0x006b: cy+=20;i+=6
        elif op==0x4e75: cy+=16;i+=2
        else: raise Exception(hex(op))
    return cy
if __name__=='__main__':
    mem=open(GAME+'/work/dumps/ram_race_start.bin','rb').read()
    tot=0
    for i in range(15):
        p,w,h,xo,yo,nib=struct.unpack('>IhhhhH',mem[0x2156a+i*14:0x2156a+i*14+14])
        c=gen(mem,p,h,2); tot+=len(c); print(i,w,h,len(c),cycles(c))
    c=gen(mem,182996 and struct.unpack('>I',mem[182996:182996+4])[0],21,4); print('layer',len(c),cycles(c)); tot+=len(c)
    print('total',tot)
