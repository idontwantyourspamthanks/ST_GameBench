from e2e import *
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2e')
try:
    time.sleep(2.5)
    (h.R/'s.txt').write_text('m $33a16 14\nm $338f0 8\nm $38498 1\n')
    h.debug('b all',0.3)
    h.cmd(f'hatari-debug b pc = $3868e :trace :file {h.R/"s.txt"}'); time.sleep(0.2)
    h.cmd('hatari-debug b pc = $39fc8 :trace'); time.sleep(0.2)
    h.cmd('hatari-debug b pc = $3853a :trace'); time.sleep(0.2)
    n=len(h._logtext())
    h._xdo('keydown','--window',h.win,'Control_R'); h._xdo('keydown','--window',h.win,'Right')
    time.sleep(0.5)
    h._xdo('keyup','--window',h.win,'Control_R'); h._xdo('keyup','--window',h.win,'Right')
    time.sleep(0.6)
    txt=h._logtext()[n:]
    h.debug('b all',0.3)
    out=[]
    for l in txt.splitlines():
        m=re.match(r'(\d+)\. CPU breakpoint',l)
        if m: out.append({'1':'\nFLIP','2':'\n JUMP','3':'\nPOLL'}[m.group(1)])
        m=re.match(r'(0003(?:3A16|38F0|8498)):\s+(.*?)\s{2,}',l)
        if m: out.append(m.group(1)[-4:]+':'+m.group(2).replace(' ',''))
    print('\n'.join(l for l in ' '.join(out).split('\n')[:30]))
finally:
    h.close()
