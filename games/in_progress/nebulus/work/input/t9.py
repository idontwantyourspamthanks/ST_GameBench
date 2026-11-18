from e2e import *
EV['TICK'] = 'pc = $382c0'
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2e')
try:
    time.sleep(2.5)
    toks = trial(h, [(0.6,'down','Control_R'),(0.35,'up','Control_R')], tail=0.5, names=['VBL','TICK','WAIT','FLIP','POLL','CONS','ACIA','STORE'])
    print(' '.join(toks))
finally:
    h.close()
