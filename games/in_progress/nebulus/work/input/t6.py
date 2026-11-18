from lib2 import *
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2a')
try:
    time.sleep(1.5)
    (h.R/'r.txt').write_text('r\n')
    h.debug('b all',0.3)
    h.cmd(f'hatari-debug b pc = $38514 :trace :file {h.R/"r.txt"}'); time.sleep(0.2)
    h.cmd('hatari-debug b pc = $382d8 :trace'); time.sleep(0.2)
    n=len(h._logtext())
    h.cmd('hatari-debug e VBL')
    h._xdo('keydown','--window',h.win,'Control_R'); time.sleep(0.3)
    h._xdo('keyup','--window',h.win,'Control_R'); time.sleep(0.3)
    txt=h._logtext()[n:]
    h.debug('b all',0.3)
    print(repr(txt[:2500]))
finally:
    h.close()
