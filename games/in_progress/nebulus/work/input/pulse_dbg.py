from pulse import *
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2e')
try:
    time.sleep(2.5)
    R=h.R
    (R/'rel.txt').write_text('w $38498 $00\nm $38498 1\ne VBL\ne FrameCycles\n')
    (R/'press.txt').write_text('w $38498 $80\nm $38498 1\ne VBL\ne FrameCycles\n' + f'b pc = $382d8 :once :file {R/"rel.txt"}\n')
    (R/'arm.txt').write_text('e VBL\ne FrameCycles\n'+f'b pc = $382d8 :once :file {R/"press.txt"}\n')
    h.debug('b all',0.3); n0=len(h._logtext())
    h.cmd('hatari-debug b pc = $3a2f8 :trace'); time.sleep(0.2)
    h.cmd(f'hatari-debug b pc = $3853a :once :file {R/"arm.txt"}')
    time.sleep(1.5)
    print(h._logtext()[n0:][:2500])
finally:
    h.close()
