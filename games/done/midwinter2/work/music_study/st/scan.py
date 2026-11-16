import sys,struct
d=open('work/dumps/ram_ingame_lobos.bin','rb').read()
def scan(addr):
    out=[]
    a=struct.pack('>I',addr)
    for pre in (b'\x4e\xb9',b'\x4e\xf9'):
        i=0
        while True:
            i=d.find(pre+a,i)
            if i<0:break
            out.append((i,pre.hex()))
            i+=1
    # also bsr.w / jsr abs.w
    return out
for t in sys.argv[1:]:
    ad=int(t,16)
    print(hex(ad), [(hex(i),p) for i,p in scan(ad)])
