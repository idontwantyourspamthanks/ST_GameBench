import re, collections
from pathlib import Path
D=Path('work/credit/fontcap')
disk=open('work/floppy/disk_a.st','rb').read(); ram=open('work/dumps/ram_race_start.bin','rb').read()
for k in range(9):
    log=(D/f'{k}.txt').read_text(); m=re.search(r"FF8200:\s+((?:[0-9a-f]{2} ){16})",log,re.I); v=bytes.fromhex(m.group(1).replace(' ',''))
    base=(v[1]<<16)|(v[3]<<8)
    buf=(D/f'{k}_70000.bin').read_bytes()+(D/f'{k}_78000.bin').read_bytes()
    scr=buf[base-0x70000:base-0x70000+32000]
    def pix(x,y):
        o=y*160+(x//16)*8; b=15-(x%16)
        return sum(((int.from_bytes(scr[o+2*i:o+2*i+2],'big')>>b)&1)<<i for i in range(4))
    hits=collections.Counter(); cells=0
    for y in range(0,193,1):
        for cx in range(40):
            rows=bytes(sum((1 if pix(cx*8+bit,y+r) else 0)<<(7-bit) for bit in range(8)) for r in range(8))
            if sum(1 for b in rows if b)>=5 and len(set(rows))>=4:
                cells+=1
                for nm,src in (('ramfont8',ram),('diskA8',disk)):
                    i=src.find(rows)
                    if i>=0: hits[(nm,hex(i))]+=1
    top=hits.most_common(6)
    print('screen',k,'cells',cells,top)
