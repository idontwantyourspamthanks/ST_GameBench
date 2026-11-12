import sys,re
sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parent))
from an_prof import load
KEYS={'flip $26e98':0x26e98,'classify loop $1d8f8':0x1d8f8,'cull hook $b5b00':0xb5b00,'keep path $1d97a':0x1d97a,'lookup $1da66':0x1da66,'xform $1da92':0x1da92,
'alloc $1da7a':0x1da7a,'polygen cell $1ebf6':0x1ebf6,'prefix $1ec28':0x1ec28,'AND test $1ecba':0x1ecba,'emit1 $1ed46':0x1ed46,'emit2 $1ed66':0x1ed66,'proj vert $1fa1a':0x1fa1a,'divide $1fa44':0x1fa44,'stream poly $1fa68':0x1fa68,'fill $38c6e':0x38c6e}
for p in sys.argv[1:]:
    d=load(p)
    fl=d['addr'].get(0x26e98,(0,0,''))[0]
    print(p,'flips',fl,'total cycles',d['total'],'per flip',d['total']/max(fl,1))
    for k,a in KEYS.items():
        c=d['addr'].get(a,(0,0,''))
        print('  %-24s count %7d  per flip %8.2f   cycles/flip %9.1f'%(k,c[0],c[0]/max(fl,1),c[1]/max(fl,1)))
