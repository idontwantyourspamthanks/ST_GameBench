from lib2 import *
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2a')
try:
    time.sleep(1.5)
    t = trial(h, [(0.2,'down','Control_R'),(0.3,'up','Control_R')])
    print(' '.join(t))
finally:
    h.close()
