import struct,sys
A='/home/ryan/Code/Amiga/gamebench/games/in_progress/Midwinter-2/work/dumps/mwii_flat.bin'
d=open(A,'rb').read()
OFF=0x270d0
# wrappers: moveq #n,d0 ; bsr.w $25aea ; ... in flat
tgt=0x25aea
wr={}
for i in range(0x20000,0x40000,2):
    if d[i]==0x70 and d[i+2:i+4]==b'\x61\x00':
        disp=struct.unpack('>h',d[i+4:i+6])[0]
        if i+2+2+disp==tgt:
            wr[i]=d[i+1]
        # bsr.w base = address of the extension word = i+2+2
print('wrappers (flat addr -> tune id):', {hex(k):hex(v) for k,v in sorted(wr.items())})
# also moveq ; bsr.w pattern with unknown
for k,v in sorted(wr.items()):
    ent=k  # wrapper entry
    op=ent+OFF
    ca=[]
    a=struct.pack('>I',op)
    for pre in (b'\x4e\xb9',b'\x4e\xf9'):
        j=0
        while True:
            j=d.find(pre+a,j)
            if j<0:break
            ca.append((hex(j),pre.hex())); j+=1
    print(hex(k),'id',hex(v),'callers',ca)
