from lib2 import *
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2a')
try:
    time.sleep(1.5)
    (h.R/'v.txt').write_text('m $ff8201 1\nm $ff8203 1\nm $ff8205 1\nm $ff8207 1\nm $ff8209 1\n')
    h.debug('b all',0.3)
    h.cmd(f'hatari-debug b pc = $382d8 :trace :file {h.R/"v.txt"}'); time.sleep(0.2)
    h.cmd(f'hatari-debug b pc = $3868e :trace :file {h.R/"v.txt"}'); time.sleep(0.2)
    n=len(h._logtext())
    time.sleep(0.5)
    txt=h._logtext()[n:]
    h.debug('b all',0.3)
    # compact
    out=[]
    for l in txt.splitlines():
        m=re.match(r'(\d+)\. CPU breakpoint',l)
        if m: out.append('\n'+('VBL' if m.group(1)=='1' else 'FLIP'))
        m=re.match(r'(0[0-9A-F]{7}):\s+([0-9a-f]{2})',l, re.I)
        if m: out.append(m.group(1)[-4:]+'='+m.group(2))
    print(' '.join(out)[:3000])
finally:
    h.close()
