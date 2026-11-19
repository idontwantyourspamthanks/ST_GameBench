from tr import *
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2e')
try:
    time.sleep(2.5)
    ev = capture(h, [(0.5,'down','Control_R'),(0.4,'up','Control_R')], tail=0.4)
    t0 = ev[0]['T']
    for e in ev[:70]:
        print('%8d %6d %-5s %s' % (e['T']-t0, e['fc'], e['n'], ('%02x'%e['d0']) if 'd0' in e else (e['st'] if 'st' in e else '')))
    print(len(ev))
finally:
    h.close()
