import struct,sys
def reloc(f, base):
    tl=struct.unpack('>L',f[2:6])[0]
    t=bytearray(f[28:28+tl]); rel=f[28+tl:]
    off=struct.unpack('>L',rel[:4])[0]; i=4; offs=[off]
    while rel[i]!=0:
        if rel[i]==1: off+=254; i+=1; continue
        off+=rel[i]; i+=1; offs.append(off)
    for o in offs:
        t[o:o+4]=struct.pack('>L',struct.unpack('>L',t[o:o+4])[0]+base)
    return t,offs
