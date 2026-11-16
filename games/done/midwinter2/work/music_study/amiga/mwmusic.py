"""Midwinter 2 (Amiga) music data model: parse tunes from the flat MWII dump (operand addresses, base $270d0)."""
import struct
FLAT='/home/ryan/Code/AtariST/gamebench/games/done/midwinter2/work/music_study/amiga/mwii_flat.bin'
B=0x270d0
D=open(FLAT,'rb').read()
H3=0x89478           # hunk 3 (chip DATA) base in operand space
def u16(a): a-=B; return struct.unpack('>H',D[a:a+2])[0]
def u32(a): a-=B; return struct.unpack('>I',D[a:a+4])[0]
TUNE_TABLE=0x57e78
NTUNES=17
# command word -> argument layout (bytes consumed after the command word)
# 0x00 halt, 0x04 instr(ptr), 0x08 next pattern, 0x0c env(ptr), 0x10 slide(4w), 0x14 vib(6w), 0x18 slide off, 0x1c vib off,
# 0x20 rest(1w), 0x24/0x28 channel end, 0x2c filter on, 0x30 filter off, 0x34 vol+=$40 flag, 0x38 goto(ptr->ptr)
ARGS={0x00:0,0x04:4,0x08:0,0x0c:4,0x10:8,0x14:12,0x18:0,0x1c:0,0x20:2,0x24:0,0x28:0,0x2c:0,0x30:0,0x34:0,0x38:4}
NAME={0x00:'HALT',0x04:'INSTR',0x08:'NEXT',0x0c:'ENV',0x10:'SLIDE',0x14:'VIB',0x18:'SLIDEOFF',0x1c:'VIBOFF',0x20:'REST',0x24:'END',0x28:'END',0x2c:'FILTON',0x30:'FILTOFF',0x34:'VOLADD',0x38:'GOTO'}

def tune_ptrs(n):
    a=TUNE_TABLE+16*n
    return [u32(a+4*i) for i in range(4)]

def read_list(p):
    out=[]
    while True:
        v=u32(p); p+=4
        if v==0: break
        out.append(v)
        if len(out)>200: raise ValueError('list too long')
    return out

def parse_pattern(p, limit=4000):
    """returns list of events: ('N',period,dur) or (cmd,args...) until NEXT/HALT/END/GOTO; plus end address"""
    ev=[]
    while len(ev)<limit:
        w=u16(p); p+=2
        if w>0x64:
            d=u16(p); p+=2
            ev.append(('N',w,d)); continue
        if w not in ARGS: ev.append(('?',w)); continue
        n=ARGS[w]
        args=[u16(p+i) for i in range(0,n,2)] if n else []
        raw=[u32(p)] if n==4 else []
        p+=n
        ev.append((NAME[w],w,args,raw))
        if w in (0x00,0x08,0x24,0x28,0x38): break
    return ev,p
