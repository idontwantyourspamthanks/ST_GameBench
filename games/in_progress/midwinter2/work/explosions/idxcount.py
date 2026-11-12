import sys, struct
from pathlib import Path
def idx_hist(buf, y0=58, y1=180):
    h=[0]*16
    for y in range(y0,y1):
        for xb in range(20):
            o=y*160+xb*8
            ws=struct.unpack('>4H',buf[o:o+8])
            for bit in range(16):
                h[sum(((ws[p]>>(15-bit))&1)<<p for p in range(4))]+=1
    return h
if __name__=='__main__':
    d=Path(sys.argv[1]); ks=[int(x) for x in sys.argv[2].split(',')]; w=sys.argv[3]
    for k in ks:
        h=idx_hist((d/f'f{k:02d}_{w}.bin').read_bytes()); print(f'{d.name} f{k:02d} {w} idx10(orange)={h[10]} idx11(white)={h[11]}  rows58-179')
