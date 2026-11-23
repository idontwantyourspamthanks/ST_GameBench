"""Compare level-start RAM dumps (lvlN.bin) of the LOOKS campaign: which regions depend on the record's mission/tower bytes."""
import sys,hashlib,struct,glob
D=sys.argv[1]
names={0:'M1T1',1:'M1T2',2:'M1T3',3:'M1T4',4:'M1T5',5:'M1T6',6:'M1T7',7:'M1T8',8:'M2T1',9:'M2T4'}
dumps={}
for i in range(10):
    try: dumps[i]=open(f'{D}/lvl{i}.bin','rb').read()
    except FileNotFoundError: pass
def md5(d,a,n): return hashlib.md5(d[a:a+n]).hexdigest()[:8]
regions={'palette $351ac(32)':(0x351ac,32),'raster pal $40390-$403e0':(0x40390,0x50),'sprite table $316e0(2560)':(0x316e0,2560),
 'sprites $14560-$24be0':(0x14560,0x24be0-0x14560),'$24be0-$2fae0':(0x24be0,0x2fae0-0x24be0),'mask buf $36406(512)':(0x36406,512),'$100e0-$11100':(0x100e0,0x1020),
 'grid $327f0(4096)':(0x327f0,4096),'time $3ad98(6)':(0x3ad98,6)}
print('region'.ljust(28),*[names[i].ljust(9) for i in dumps])
for r,(a,n) in regions.items():
    print(r.ljust(28),*[md5(dumps[i],a,n).ljust(9) for i in dumps])
