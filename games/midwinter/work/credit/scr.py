import sys
def decode(ram, base=0x78000):
    rows=[]
    for y in range(200):
        r=[]
        for g in range(20):
            o=base+y*160+g*8
            w=[(ram[o+2*p]<<8)|ram[o+2*p+1] for p in range(4)]
            for b in range(16):
                r.append(sum(((w[p]>>(15-b))&1)<<p for p in range(4)))
        rows.append(r)
    return rows
if __name__=='__main__':
    ram=open(sys.argv[1],'rb').read()
    rows=decode(ram, int(sys.argv[2],16) if len(sys.argv)>2 else 0x78000)
    for y in range(170,200):
        print(y, ''.join('%x'%c if c else '.' for c in rows[y]))
