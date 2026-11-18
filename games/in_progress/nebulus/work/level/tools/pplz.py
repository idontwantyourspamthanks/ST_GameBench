"""PP-LZ (Gamex 'C3' file) codec for NEBEXE.FIC. Format (verified: decodes NEBEXE.FIC to exactly 271849 B, consumes 166616):
 header 32 B: 'C3' + u32 packed_len + u32 unpacked_len + name...; body tokens:
   0x00 end | 0x01-0x7f n literal bytes | 0x80|c : copy c+3 bytes, 1-byte offset | 0xc0|c : copy c+4 bytes, 2-byte BE offset
 (disasm-equivalent of tools/pp_depack.py: cnt=c&0x3f; +2 (1B off) / +3 (2B off); loop cnt+1 times)."""
import struct
HDR=32
def unpack(f):
    assert f[:2]==b'C3'
    plen,ulen=struct.unpack('>II',f[2:10])
    src=f[HDR:]; out=bytearray(); src_of=[]   # src_of[i]: packed offset (file) if literal else -1
    i=0
    while True:
        c=src[i]; i+=1
        if c==0: break
        if c<0x80:
            for k in range(c): src_of.append(HDR+i+k)
            out+=src[i:i+c]; i+=c; continue
        cnt=c&0x3f
        if c&0x40: cnt+=3; off=(src[i]<<8)|src[i+1]; i+=2
        else: cnt+=2; off=src[i]; i+=1
        for _ in range(cnt+1): out.append(out[-off]); src_of.append(-1)
    assert len(out)==ulen and HDR+i==len(f), (len(out),ulen,HDR+i,len(f))
    return bytes(out),src_of
def pack(data, chain=48):
    """DP-optimal-ish encoder: literal byte ~1.008, 1-byte-offset copy 2 B (len 3..66), 2-byte-offset copy 3 B (len 4..67).
    Returns the 32-byte header + stream (header name copied by pack_file)."""
    n=len(data)
    INF=float('inf')
    best=[INF]*(n+1); best[0]=0.0; prev=[None]*(n+1)
    heads={}
    LIT=1+1/127
    for i in range(n):
        b=best[i]
        if b+LIT<best[i+1]: best[i+1]=b+LIT; prev[i+1]=(i,0,0)
        if i+3<=n:
            key=data[i:i+3]
            cand=heads.get(key)
            if cand:
                lim=min(n-i,67)
                bl1=0;bo1=0;bl2=0;bo2=0
                for p in reversed(cand[-chain:]):
                    off=i-p
                    if off>65535: break
                    m=3
                    while m<lim and data[p+m]==data[i+m]: m+=1
                    if off<=255 and m>bl1: bl1,bo1=m,off
                    if m>bl2: bl2,bo2=m,off
                    if bl2==lim and bl1==lim: break
                if bl1>=3:
                    for ln in range(3,min(bl1,66)+1):
                        if b+2<best[i+ln]: best[i+ln]=b+2; prev[i+ln]=(i,ln,bo1)
                if bl2>=4:
                    for ln in range(4,bl2+1):
                        if b+3<best[i+ln]: best[i+ln]=b+3; prev[i+ln]=(i,ln,bo2)
            heads.setdefault(key,[]).append(i)
    toks=[];i=n
    while i>0:
        j,ln,off=prev[i]; toks.append((j,ln,off)); i=j
    toks.reverse()
    out=bytearray(); lit=[]
    def flush():
        nonlocal lit
        a=lit[0]; end=lit[-1]+1; p=a
        while p<end:
            k=min(127,end-p); out.append(k); out.extend(data[p:p+k]); p+=k
        lit=[]
    for j,ln,off in toks:
        if ln==0:
            lit.append(j) if (not lit or lit[-1]==j-1) else (flush(), lit.append(j))
            continue
        if lit: flush()
        if off<=255 and ln<=66: out.append(0x80|(ln-3)); out.append(off)
        else: out.append(0xc0|(ln-4)); out+=struct.pack('>H',off)
    if lit: flush()
    out.append(0)
    return bytes(out)
def pack_file(orig, data):
    body=pack(data)
    hdr=bytearray(orig[:HDR]); hdr[2:6]=struct.pack('>I',len(body)); hdr[6:10]=struct.pack('>I',len(data))
    return bytes(hdr)+body
