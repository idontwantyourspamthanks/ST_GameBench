#!/usr/bin/env python3
"""Unpack the POP2.TOS of the ICS/Illegal/Vmax Populous 2 cracks (a Pack-Ice style backward bit-stream packer).
Transliteration of the depacker at text offset $56 (relocated to $167e+$20) of that program.
usage: unpack_pop2.py POP2.TOS out.bin   -> out.bin = RAM image from $1770; prints load base and used packed length
"""
import struct, sys
d=open(sys.argv[1],'rb').read()
text=d[0x1c:0x1c+struct.unpack('>I',d[2:6])[0]]
STREAM=0x128
# the program copies $16ff0 bytes starting at text+$128 to $1770
PLEN=0x16ff0
stream=bytearray(text[STREAM:STREAM+PLEN])
# depacker: a1=start ($1770 -> 0), d0=PLEN
a0=PLEN
def rd_long():
    global a0
    a0-=4
    return struct.unpack('>I',stream[a0:a0+4])[0]
size=rd_long()           # movea.l -(a0),a2 ; adda.l a1,a2
d5=rd_long()             # move.l -(a0),d5
d0=rd_long()
d5^=d0
out=bytearray(size)
a2=size
class S: pass
st=S(); st.d0=d0; st.d5=d5
def bit():
    # lsr.l #1,d0 ; bne -> carry; else refill (bsr $102: d0=-(a0); eor d5; ccr=$10 (X set); roxr.l #1,d0 -> carry out, X into top)
    c=st.d0&1; st.d0>>=1
    if st.d0!=0: return c
    st.d0=rd_long(); st.d5^=st.d0
    c=st.d0&1; st.d0=(st.d0>>1)|0x80000000
    return c
def getbits(n):   # $10e: d1=n-1 ... returns d2 (n bits MSB first)
    v=0
    for _ in range(n):
        v=(v<<1)|bit()
    return v
a=a2
# main loop $64
while True:
    # $64: lsr d0 ; bcs $aa (match)
    if bit()==0:
        # literal run
        d1=8; d3=1
        if bit()==0:   # $7a: bcs $d6 -> (match with d1=8? ) careful
            pass
        # replicate exactly:
        pass
    break
