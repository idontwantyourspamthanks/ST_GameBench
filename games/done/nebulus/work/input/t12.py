from tr import *
h = Nebulus(snapshot='snap/play_noenemy.sav', workdir='/tmp/strun-nin2e')
try:
    time.sleep(2.5)
    ev = capture(h, [(0.3,'down','Right'),(0.5,'down','Control_R'),(0.5,'up','Control_R'),(0.0,'up','Right')], names=['VBL','POLL','FLIP','STORE'], extra=[('JUMP','pc = $39fc8'),('JUMPB','pc = $39ffc'),('SHOOT','pc = $3a2f8')], tail=0.8)
    t0 = ev[0]['T']
    prev=None
    for e in ev:
        if e['n']=='VBL': continue
        s=''
        if 'd0' in e: s='%02x'%e['d0']
        if 'st' in e:
            st=e['st']; s=' '.join('%s=%d'%(k,v) for k,v in st.items())
        print('%8d %-6s %s' % (e['T']-t0, e['n'], s))
finally:
    h.close()
