import sys
d=sys.argv[1]
sites=[0xb632,0xb6f4,0xb800,0xb80c,0xb8ec,0xb93a,0xb940,0xb946,0xbb7c,0xbbf8,0xbc02]
m=[open(f"{d}/m{s:x}.bin","rb").read() for s in sites]
back=int.from_bytes(m[0][0x3c510:0x3c514],'big'); front=int.from_bytes(m[0][0x3c50c:0x3c510],'big')
print("back",hex(back),"front",hex(front))
def rng(a,b,gap=8):
    out=[];cur=None
    # fast compare via chunks
    for i in range(0,len(a),4096):
        if a[i:i+4096]==b[i:i+4096]: continue
        for j in range(i,min(i+4096,len(a))):
            if a[j]!=b[j]:
                if cur and j-cur[1]<=gap: cur[1]=j+1
                else:
                    if cur: out.append(tuple(cur))
                    cur=[j,j+1]
    if cur: out.append(tuple(cur))
    return out
for i in range(len(sites)-1):
    rs=rng(m[i],m[i+1])
    scr=0; other=[]
    for s,e in rs:
        if back<=s<back+32000 or front<=s<front+32000: scr+=e-s
        else: other.append((s,e))
    print(f"{sites[i]:x}->{sites[i+1]:x}: ranges {len(rs)}, screen bytes {scr}, other ranges {len(other)} bytes {sum(e-s for s,e in other)}")
    for s,e in other[:40]:
        print(f"     {s:05x}-{e:05x} {m[i][s:e][:8].hex()} -> {m[i+1][s:e][:8].hex()}")
