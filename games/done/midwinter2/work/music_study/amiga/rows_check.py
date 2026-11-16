from explore import *
SEG={'mw2':[0x24a070,0x27f478,0x293e50,0x5cc8]}
game='mw2'
for st in ('mw2_equip','mw2_cockpit','mw2_hall'):
    with MW2.from_image(IMG, game=game, keep=STATES+f'scratch_{game}.hdf') as g:
        segs=[{'start':a} for a in SEG[game]]
        g.load_state(STATES+st+'.clstate'); g._hunk1=lambda: segs[1]['start']
        x=Explorer(g,mmio=True,segs=segs)
        t0=g.now(); x.run_to(t0+5)
        base0=segs[0]['start']
        mus=[r for r in x.rows if base0+0x30440<=r[4]<base0+0x31240]
        sfx=[r for r in x.rows if not (base0+0x30440<=r[4]<base0+0x31240)]
        vols=sorted(set((r[5],r[7]) for r in mus if r[5] in (0xdff0a8,0xdff0b8,0xdff0c8,0xdff0d8)))[:6]
        print(st,'music-code AUD rows in 5 s:',len(mus),'| other-code AUD rows:',len(sfx),'| ticks',len(set(r[0] for r in mus)),'| events',x.ev)
