from ui import *
import random, struct, ovl
gd=__import__('pathlib').Path
base=bytearray(open('/tmp/test3.ovl','rb').read())
rng=random.Random(20261118)
files=[]
for i in range(5): files.append(('random%d'%i,bytes(rng.randrange(256) for _ in range(8192))))
b=bytearray(8192); b[:4]=b'NCMP'
for i in range(4,8192): b[i]=rng.randrange(256)
files.append(('magic+random',bytes(b)))
for k in (1,2,3,5,8,12):
    b=bytearray(base)
    for _ in range(k): b[rng.randrange(8,700)]=rng.randrange(256)
    files.append((f'flip{k}',bytes(b)))
b=bytearray(base); b[300:]=bytes(8192-300); files.append(('truncated300',bytes(b)))
b=bytearray(base); b[5]=2; files.append(('version2',bytes(b)))
b=bytearray(base); b[6:8]=b'\x00\x7f'; files.append(('nlev127',bytes(b)))
b=bytearray(base); b[8:10]=b'\x00\xc8'; files.append(('ncamp200',bytes(b)))
b=bytearray(base); b[274]=0; files.append(('rows0',bytes(b)))
b=bytearray(base); b[274]=255; files.append(('rows255',bytes(b)))
b=bytearray(base); b[276:278]=b'\xff\xff'; files.append(('len65535',bytes(b)))
b=bytearray(base); b[16+12]=255; b[16+14:16+30]=bytes([255]*16); files.append(('camp255',bytes(b)))
b=bytearray(base); b[16+14:16+17]=bytes([0x7f,0x90,0x05]); files.append(('badentries',bytes(b)))
b=bytearray(base)
files.append(('valid',bytes(b)))
import sys
only=sys.argv[1:]
files=[f for f in files if not only or f[0] in only]
print(len(files),'files',flush=True)
# title snapshot with the hooks installed
os.system(f"cd {G} && python3 tools/nepatch.py build --out work/editor/build_final --only nt_trainers ed_overlay >/dev/null")
import os.path
if not os.path.exists('/tmp/ed_title.sav'):
    h=start('/tmp/ned90a',gd(E+'build_final')); h.savemem('/tmp/ed_title.sav'); h.close(); time.sleep(1)
res=[]
for n,(name,data) in enumerate(files):
    open('/tmp/fz.ovl','wb').write(data)
    pr=ovl.validate(data)
    h=Nebulus(snapshot='/tmp/ed_title.sav',workdir=f'/tmp/ned91b',game=gd(E+'build_final'))
    try:
        time.sleep(2)
        h.debug('loadbin /tmp/fz.ovl $bc000',0.6)
        poke(h,0x77c80+40,bytes([0,0]))
        v0=h.vbl()
        h.key('F10',hold=0.5); time.sleep(2)
        select(h,'Levels',1.0); items,_=menu(h)
        out=[]
        if items and items[0][0]==6:
            select_i(h,0); select(h,'Edit',1.5); out.append('edit-ok'); h.key('F10',hold=0.5); time.sleep(1.5); select(h,'< back',1.0)
        else:
            select(h,'< back',1.0)
        select(h,'Campaigns',1.0); items,_=menu(h)
        if items and items[0][0]==7:
            select_i(h,0); select(h,'Play',1.0); out.append('play'); time.sleep(8)
        v1=h.vbl()
        log=open('/tmp/ned91b/log.txt',errors='replace').read()
        bad=[l for l in log.splitlines() if ('Address Error' in l or 'Illegal' in l or 'Double' in l) and 'e0' not in l.lower()[:0]]
        mg=grab(h,0xBC000,4)
        r=(name,'validate:'+('ok' if not pr else pr[0]),'magic after:'+mg.decode('latin1'),out,'vbl',v1-v0,'errors',len(bad))
    except Exception as e:
        r=(name,'EXC',repr(e)[:100])
    finally:
        h.close()
    print(r,flush=True); res.append(r)
