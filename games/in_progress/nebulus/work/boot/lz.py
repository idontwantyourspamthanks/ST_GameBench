def lz(src):
    out=bytearray(); i=0
    while True:
        c=src[i]; i+=1
        if c==0: break
        if c<0x80:
            out+=src[i:i+c]; i+=c; continue
        cnt=c&0x3f
        if c&0x40:
            cnt+=3; off=(src[i]<<8)|src[i+1]; i+=2
        else:
            cnt+=2; off=src[i]; i+=1
        for _ in range(cnt+1): out.append(out[-off])
    return bytes(out), i
