import json, sys
FPC=160256
def T(e): return e['vbl']*FPC+e['fc']
def an(tag):
    runs=json.load(open(f'raw_{tag}.json')); rows=[]
    for r in runs:
        ev=[e for e in r['ev'] if e['n']!='M']
        press=next((e for e in ev if e['n']=='STORE' and e['d0']&0xf0==0x80),None)
        rel=next((e for e in ev if e['n']=='STORE' and e['d0']&0xf0==0x00 and e['d0']<0x10 and (press is None or T(e)>T(press))),None)
        shoot=any(e['n']=='SHOOT' for e in ev)
        if not press: rows.append((round(r['hold']*1000),None,None,None,shoot)); continue
        gap=(T(rel)-T(press))/FPC if rel else None
        polls=[e for e in ev if e['n']=='POLL' and T(e)>T(press) and (rel is None or T(e)<T(rel))]
        rows.append((round(r['hold']*1000), round(gap,2) if gap is not None else None, len(polls), shoot))
    print('==',tag,' (hold_ms, joy press->release gap in frames, polls inside the gap, fire reached state machine)')
    for x in sorted(rows,key=lambda x:(x[1] is None, x[1] or 0)): print('  ',x)
    ok=[x for x in rows if len(x)==4]
    print('  registered %d / %d ; with 0 polls in gap: %d (registered %d)'%(sum(x[3] for x in ok),len(ok),sum(1 for x in ok if x[2]==0),sum(1 for x in ok if x[2]==0 and x[3])))
for t in sys.argv[1:]: an(t)
