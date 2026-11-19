from e2e import *
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2e')
try:
    time.sleep(2.5)
    toks = trial(h, [(0,'down','Control_R'),(0,'down','Right'),(0.35,'up','Control_R'),(0,'up','Right')], tail=0.9, names=BASE2)
    print(' '.join(toks))
finally:
    h.close()
